"""企業調査データの検証・取り込み・移動時間算定・スコアリング・営業仮説。

調査結果（JSON）は Claude のWeb調査または gBizINFO API から得る。ここでは
「捏造・未確認データを確定対象に混ぜない」ための検証と、決定的な評価を行う。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import schema as S
from .core import Budget, Store, get_logger, is_unknown, short_hash, to_int, today

log = get_logger()
URL_RE = re.compile(r"^https?://[^\s]+$")
WELFARE_ASSET_WORDS = ["退職金", "確定拠出", "企業年金", "持株", "財形", "中退共", "iDeCo", "DC"]
WELFARE_WORDS = WELFARE_ASSET_WORDS + ["住宅手当", "家族手当", "資格", "育児", "介護休", "社宅",
                                       "健康診断", "人間ドック", "慶弔", "保養", "社員旅行", "奨学金"]
DEPT_WORDS = ["総務", "人事", "管理", "経営企画", "労務", "採用"]


# ---------- 法人番号 ----------
def valid_corporate_number(num: str) -> bool:
    """13桁＋チェックデジット検証（国税庁の算式）。"""
    num = str(num)
    if not re.fullmatch(r"[1-9]\d{12}", num):
        return False
    base = num[1:]
    total = sum(int(d) * (1 if i % 2 == 0 else 2) for i, d in enumerate(reversed(base)))
    return 9 - (total % 9) == int(num[0])


def company_key(rec: dict) -> tuple[str, bool]:
    """(キー, 法人番号確認済みか)。未確認時は名称+所在地から仮キーを作る。"""
    num = re.sub(r"\D", "", str(rec.get("corporate_number", "")))
    if valid_corporate_number(num):
        return num, True
    return f"仮-{short_hash(rec.get('name', ''), rec.get('city', ''))}", False


# ---------- 検証 ----------
def validate_record(rec: dict) -> list[str]:
    """致命的な不備（取り込み拒否理由）を返す。空なら取り込み可。"""
    errs = []
    if is_unknown(rec.get("name")):
        errs.append("企業名なし")
    if not URL_RE.match(str(rec.get("website", ""))):
        errs.append("公式サイトURLなし（実在確認不可）")
    srcs = [s for s in rec.get("sources") or [] if URL_RE.match(str(s.get("url", "")))]
    if not srcs:
        errs.append("情報源URLなし")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(rec.get("verified_date", ""))):
        errs.append("確認日なし")
    num = str(rec.get("corporate_number", ""))
    if not is_unknown(num) and not valid_corporate_number(re.sub(r"\D", "", num)):
        errs.append(f"法人番号のチェックデジット不一致: {num}")
    emp = rec.get("employees")
    if emp is not None and to_int(emp) is None:
        errs.append(f"従業員数が数値でない: {emp}")
    if to_int(emp) is not None and not URL_RE.match(str(rec.get("employees_url", ""))):
        errs.append("従業員数に情報源URLがない")
    return errs


# ---------- アクセス ----------
def norm_station(name: str) -> str:
    n = re.sub(r"(駅|\s|　)", "", str(name or ""))
    return n.replace("ヶ", "ケ").replace("が丘", "ケ丘")


def travel_minutes(station: str, walk, settings: dict) -> tuple[int | None, str]:
    """武蔵小金井駅からの概算移動時間（駅間所要時間表＋公式サイト記載の徒歩分数）。"""
    table = {norm_station(k): v for k, v in settings["stations"].items()}
    st, w = norm_station(station), to_int(walk)
    if st not in table:  # 「JR中央線武蔵小金井」のような路線名付き表記は末尾一致（最長）で解決
        hits = sorted((k for k in table if st.endswith(k)), key=len, reverse=True)
        st = hits[0] if hits else st
    if is_unknown(station) or st not in table:
        return None, "未確認（最寄り駅が所要時間表にない／不明）"
    if w is None:
        return None, "未確認（駅からの徒歩分数が不明）"
    return table[st] + w, "概算（駅間所要時間表＋公式記載の徒歩分）"


def area_tier(city: str, settings: dict) -> str:
    for tier, cities in settings["areas"].items():
        if city in cities:
            return tier
    return "対象外地域"


def industry_tier(industry: str, settings: dict) -> str:
    for tier, inds in settings["industries"].items():
        if industry in inds:
            return tier
    return "その他"


# ---------- スコアリング ----------
def score(row: dict, settings: dict, has_referral: bool = False) -> tuple[int, dict]:
    """企業マスター行を100点満点で評価。内訳dictも返す。未確認は0点（加点しない）。"""
    b = {}
    er = settings["employee_range"]
    emp = to_int(row.get("従業員数"))
    if emp is None:
        b["従業員規模"] = 0
    elif er["ideal_min"] <= emp <= er["ideal_max"]:
        b["従業員規模"] = 20
    elif 40 <= emp < er["ideal_min"] or er["ideal_max"] < emp <= 150:
        b["従業員規模"] = 14
    elif 30 <= emp < 40 or 150 < emp <= 200:
        b["従業員規模"] = 8
    elif 20 <= emp < 30 or 200 < emp <= 300:
        b["従業員規模"] = 4
    else:
        b["従業員規模"] = 0

    rec, ret = str(row.get("採用情報", "")), str(row.get("人材定着の取組", ""))
    p = 0
    if not is_unknown(rec) and not rec.startswith("募集なし"):
        p += 10
        if "新卒" in rec and re.search(r"中途|キャリア|経験者", rec):
            p += 4
    if not is_unknown(ret):
        p += 6
    b["採用・人材定着"] = min(p, 20)

    wel, cert = str(row.get("福利厚生情報", "")), str(row.get("認定・健康経営", ""))
    p = 0
    if not is_unknown(wel):
        p += 8
        if sum(w in wel for w in WELFARE_WORDS) >= 3:
            p += 4
    if not is_unknown(cert):
        p += 8
    b["福利厚生への関心"] = min(p, 20)

    t = to_int(row.get("移動時間(分)"))
    b["アクセス"] = 0 if t is None else 15 if t <= 20 else 12 if t <= 30 else 9 if t <= 45 \
        else 5 if t <= settings["max_travel_minutes"] else 0

    if has_referral:
        p = 15
    else:
        rep = str(row.get("代表者(公開情報)", ""))
        p = 0
        p += 5 if "オーナー経営" in rep else 0
        p += 2 if not is_unknown(rep) else 0
        p += 3 if any(w in str(row.get("公開担当部署", "")) for w in DEPT_WORDS) else 0
        p += 2 if not is_unknown(row.get("代表電話")) else 0
        prohibited = str(row.get("営業お断り表記", "")).startswith("あり")
        if not is_unknown(row.get("公開メール")) or \
                (not is_unknown(row.get("問い合わせフォーム")) and not prohibited):
            p += 3
    b["意思決定者への接触可能性"] = min(p, 15)

    p = {"最優先": 6, "次点": 4}.get(row.get("業種区分", ""), 2)
    if any(w in wel for w in WELFARE_ASSET_WORDS):
        p += 2
    if "新卒" in rec or re.search(r"若手|20代|子育て|育児", rec + ret + wel):
        p += 2
    b["FP相談との親和性"] = min(p, 10)
    return sum(b.values()), b


def rank(total: int, settings: dict) -> str:
    for r, th in sorted(settings["ranks"].items(), key=lambda x: -x[1]):
        if total >= th:
            return r
    return "C"


def classify(row: dict, settings: dict, suppressed: bool, key_verified: bool = True) -> tuple[str, str]:
    """(対象区分, 追加調査理由)。従業員数・移動時間が未確認なら確定対象にしない。"""
    if suppressed:
        return "営業停止", ""
    reasons = []
    emp, t = to_int(row.get("従業員数")), to_int(row.get("移動時間(分)"))
    if emp is None:
        reasons.append("従業員数未確認")
    if t is None:
        reasons.append("移動時間未確認")
    if reasons:
        return "追加調査", "・".join(reasons)
    er = settings["employee_range"]
    if row.get("地域区分") == "対象外地域":
        return "対象外", "対象地域外"
    if t > settings["max_travel_minutes"]:
        return "対象外", f"移動時間{t}分（上限超過）"
    if not er["hard_min"] <= emp <= er["hard_max"]:
        return "対象外", f"従業員数{emp}名（対象規模外）"
    return "確定対象", "" if key_verified else "法人番号未確認（仮キー。要確認）"


# ---------- 営業仮説・推奨アプローチ ----------
INDUSTRY_HOOK = {
    "IT・システム開発": "エンジニアの採用競争が激しく、20〜30代社員の住宅購入・資産形成の関心が高い。費用ゼロで福利厚生メニューを追加でき、採用ページの訴求材料になる",
    "製造業": "技能人材の定着が経営課題。住宅ローン・教育資金・退職後の生活設計など勤続層のライフイベント相談ニーズが大きい",
    "建設業": "若手入職者の確保と定着が課題。現場勤務で金融機関に相談する時間が取りにくい社員に、オンライン／出張相談を提供できる",
    "設備工事業": "有資格者の定着が受注力に直結。家計・住宅・老後の不安解消を会社の支援として打ち出せる",
    "税理士法人": "職員向け福利厚生に加え、顧問先企業への紹介パートナーとしての連携余地がある",
    "医療法人": "看護師・コメディカルの定着が課題。シフト勤務者でも利用しやすい個別相談は福利厚生として差別化になる",
    "不動産管理": "社員自身の住宅購入・資産形成への関心が高く、相談内容との親和性がある",
    "物流": "ドライバー・倉庫人材の定着が課題。家計管理・教育資金の相談機会を会社負担ゼロで提供できる",
    "介護": "離職率の抑制が経営課題。家計・老後資金の不安に寄り添う福利厚生として職員満足度の向上が見込める",
}


def hypothesis(row: dict) -> str:
    parts = []
    if not is_unknown(row.get("採用情報")):
        parts.append(f"採用活動中（{str(row['採用情報'])[:40]}）で、福利厚生の拡充が採用・定着の訴求になる")
    if not is_unknown(row.get("認定・健康経営")):
        parts.append(f"{str(row['認定・健康経営'])[:40]}の取り組みがあり、従業員支援施策との方針整合性が高い")
    if not is_unknown(row.get("福利厚生情報")):
        w = [x for x in WELFARE_ASSET_WORDS if x in str(row["福利厚生情報"])]
        if w:
            parts.append(f"既存制度（{'・'.join(w)}）の活用促進・金融リテラシー向上の文脈で提案できる")
    parts.append(INDUSTRY_HOOK.get(row.get("業種", ""), "費用負担なしで従業員と家族向けの相談窓口を追加できる"))
    return "。".join(parts) + "。"


def approach(row: dict) -> str:
    if not is_unknown(row.get("紹介可能性")) and str(row["紹介可能性"]).startswith("あり"):
        return "紹介（既存人脈・パートナー経由で紹介依頼）→ 訪問"
    prohibited = str(row.get("営業お断り表記", "")).startswith("あり")
    owner = "オーナー経営" in str(row.get("代表者(公開情報)", ""))
    steps = []
    if owner:
        steps.append("社長宛て手紙（郵送）")
    if not is_unknown(row.get("公開メール")):
        steps.append("公開メール宛ての初回メール")
    elif not is_unknown(row.get("問い合わせフォーム")) and not prohibited:
        steps.append("問い合わせフォーム（営業可否を目視確認のうえ）")
    if not steps:
        steps.append("社長・総務宛て手紙（郵送）")
    if not is_unknown(row.get("代表電話")):
        dept = row.get("公開担当部署")
        steps.append(f"電話フォロー（{'総務・人事ご担当' if is_unknown(dept) else dept}宛て）")
    note = "　※フォームは営業お断り表記あり・使用禁止" if prohibited else ""
    return " → ".join(steps) + note


# ---------- 取り込み ----------
def _v(x, default=S.UNKNOWN):
    return default if is_unknown(x) else x


def _dept(x) -> str:
    """部署名として使えるもののみ採用（「明記なし」等の注記や長文は未確認扱い）。"""
    x = str(_v(x)).strip()
    return S.UNKNOWN if re.search(r"なし|未確認|不明", x) or len(x) > 20 else x


def to_master_row(rec: dict, settings: dict) -> tuple[dict, bool]:
    key, verified = company_key(rec)
    city = _v(rec.get("city"))
    t, t_kind = travel_minutes(rec.get("nearest_station"), rec.get("walk_minutes"), settings)
    emp = to_int(rec.get("employees"))
    rep = _v(rec.get("representative"))
    if rep != S.UNKNOWN and rec.get("owner_managed") is True:
        rep += "／オーナー経営（" + str(_v(rec.get("owner_managed_basis"), "公開情報より"))[:40] + "）"
    ra = rec.get("recruit_active")
    recruit = _v(rec.get("recruit_info"))
    if ra is False:
        recruit = "募集なし（確認時点）" if recruit == S.UNKNOWN else "募集なし：" + recruit
    sp = rec.get("sales_prohibited")
    prohibited = "あり：" + str(rec.get("sales_prohibited_note", ""))[:60] if sp is True \
        else "なし（確認日時点）" if sp is False else S.UNKNOWN
    srcs = [s["url"] for s in rec.get("sources") or [] if URL_RE.match(str(s.get("url", "")))]
    for k in ("corporate_number_url", "employees_url", "access_url"):
        if URL_RE.match(str(rec.get(k, ""))) and rec[k] not in srcs:
            srcs.append(rec[k])
    row = {
        "法人番号": key, "企業名": rec["name"], "所在地": _v(rec.get("address")), "市区": city,
        "地域区分": area_tier(city, settings), "最寄り駅": _v(rec.get("nearest_station")),
        "駅徒歩(分)": _v(to_int(rec.get("walk_minutes"))),
        "移動時間(分)": _v(t), "移動時間区分": t_kind,
        "従業員数": _v(emp), "従業員数時点": _v(rec.get("employees_as_of")),
        "業種": _v(rec.get("industry"), "その他"),
        "業種区分": industry_tier(rec.get("industry", ""), settings),
        "事業概要": _v(rec.get("business_summary")), "公式サイト": rec["website"],
        "代表者(公開情報)": rep, "採用情報": recruit, "採用URL": _v(rec.get("recruit_url")),
        "福利厚生情報": _v(rec.get("welfare_info")), "福利厚生URL": _v(rec.get("welfare_url")),
        "認定・健康経営": _v(rec.get("health_mgmt")), "人材定着の取組": _v(rec.get("retention_info")),
        "地域活動": _v(rec.get("community_info")), "公開担当部署": _dept(rec.get("contact_department")),
        "代表電話": _v(rec.get("contact_phone")), "公開メール": _v(rec.get("contact_email")),
        "問い合わせフォーム": _v(rec.get("contact_form_url")), "営業お断り表記": prohibited,
        "公式SNS": "\n".join(rec.get("sns") or []) or S.UNKNOWN,
        "情報源": "\n".join(srcs), "確認日": rec["verified_date"],
        "紹介可能性": S.UNKNOWN, "営業ステータス": "未着手", "次回アクション日": "",
        "初回登録日": today(), "最終更新日": today(),
    }
    return row, verified


def rescore(store: Store, settings: dict) -> dict:
    """全企業を再評価し、02_優先営業リストを再生成する。"""
    from . import plays
    suppressed = {r["法人番号"] for r in store.read(S.SUPPRESS)}
    referral = set()
    for p in store.read(S.PARTNERS):
        referral.update(x for x in re.split(r"[\s,、]+", str(p.get("紹介可能企業(法人番号)", ""))) if x)
    rows = store.read(S.MASTER)
    for r in rows:
        key = str(r["法人番号"])
        if key in referral:
            r["紹介可能性"] = "あり（07_士業・紹介パートナー参照）"
        has_ref = str(r.get("紹介可能性", "")).startswith("あり")
        total, b = score(r, settings, has_ref)
        r["スコア"], r["ランク"] = total, rank(total, settings)
        r["スコア内訳"] = " / ".join(f"{k}{v}" for k, v in b.items())
        r["対象区分"], r["追加調査理由"] = classify(
            r, settings, key in suppressed, not key.startswith("仮-"))
        if key in suppressed:
            r["営業ステータス"] = "営業停止"
        r["営業仮説"], r["推奨アプローチ"] = hypothesis(r), approach(r)
        r["入口提案"] = plays.PLAYS[plays.select(r)[0]["key"]][0]
    store.write(S.MASTER, rows)

    b_min = settings["ranks"]["B"]
    cand = [r for r in rows if r["対象区分"] == "確定対象" and r["スコア"] >= b_min]
    cand.sort(key=lambda r: (not str(r.get("紹介可能性", "")).startswith("あり"), -r["スコア"],
                             to_int(r["移動時間(分)"]) or 999))
    pri = []
    for i, r in enumerate(cand, 1):
        contact = " / ".join(str(r[c]) for c in ("公開担当部署", "代表電話", "公開メール")
                             if not is_unknown(r.get(c)))
        pri.append({**{c: r.get(c, "") for c in S.SHEETS[S.PRIORITY]}, "順位": i,
                    "接触先": contact or S.UNKNOWN,
                    "最初の一言": plays.PLAYS[plays.select(r)[0]["key"]][4]})
    store.write(S.PRIORITY, pri)
    plays.build_list(store)
    stat = {k: sum(1 for r in rows if r["対象区分"] == k) for k in S.TARGET_CLASSES}
    stat.update({f"ランク{k}": sum(1 for r in cand if r["ランク"] == k) for k in "SAB"})
    return stat


def import_files(paths: list[Path], store: Store, settings: dict) -> dict:
    """調査JSONを検証して企業マスターへ冪等に取り込む。"""
    res = {"insert": 0, "update": 0, "rejected": []}
    seen = set()
    for p in paths:
        for rec in json.loads(Path(p).read_text(encoding="utf-8")):
            errs = validate_record(rec)
            if errs:
                res["rejected"].append({"name": rec.get("name"), "file": Path(p).name, "errors": errs})
                log.warning("取り込み拒否 %s: %s", rec.get("name"), "; ".join(errs))
                continue
            row, _ = to_master_row(rec, settings)
            if row["法人番号"] in seen:
                continue
            seen.add(row["法人番号"])
            res[store.upsert(S.MASTER, row, keep=S.MASTER_HUMAN_COLUMNS)] += 1
    res["stats"] = rescore(store, settings)
    log.info("調査取り込み: 新規%d 更新%d 拒否%d", res["insert"], res["update"], len(res["rejected"]))
    return res


# ---------- gBizINFO（トークン設定時のみ） ----------
class GBizClient:
    """gBizINFO REST API。利用規約に従い、間隔を空けて呼び出し、月間上限を守る。"""

    def __init__(self, token: str, settings: dict, budget: Budget, session=None):
        if not token:
            raise RuntimeError("GBIZINFO_API_TOKEN が未設定です（.env.example 参照）")
        import requests
        self.s = session or requests.Session()
        self.token, self.conf, self.budget = token, settings["gbizinfo"], budget
        self._last = 0.0

    def _get(self, url: str, params: dict | None = None) -> dict:
        self.budget.charge("gbizinfo")
        wait = self.conf["min_interval_sec"] - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            r = self.s.get(url, params=params, timeout=30,
                           headers={"X-hojinInfo-api-token": self.token, "Accept": "application/json"})
            self._last = time.time()
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))  # 制限には待機で従う（回避しない）
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"gBizINFO 応答エラー: HTTP {r.status_code}")

    def search(self, prefecture: str = "13", city: str = "", emp_from: int = 30,
               emp_to: int = 300, page: int = 1) -> list[dict]:
        params = {"prefecture": prefecture, "employee_number_from": emp_from,
                  "employee_number_to": emp_to, "exist_flg": "true", "page": page, "limit": 100}
        if city:
            params["city"] = city
        return self._get(self.conf["base_url"], params).get("hojin-infos", [])

    def to_record(self, h: dict) -> dict:
        """API応答を調査レコード形式へ。APIにない項目は未確認のまま（Web調査で補完）。"""
        num = h.get("corporate_number", "")
        url = f"https://info.gbiz.go.jp/hojin/ichiran?hojinBango={num}"
        return {"corporate_number": num, "corporate_number_url": url, "name": h.get("name"),
                "address": h.get("location"), "employees": h.get("employee_number"),
                "employees_as_of": f"gBizINFO更新日 {h.get('update_date', '')[:10]}",
                "employees_url": url, "website": h.get("company_url") or S.UNKNOWN,
                "business_summary": (h.get("business_summary") or S.UNKNOWN)[:80],
                "representative": h.get("representative_name") or S.UNKNOWN,
                "sources": [{"url": url, "what": "gBizINFO 法人基本情報"}],
                "verified_date": today()}


# ---------- 出典の再照合（抜き取り検証） ----------
def verify_sources(paths: list[Path], budget: Budget | None = None, session=None) -> list[dict]:
    """従業員数が出典ページに実際に記載されているかを再取得して照合する（1社1リクエスト・間隔2秒）。"""
    import requests
    s = session or requests.Session()
    out = []
    for p in paths:
        for rec in json.loads(Path(p).read_text(encoding="utf-8")):
            emp, url = to_int(rec.get("employees")), str(rec.get("employees_url", ""))
            if emp is None or not URL_RE.match(url):
                out.append({"name": rec.get("name"), "result": "対象外（従業員数未確認）"})
                continue
            if budget:
                budget.charge("websearch")
            try:
                r = s.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0 (compatible; sfs-verify)"})
                r.encoding = r.apparent_encoding
                text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
                ok = bool(re.search(rf"(?<![\d,]){emp:,}\s*(名|人)|(?<![\d,]){emp}\s*(名|人)", text))
                res = "一致" if ok else f"要目視確認（HTTP {r.status_code}・本文に「{emp}名/人」なし）"
            except requests.RequestException as e:
                res = f"取得失敗（{type(e).__name__}）"
            out.append({"name": rec.get("name"), "employees": emp, "url": url, "result": res})
            if session is None:
                time.sleep(2)
    return out
