"""フォーム営業：フォーム判定 → 企業別の短文生成 → 承認キュー → 承認済みのみ送信 → 効果測定。

設計の前提（記事「フォーム営業の攻略」の考え方に対応）
  ① リストの精査 … 11_入口提案リスト（どの課題に何を提案するかを公開情報の根拠つきで説明できる企業だけ）
  ② 営業文       … 課題 → 改善の提案 → 根拠 → 話を聞くと分かること、の順で短く。入口提案ごとに出し分け
  ③ 数字で直す   … 送信数・返信数・アポ数・導入数を 文面パターン別／入口提案別 に集計

守ること
  - 営業お断りの表記があるフォーム、CAPTCHA付きフォーム、robots.txt で禁止されたページには送らない（回避しない）
  - 1社1回。営業停止リストの企業には送らない。1日の上限と送信間隔を守る
  - 送信は 13_フォーム営業キュー で人が「承認=済」「承認者」を入れた行だけ。所属代理店の承認が前提
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from . import plays
from . import schema as S
from .core import ROOT, Budget, Store, get_logger, is_unknown, to_int, today
from .outreach import eligible
from .pipeline import REPLIED, is_suppressed, log_activity

log = get_logger()
UA = "Mozilla/5.0 (compatible; sfs-formcheck; +business inquiry)"
PROHIBIT_RE = re.compile(
    r"(営業|セールス|売り?込み|勧誘|宣伝|広告)[^。\n]{0,25}(お断り|ご遠慮|禁止|固くお断り|対応いたしかね|受け付けて(おり|い)ません|返信(いた)?しません)"
    r"|(お断り|ご遠慮)[^。\n]{0,12}(営業|セールス|売り?込み|勧誘)")
CAPTCHA_RE = re.compile(r"recaptcha|hcaptcha|turnstile|g-recaptcha|captcha", re.I)
SALES_OPTION_RE = re.compile(r"営業|提案|ご紹介|協業|パートナー|その他")
OK, NG, MANUAL, UNKNOWN_ST = "送信可", "営業お断り（送信しない）", "手動対応", "未確認"

# 入力欄の種類 → 見出し・name属性のキーワード（上から順に判定）
FIELD_KEYS = [
    ("company_kana", r"(会社|法人|貴社|企業).*(カナ|かな|フリガナ|ふりがな)"),
    ("company", r"会社|法人|貴社|企業|団体|御社|company|organization|corp"),
    ("dept", r"部署|所属|役職|department|division"),
    ("name_kana", r"フリガナ|ふりがな|カナ|かな|kana|furigana|ruby"),
    ("email_confirm", r"(確認|再入力|confirm).*(メール|mail)|(メール|mail).*(確認|再入力|confirm)"),
    ("email", r"メール|mail"),
    ("tel", r"電話|tel|phone|携帯"),
    ("zip", r"郵便|zip|postal"),
    ("address", r"住所|所在地|address"),
    ("url", r"URL|ホームページ|サイト|website"),
    ("subject", r"件名|題名|タイトル|subject|title"),
    ("body", r"内容|本文|詳細|メッセージ|ご用件|ご質問|お問い?合わせ|message|inquiry|comment|body"),
    ("name", r"氏名|お名前|名前|担当者|name"),
]


def robots_allowed(url: str, session=None) -> bool | None:
    """robots.txt で取得が許可されているか。取得できなければ None。"""
    import requests
    p = urlparse(url)
    try:
        r = (session or requests).get(f"{p.scheme}://{p.netloc}/robots.txt", timeout=15, headers={"User-Agent": UA})
        if r.status_code >= 400:
            return True
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch("*", url)
    except Exception:
        return None


def classify_field(label: str, name: str, ftype: str = "") -> str:
    if ftype == "email":
        return "email_confirm" if re.search(r"確認|confirm|再", label + name, re.I) else "email"
    if ftype == "tel":
        return "tel"
    if ftype == "textarea":
        return "body"
    text = f"{label} {name}"
    for key, pat in FIELD_KEYS:
        if re.search(pat, text, re.I):
            return key
    return "unknown"


def parse_form(html: str, url: str = "") -> dict:
    """フォームページのHTMLから、判定に必要な情報を取り出す（送信はしない）。"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = re.sub(r"\s+", " ", soup.get_text(" "))
    m = PROHIBIT_RE.search(text)
    forms = [f for f in soup.find_all("form")
             if f.find("textarea") or len(f.find_all("input", {"type": ["text", "email", "tel"]})) >= 2]
    form = max(forms, key=lambda f: len(f.find_all(["input", "textarea", "select"])), default=None)
    fields, unknown_required, options = [], [], []
    if form is not None:
        for el in form.find_all(["input", "textarea", "select"]):
            t = (el.get("type") or el.name).lower()
            if t in ("hidden", "submit", "button", "image", "reset", "file"):
                continue
            label = ""
            if el.get("id"):
                lb = soup.find("label", {"for": el["id"]})
                label = lb.get_text(" ", strip=True) if lb else ""
            if not label:
                par = el.find_parent(["label", "tr", "dl", "div", "p", "li"])
                label = par.get_text(" ", strip=True)[:60] if par else ""
            label += " " + (el.get("placeholder") or "") + " " + (el.get("aria-label") or "")
            req = el.has_attr("required") or bool(re.search(r"必須|\*|※", label)) or "required" in " ".join(el.get("class") or [])
            kind = "choice" if t in ("select", "radio", "checkbox") else classify_field(label, el.get("name") or "", t)
            if el.name == "select":
                options += [o.get_text(strip=True) for o in el.find_all("option")]
            if t == "radio":
                options.append(label.strip()[:30])
            fields.append({"kind": kind, "name": el.get("name") or "", "type": t, "required": req})
            if kind == "unknown" and req:
                unknown_required.append((el.get("name") or label)[:30])
    captcha = bool(CAPTCHA_RE.search(html))
    kinds = {f["kind"] for f in fields}
    if m:
        status, basis = NG, f"表記あり「{text[max(0, m.start() - 15):m.end() + 15].strip()}」"
    elif form is None:
        status, basis = MANUAL, "入力フォームを検出できず（JavaScript描画・外部フォーム・電話のみ等）"
    elif captcha:
        status, basis = MANUAL, "CAPTCHA（画像認証等）あり。自動送信しない"
    elif "body" not in kinds:
        status, basis = MANUAL, "本文欄を特定できず"
    elif unknown_required:
        status, basis = MANUAL, "用途不明の必須項目あり：" + "、".join(unknown_required[:3])
    else:
        sales_opt = [o for o in options if re.search(r"営業|提案|協業", o)]
        status = OK
        basis = "営業お断りの表記なし・CAPTCHAなし・必須項目を特定" + (f"／専用区分あり「{sales_opt[0]}」" if sales_opt else "")
    return {"status": status, "basis": basis, "fields": sorted(kinds), "captcha": captcha,
            "options": [o for o in options if o][:12]}


def analyze(url: str, session=None, budget: Budget | None = None) -> dict:
    """フォームURLを1回取得して判定する。robots.txt で禁止なら取得しない。"""
    import requests
    if is_unknown(url) or not str(url).startswith("http"):
        return {"status": MANUAL, "basis": "問い合わせフォームのURLが未確認", "fields": [], "options": []}
    allowed = robots_allowed(url, session)
    if allowed is False:
        return {"status": NG, "basis": "robots.txt で取得が禁止されているページ（送信しない）", "fields": [], "options": []}
    if budget:
        budget.charge("websearch")
    try:
        r = (session or requests).get(url, timeout=25, headers={"User-Agent": UA})
        r.encoding = r.apparent_encoding
        if r.status_code >= 400:
            return {"status": UNKNOWN_ST, "basis": f"取得できず（HTTP {r.status_code}）", "fields": [], "options": []}
        res = parse_form(r.text, url)
        if res["status"] == MANUAL and "検出できず" in res["basis"] and session is None:
            html = render(url)                      # JavaScript描画のフォームはブラウザで描画して再判定
            if html:
                res = parse_form(html, url)
                res["basis"] += "（ブラウザ描画後に判定）"
        return res
    except Exception as e:
        return {"status": UNKNOWN_ST, "basis": f"取得できず（{type(e).__name__}）", "fields": [], "options": []}


def render(url: str) -> str:
    """tools/render.js でページを描画してHTMLを得る（読み取りのみ）。失敗時は空文字。"""
    try:
        p = subprocess.run(["node", str(ROOT / "tools" / "render.js"), url], capture_output=True, text=True, timeout=90)
        return p.stdout if p.returncode == 0 else ""
    except Exception:
        return ""


# ---------- 文面 ----------
def render_form_message(row: dict, settings: dict, variant: str) -> tuple[str, str]:
    """(件名, 本文)。課題 → 改善の提案 → 根拠 → 話を聞くと分かること、の順。variant は A / B。"""
    msg, s = plays.messages(), settings["sender"]
    key = plays.select(row)[0]["key"]
    v = {"company": row["企業名"], "city": row.get("市区", ""), "me": s["name"], "my_company": s["company"],
         "concept": settings["form_sales"]["concept"]}
    if settings["form_sales"].get("offer") == "komon":
        k, of = msg["komon"], settings["offer"]
        hook = key if key in ("dc", "newhire", "preretire") else \
            "kenko" if "健康経営" in str(row.get("認定・健康経営", "")) else "default"
        emp = to_int(row.get("従業員数"))
        per = f"従業員{emp}名の貴社の場合、1人あたり月約{int(of['monthly_yen'] / emp / 10 + 0.5) * 10:,}円です。" if emp else ""
        subject, why = k["subject"], plays._r(k["why"][hook], **v)
        lead = k["lead_" + variant.lower()]
        offer = plays._r(k["offer"], offer_name=of["name"], price_text=of["price_text"],
                         custom=k["custom"].get(hook, k["custom"]["default"]), per_head=per)
        learn, disclosure = k["learn"], k["disclosure"]
    else:
        f = msg["form"][key]
        subject, why = msg["plays"][key]["subject"], plays._r(f["why_you"], **v)
        lead, offer = plays._r(f["lead_" + variant.lower()], **v), plays._r(f["offer"], **v)
        learn, disclosure = plays._r(f["learn"], **v), msg["form_disclosure"]
    body = "\n".join([
        f"{row['企業名']} ご担当者さま",
        "",
        f"{s['company']}の{s['name']}と申します。{why}",
        "",
        lead,
        offer,
        "",
        learn,
        "ご関心がございましたら、このメッセージへのご返信、または下記までご連絡ください。",
        *([f"概要：{s['lp_url'].rstrip('/')}/"] if str(s.get("lp_url", "")).startswith("http") else []),
        "",
        disclosure,
        "",
        f"{s['company']} {s['title']} {s['name']}／{s['address']}",
        f"TEL {s['phone']}／MAIL {s['email']}／{s['website']}",
        f"保険募集は{s['agency']}の登録募集人として行います。",
    ])
    return subject, body


def variant_for(corp: str) -> str:
    """文面パターンを企業ごとに固定で割り当てる（A/Bを半々に。再実行しても変わらない）。"""
    return "AB"[sum(map(ord, str(corp))) % 2]


# ---------- キュー ----------
HUMAN_COLS = ["承認", "承認者", "送信状態", "送信日時", "証跡", "備考", "フォーム判定", "判定根拠", "入力欄"]


def candidates(store: Store, settings: dict) -> list[dict]:
    """フォーム営業の対象：確定対象で営業停止でない企業をスコア順に（form_sales.min_score 以上）。"""
    suppressed = {str(r["法人番号"]) for r in store.read(S.SUPPRESS)}
    lo = settings["form_sales"].get("min_score", 0)
    rows = [r for r in store.read(S.MASTER) if r.get("対象区分") == "確定対象"
            and str(r["法人番号"]) not in suppressed and (to_int(r.get("スコア")) or 0) >= lo]
    return sorted(rows, key=lambda r: (not str(r.get("紹介可能性", "")).startswith("あり"), -(to_int(r["スコア"]) or 0)))


def build_queue(store: Store, settings: dict, check: bool = False, budget: Budget | None = None,
                session=None) -> list[dict]:
    """13_フォーム営業キュー を更新。確定対象の企業が対象（スコア順）。承認・送信状態は引き継ぐ。

    check=True のとき、未判定の企業のフォームを取得して判定する（1社1回・間隔を空ける）。
    """
    prev = {str(r["法人番号"]): r for r in store.read(S.FORMQ)}
    rows = []
    for row in candidates(store, settings):
        corp = str(row["法人番号"])
        old = prev.get(corp, {})
        q = {c: "" for c in S.SHEETS[S.FORMQ]}
        q.update({"法人番号": corp, "企業名": row["企業名"], "ランク": row["ランク"], "スコア": row["スコア"],
                  "フォームURL": row.get("問い合わせフォーム", S.UNKNOWN), "入口提案": row.get("入口提案", ""),
                  "根拠": plays.select(row)[0]["evidence"], "承認": "未", "送信状態": "未送信",
                  "フォーム判定": UNKNOWN_ST, "判定根拠": ""})
        q.update({c: old[c] for c in HUMAN_COLS if old.get(c)})
        if str(row.get("営業お断り表記", "")).startswith("あり"):
            q["フォーム判定"], q["判定根拠"] = NG, "企業調査で営業お断りの表記を確認：" + str(row["営業お断り表記"])[:60]
        elif check and q["フォーム判定"] == UNKNOWN_ST:
            a = analyze(q["フォームURL"], session, budget)
            q["フォーム判定"], q["判定根拠"], q["入力欄"] = a["status"], a["basis"], "・".join(a["fields"])
            if session is None:
                time.sleep(2)
        if q["送信状態"] == "未送信":             # 送信済みの文面は書き換えない
            q["文面パターン"] = variant_for(corp)
            q["件名"], q["本文"] = render_form_message(row, settings, q["文面パターン"])
            q["文字数"] = len(q["本文"])
        else:
            q.update({c: old.get(c, "") for c in ("文面パターン", "件名", "本文", "文字数")})
        rows.append(q)
    # 優先営業リストから外れたが送信済みの行は履歴として残す
    keep = [r for c, r in prev.items() if c not in {x["法人番号"] for x in rows} and r.get("送信状態") == "送信済"]
    store.write(S.FORMQ, rows + keep)
    return rows + keep


def sendable(store: Store, settings: dict, on: str | None = None) -> tuple[list[dict], list[str]]:
    """送信してよい行と、止めた理由の一覧。"""
    reasons = []
    if not settings["compliance"]["agency_approved"]:
        return [], ["所属代理店の承認が未登録（compliance.agency_approved）"]
    if any("（" in str(v) for v in settings["sender"].values()):
        return [], ["差出人情報（settings.yaml の sender）に未記入の項目がある"]
    fs, day = settings["form_sales"], on or today()
    sent_today = sum(1 for r in store.read(S.FORMQ) if str(r.get("送信日時", "")).startswith(day))
    done = {str(a["法人番号"]) for a in store.read(S.ACTIVITY) if a["チャネル"] == "フォーム" and a["結果"] != "下書き"}
    out = []
    for r in store.read(S.FORMQ):
        corp = str(r["法人番号"])
        if r.get("承認") != "済" or r.get("送信状態") != "未送信":
            continue
        why = None
        if is_unknown(r.get("承認者")):
            why = "承認者が未記入"
        elif r.get("フォーム判定") != OK:
            why = f"フォーム判定が「{r.get('フォーム判定')}」"
        elif is_suppressed(store, corp):
            why = "営業停止リストに登録済み"
        elif corp in done:
            why = "このフォームには送信済み（1社1回）"
        elif int(r.get("文字数") or 0) > fs["max_chars"]:
            why = f"本文が{fs['max_chars']}字を超過"
        elif sent_today + len(out) >= fs["daily_max"]:
            why = f"1日の上限 {fs['daily_max']} 件に到達"
        if why:
            reasons.append(f"{r['企業名']}：{why}")
        else:
            out.append(r)
    return out, reasons


def send(store: Store, settings: dict, budget: Budget, dry_run: bool = True, runner=None,
         on: str | None = None) -> dict:
    """承認済みの行をブラウザで入力する。dry_run=True は入力と確認画面の撮影まで（送信しない）。"""
    rows, reasons = sendable(store, settings, on)
    s, fs = settings["sender"], settings["form_sales"]
    shots = ROOT / "output" / "form_evidence"
    shots.mkdir(parents=True, exist_ok=True)
    result = {"dry_run": dry_run, "sent": [], "failed": [], "skipped": reasons}
    queue = store.read(S.FORMQ)
    for i, r in enumerate(rows):
        corp = str(r["法人番号"])
        if not dry_run:
            budget.charge("form_send")
        job = {"url": r["フォームURL"], "send": not dry_run,
               "screenshot": str(shots / f"{corp}_{today()}{'' if not dry_run else '_dryrun'}.png"),
               "values": {"company": s["company"], "company_kana": s.get("company_kana", ""), "name": s["name"],
                          "name_kana": s.get("name_kana", ""), "dept": s["title"], "email": s["email"],
                          "email_confirm": s["email"], "tel": s["phone"], "zip": s.get("zip", ""),
                          "address": s["address"], "url": s["website"], "subject": r["件名"], "body": r["本文"]}}
        res = (runner or run_browser)(job)
        ok = res.get("ok") and (dry_run or res.get("submitted"))
        for q in queue:
            if str(q["法人番号"]) == corp:
                if dry_run:
                    q["備考"] = f"試行（未送信）{today()}：{res.get('detail', '')}"[:200]
                elif ok:
                    q.update({"送信状態": "送信済", "送信日時": f"{on or today()} {dt.datetime.now():%H:%M}",
                              "証跡": Path(job["screenshot"]).name})
                else:
                    q.update({"送信状態": "手動対応", "備考": f"自動送信できず：{res.get('detail', '')}"[:200]})
        store.write(S.FORMQ, queue)
        if ok and not dry_run:
            log_activity(store, settings, corp, "フォーム", "未返信", date=on,
                         content=f"フォーム送信｜{r['入口提案'][:20]}｜文面{r['文面パターン']}", approver=r["承認者"])
            result["sent"].append(r["企業名"])
        elif not ok:
            result["failed"].append(f"{r['企業名']}：{res.get('detail', '')}")
        if runner is None and i < len(rows) - 1:
            time.sleep(fs["min_interval_sec"])
    log.info("フォーム送信 dry_run=%s 送信%d 失敗%d 見送り%d", dry_run, len(result["sent"]),
             len(result["failed"]), len(reasons))
    return result


def run_browser(job: dict) -> dict:
    """tools/form_submit.js（Playwright）を1件実行。"""
    try:
        p = subprocess.run(["node", str(ROOT / "tools" / "form_submit.js")], input=json.dumps(job),
                           capture_output=True, text=True, timeout=120)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {"ok": False, "detail": f"ブラウザ実行エラー（{type(e).__name__}）"}


# ---------- 効果測定 ----------
def funnel(store: Store) -> list[dict]:
    """文面パターン別・入口提案別の 送信→返信→アポ→導入。件数が少ないうちは優劣を判定しない。"""
    q = [r for r in store.read(S.FORMQ) if r.get("送信状態") == "送信済"]
    acts = store.read(S.ACTIVITY)
    replied = {str(a["法人番号"]) for a in acts if a["結果"] in REPLIED}
    appo = {str(a["法人番号"]) for a in acts if a["結果"] == "アポ獲得"} | {str(d["法人番号"]) for d in store.read(S.DEALS)}
    adopted = {str(a["法人番号"]) for a in store.read(S.ADOPTED)}
    out = []
    for label, keyfn in (("文面パターン", lambda r: r["文面パターン"]), ("入口提案", lambda r: r["入口提案"])):
        for k in sorted({keyfn(r) for r in q}):
            g = [str(r["法人番号"]) for r in q if keyfn(r) == k]
            n = len(g)
            rep = sum(c in replied for c in g)
            out.append({"区分": label, "値": k, "送信": n, "返信": rep, "アポ": sum(c in appo for c in g),
                        "導入": sum(c in adopted for c in g),
                        "返信率(%)": round(rep / n * 100, 1) if n else None,
                        "判定": "判定不能（送信30件未満）" if n < 30 else "比較可"})
    return out
