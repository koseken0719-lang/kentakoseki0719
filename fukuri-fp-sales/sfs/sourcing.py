"""候補企業の大量リストアップ（調査エージェントを使わない経路）。

種リスト … 健康経営優良法人（中小規模法人部門）の認定法人一覧（公開Excel。法人番号・市区町村・業種つき）
補完     … gBizINFO の公開ページ（従業員数／厚生年金の被保険者数／企業ホームページ／認定）
           → 公式サイト → 問い合わせフォーム・採用ページ（キーワードの有無のみ）
出力     … 調査レコード（data/research/seed_*.json）。research.import_files でそのまま取り込める。

1社あたりの取得は最大4ページ、間隔を空ける。robots.txt で禁止されたページは取得しない。
確認できない項目は未確認のままにし、推測で埋めない。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from . import schema as S
from .core import ROOT, Budget, Store, get_logger, today
from .forms import UA, robots_allowed
from .research import drive_minutes, valid_corporate_number

log = get_logger()
SEED_URL = "https://kenko-keiei.jp/houjin_list/"
GBIZ = "https://info.gbiz.go.jp/hojin/ichiran?hojinBango={}"
EXCLUDE_INDUSTRY = re.compile(r"保険業|金融業|地方公共団体")
INDUSTRY_MAP = [(r"情報通信", "IT・システム開発"), (r"製造", "製造業"), (r"建設", "建設業"), (r"設備工事", "設備工事業"),
                (r"運輸|物流|郵便", "物流"), (r"不動産", "不動産管理"), (r"医療|福祉|介護", "介護"),
                (r"税理士|士業|専門・技術", "その他")]
CONTACT_RE = re.compile(r"contact|inquiry|inquire|toiawase|otoiawase|お問い?合わ?せ|お問合せ", re.I)
RECRUIT_RE = re.compile(r"recruit|saiyo|career|採用|求人", re.I)
HOOKS = {"確定拠出年金": r"確定拠出|企業型\s*DC|401\s*k", "退職金": r"退職金", "財形": r"財形", "持株会": r"持株",
         "新卒採用": r"(?<!第二)新卒", "資格取得支援": r"資格取得", "住宅手当": r"住宅手当"}


def load_seed(path: Path, settings: dict) -> list[dict]:
    """認定法人一覧から、対象エリア（車での上限時間内）の候補を近い順に返す。"""
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True)
    mx, out = settings["max_travel_minutes"], []
    for ws in wb.worksheets:
        hdr = None
        for r in ws.iter_rows(values_only=True):
            if r and r[0] == "No.":
                hdr = [str(x) for x in r]
                continue
            if not hdr or not r or r[0] is None:
                continue
            d = dict(zip(hdr, r))
            if d.get("都道府県") not in settings["drive_minutes"]:
                continue
            m = settings["drive_minutes"][d["都道府県"]].get(str(d.get("市区町村")))
            num = str(d.get("法人番号") or "").strip()
            if m is None or m > mx or d.get("小規模特例認定") or not valid_corporate_number(num) \
                    or EXCLUDE_INDUSTRY.search(str(d.get("業種") or "")):
                continue
            out.append({"corporate_number": num, "name": str(d["認定法人名"]).strip(), "pref": d["都道府県"],
                        "city": str(d["市区町村"]), "seed_industry": str(d.get("業種") or ""), "drive": m,
                        "cert": f"健康経営優良法人2026（中小規模法人部門{'・' + ws.title if 'ブライト' in ws.title else ''}）"})
    wb.close()
    out.sort(key=lambda x: (x["drive"], x["corporate_number"]))
    return out


def _get(url: str, session, timeout: int = 25) -> str:
    r = session.get(url, timeout=timeout, headers={"User-Agent": UA})
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text


def _text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for x in soup(["script", "style"]):
        x.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" "))


def parse_gbiz(html: str) -> dict:
    """gBizINFO の法人ページから、従業員数・被保険者数・ホームページ・所在地・業種・認定を取り出す。"""
    t = _text(html)
    g = lambda pat: (m.group(1).strip() if (m := re.search(pat, t)) else None)
    emp = g(r"従業員数\s+([\d,]+)\s*人")
    insured = None
    if (m := re.search(r"被保険者数 全喪年月日(.*?)財務 ※", t)):
        nums = [int(x.replace(",", "")) for x in re.findall(r"([\d,]+)\s*人", m.group(1))]
        insured = sum(nums) if nums else None
    hp = g(r"企業ホームページ\s+(https?://\S+)")
    certs = [c for c in ("ユースエール", "くるみん", "えるぼし", "健康経営優良法人") if c in t]
    return {"employees": int(emp.replace(",", "")) if emp else None, "insured": insured, "homepage": hp,
            "address": g(r"本店所在地\s+(\S+)\s"), "gbiz_industry": g(r"業種\s+([A-Z]\.\S+)"),
            "business": g(r"事業概要\s+(.+?)\s+（\s*職場情報総合サイト"), "certs": certs}


def scan_site(homepage: str, session) -> dict:
    """公式サイトのトップと採用ページから、問い合わせ・採用のリンクと制度キーワードの有無を拾う。"""
    from bs4 import BeautifulSoup
    out = {"contact": None, "recruit": None, "hooks": [], "hook_url": None, "phone": None}
    if robots_allowed(homepage, session) is False:
        return out
    html = _get(homepage, session)
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(homepage).netloc
    for a in soup.find_all("a", href=True):
        href, label = urljoin(homepage, a["href"]), a.get_text(" ", strip=True)
        if not href.startswith("http") or re.search(r"\.(pdf|jpg|png|zip)$|^mailto:|^tel:", href, re.I):
            continue
        same = urlparse(href).netloc.endswith(host.removeprefix("www."))
        if not out["contact"] and same and CONTACT_RE.search(href + " " + label) and "privacy" not in href:
            out["contact"] = href
        if not out["recruit"] and RECRUIT_RE.search(href + " " + label):
            out["recruit"] = href
    if (m := re.search(r"(?:TEL|電話)[^\d]{0,8}(0\d{1,3}-\d{2,4}-\d{4})", _text(html))):
        out["phone"] = m.group(1)
    pages = [(homepage, html)]
    if out["recruit"] and urlparse(out["recruit"]).netloc.endswith(host.removeprefix("www.")) \
            and robots_allowed(out["recruit"], session) is not False:
        try:
            pages.append((out["recruit"], _get(out["recruit"], session)))
        except Exception:
            pass
    for url, h in reversed(pages):                      # 採用ページを優先
        found = [k for k, pat in HOOKS.items() if re.search(pat, _text(h))]
        if found and not out["hooks"]:
            out["hooks"], out["hook_url"] = found, url
    return out


def _size(g: dict) -> tuple[int | None, str]:
    if g.get("employees") is not None:
        return g["employees"], "gBizINFO掲載値（時点記載なし）"
    if g.get("insured"):
        return g["insured"], "厚生年金の被保険者数（gBizINFO掲載。従業員数そのものではない）"
    return None, S.UNKNOWN


def _cache(name: str) -> Path:
    p = ROOT / "data" / "seed" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(name: str) -> dict:
    p = _cache(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def stage1(store: Store, settings: dict, budget: Budget, target: int = 200, seed: Path | None = None,
           session=None, sleep: float = 1.5) -> dict:
    """段階1：近い順にgBizINFOを引き、規模が対象範囲（30〜300名）の会社が target 社たまるまで進める。

    結果は data/seed/gbiz_cache.json に保存し、再実行時は続きから。
    """
    import requests
    s = session or requests.Session()
    er = settings["employee_range"]
    cache = _load("gbiz_cache.json")
    known = {str(r["法人番号"]) for r in store.read(S.MASTER)} | {str(r["法人番号"]) for r in store.read(S.SUPPRESS)}
    ok = lambda v: (n := _size(v["g"])[0]) is not None and er["hard_min"] <= n <= er["hard_max"]
    qualified = sum(1 for k, v in cache.items() if k not in known and ok(v))
    fetched = errors = 0
    for c in load_seed(seed or _cache("kenko_chusho_2026.xlsx"), settings):
        if qualified >= target:
            break
        num = c["corporate_number"]
        if num in cache or num in known:
            continue
        try:
            budget.charge("gbizinfo")
            cache[num] = {"c": c, "g": parse_gbiz(_get(GBIZ.format(num), s))}
            qualified += ok(cache[num])
            fetched += 1
        except Exception as e:
            errors += 1
            log.info("gBizINFO取得失敗 %s: %s", c["name"], type(e).__name__)
        if fetched % 25 == 0:
            _cache("gbiz_cache.json").write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        if session is None:
            time.sleep(sleep)
    _cache("gbiz_cache.json").write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return {"今回取得": fetched, "取得失敗": errors, "調査済み累計": len(cache), "規模が対象範囲（未登録）": qualified}


def qualified(store: Store, settings: dict) -> list[dict]:
    """規模が対象範囲で未登録の候補（近い順）。homepage は gBizINFO または sites.json から。"""
    er, sites = settings["employee_range"], _load("sites.json")
    known = {str(r["法人番号"]) for r in store.read(S.MASTER)} | {str(r["法人番号"]) for r in store.read(S.SUPPRESS)}
    out = []
    for num, v in _load("gbiz_cache.json").items():
        n = _size(v["g"])[0]
        if num in known or n is None or not er["hard_min"] <= n <= er["hard_max"]:
            continue
        site = sites.get(num, {})
        out.append({**v["c"], "g": v["g"], "size": n, "homepage": v["g"].get("homepage") or site.get("website"),
                    "contact": site.get("contact_url"), "site_checked": num in sites})
    out.sort(key=lambda x: (x["drive"], abs(x["size"] - 75)))
    return out


def needs_site(store: Store, settings: dict) -> list[dict]:
    """公式サイトが未特定の候補（Web検索での補完対象）。"""
    return [{"corporate_number": q["corporate_number"], "name": q["name"], "pref": q["pref"], "city": q["city"],
             "address": q["g"].get("address"), "industry": q["seed_industry"]}
            for q in qualified(store, settings) if not q["homepage"] and not q["site_checked"]]


def stage3(store: Store, settings: dict, limit: int = 200, session=None, sleep: float = 1.0) -> dict:
    """段階3：公式サイトが分かった候補を調査レコードにして data/research/ に書き出す。"""
    import requests
    s = session or requests.Session()
    recs = []
    for q in qualified(store, settings):
        if len(recs) >= limit:
            break
        if not q["homepage"]:
            continue
        try:
            recs.append(enrich(q, s, g=q["g"], homepage=q["homepage"], contact=q["contact"]))
        except Exception as e:
            log.info("レコード化失敗 %s: %s", q["name"], type(e).__name__)
        if session is None:
            time.sleep(sleep)
    out = ROOT / "data" / "research" / f"seed_{today()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"調査レコード": len(recs), "file": str(out)}


def enrich(c: dict, session, g: dict, homepage: str, contact: str | None = None) -> dict:
    """候補1社を調査レコードにする（公式サイトのトップと採用ページを見る）。"""
    url = GBIZ.format(c["corporate_number"])
    emp, as_of = _size(g)
    site = {"contact": None, "recruit": None, "hooks": [], "hook_url": None, "phone": None}
    try:
        site = scan_site(homepage, session)
    except Exception as e:
        log.info("サイト取得不可 %s: %s", c["name"], type(e).__name__)
    site["contact"] = contact or site["contact"]
    hooks = site["hooks"]
    welfare = [h for h in hooks if h != "新卒採用"]
    industry = next((v for pat, v in INDUSTRY_MAP if re.search(pat, c["seed_industry"])), "その他")
    srcs = [{"url": SEED_URL, "what": "健康経営優良法人2026 認定法人一覧（法人番号・市区町村・業種）"},
            {"url": url, "what": "gBizINFO（従業員数または被保険者数・所在地）"},
            {"url": homepage, "what": "公式サイト"}]
    if site["hook_url"] and site["hook_url"] != homepage:
        srcs.append({"url": site["hook_url"], "what": "公式サイト（制度・採用のキーワード有無）"})
    return {
        "corporate_number": c["corporate_number"], "corporate_number_url": url, "name": c["name"],
        "address": g.get("address") or f"{c['pref']}{c['city']}", "city": c["city"],
        "employees": emp, "employees_as_of": as_of, "employees_url": url if emp else S.UNKNOWN,
        "industry": industry, "business_summary": (g.get("business") or c["seed_industry"])[:80],
        "website": homepage,
        "recruit_active": None,
        "recruit_info": "新卒採用の記載あり（公式サイトのキーワード検出。募集中かは未確認）" if "新卒採用" in hooks else S.UNKNOWN,
        "recruit_url": site["recruit"] or S.UNKNOWN,
        "welfare_info": ("記載あり：" + "・".join(welfare) + "（公式サイトのキーワード検出）") if welfare else S.UNKNOWN,
        "welfare_url": site["hook_url"] or S.UNKNOWN,
        "health_mgmt": "・".join(dict.fromkeys([c["cert"]] + [x for x in g.get("certs", []) if x != "健康経営優良法人"])),
        "health_mgmt_url": SEED_URL,
        "contact_phone": site["phone"] or S.UNKNOWN, "contact_form_url": site["contact"] or S.UNKNOWN,
        "sales_prohibited": None, "sns": [], "sources": srcs, "verified_date": today(),
        "notes": f"種リスト経由の機械収集。業種（認定一覧）：{c['seed_industry']}",
    }
