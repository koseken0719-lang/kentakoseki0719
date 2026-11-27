"""入口提案（プレイ）の選定。

「福利厚生FP相談を導入しませんか」ではなく、相手がすでに抱えている用事
（DCの継続投資教育・安全大会の講師・新入社員研修・定年前説明など）に乗る提案を、
公開情報の記載を根拠に企業ごとに選ぶ。根拠が公開情報にあるものと、業種からの仮説を区別する。
"""
from __future__ import annotations

import re

from . import schema as S
from .core import Store, is_unknown, to_int

CONFIRMED, HYPO = "公開情報に記載あり", "業種・規模からの仮説（要ヒアリング）"

# key: (名称, 相手にとっての用事, 経営者への切り口, 提案時期, 最初の一言)
PLAYS = {
    "partner": ("パートナー提携（顧問先向け共催セミナー・相互紹介）",
                "顧問先への付加価値づくり。職員の福利厚生としても利用可",
                "顧問先の「社員が辞める・採れない」相談に、費用ゼロで出せる打ち手を1つ増やせる",
                "通年（決算・年末調整の繁忙期を避ける）",
                "顧問先の従業員向けに、無料のお金のセミナーを共催しませんか。先生方の顧問先サービスの一つとしてお使いいただけます。"),
    "dc": ("企業型DCの継続投資教育セミナー（無料・60分）",
           "確定拠出年金法で事業主の努力義務とされる継続投資教育。未実施・形骸化している企業が多い",
           "せっかく会社が掛金を出しているDCを、社員が「福利厚生」として実感できるようにする",
           "通年（新入社員の加入時期の4〜5月、または下期の10〜11月が通しやすい）",
           "御社の確定拠出年金について、従業員向けの継続投資教育を無料で代行できます。法令上の努力義務への対応としてお使いください。"),
    "safety": ("安全大会・安全衛生協議会での講話（無料・30分）",
               "毎年の安全大会の講師探し。テーマは「お金の不安と不注意災害」「家計トラブルの予防」",
               "若手・職人の定着と、金銭トラブルによる離職・事故の予防",
               "4〜5月に提案（全国安全週間 7/1〜7 前後の開催が多い）。年度末の協力会総会も候補",
               "今年の安全大会の講話枠で、30分のお金の話を無料でお引き受けできます。講師のご予定はもうお決まりでしょうか。"),
    "preretire": ("50代向け 定年前ライフプランセミナー（無料・60〜90分）",
                  "再雇用・退職金・年金の説明を総務が個別に受けている負担の軽減",
                  "ベテランが安心して働き続けられる環境づくりと、技能承継期間の確保",
                  "通年（定年到達者が多い年度末の前、10〜1月が通しやすい）",
                  "50代の社員の方向けに、退職金・再雇用・年金を整理するセミナーを無料で実施できます。総務へのご質問が減ったとのお声をいただく内容です。"),
    "newhire": ("新入社員研修の1コマ（給与明細・社会保険・NISAの基礎／無料・60分）",
                "4月研修のコンテンツ。社会人1年目の金銭トラブル予防と、会社の制度説明",
                "新卒の早期離職の予防。「手取り」だけで他社と比較されないよう、総報酬を最初に伝える",
                "12〜2月に提案（4月研修の内容確定前）",
                "来春の新入社員研修で、給与明細の読み方と会社の制度を説明する1コマを無料で担当できます。研修の内容はこれからお決めになる時期でしょうか。"),
    "totalreward": ("自社制度の価値を伝える社内説明会（退職金・財形等の見える化／無料・45分）",
                    "制度はあるのに社員に価値が伝わっていない。求人票・面接での説明にも使える",
                    "賃上げをせずに、今すでに払っている報酬（退職金・会社負担の社会保険料等）の価値を伝える",
                    "通年（昇給・賞与の時期、または年末調整期が通しやすい）",
                    "御社の退職金や財形などの制度を、社員の方に「いくら分の価値か」で説明する会を無料で実施できます。"),
    "survey": ("従業員マネー意識アンケート（匿名5問・無料診断）",
               "社員が何に不安を感じているかの把握。健康経営・エンゲージメント施策の基礎資料",
               "離職理由になりやすい「お金の不安」を数字で把握し、打ち手を決める材料にする",
               "通年",
               "従業員の方がお金のどこに不安を感じているか、匿名5問のアンケートで無料診断できます。結果は集計レポートでお返しします。"),
}

DC_RE = re.compile(r"確定拠出|企業型\s*DC|\bDC\b|401\s*k", re.I)
ASSET_RE = re.compile(r"退職金|財形|持株|中退共|企業年金")
# 「第二新卒歓迎」「新卒/中途の区分記載なし」は新卒採用の根拠にしない
NEWGRAD_RE = re.compile(r"(?<!第二)新卒(?![^。、]{0,12}(記載なし|未確認|問わず))")
CERT_RE = re.compile(r"健康経営|くるみん|えるぼし|ユースエール")


def _snip(text: str, pat: re.Pattern | str, width: int = 28) -> str:
    m = re.search(pat, text)
    if not m:
        return ""
    s = text[max(0, m.start() - width):m.end() + width].replace("\n", " ")
    return f"「…{s}…」"


def select(row: dict) -> list[dict]:
    """該当する入口提案を優先順に返す（根拠の記載があるものを先に）。"""
    wel, rec, ret = (str(row.get(k, "")) for k in ("福利厚生情報", "採用情報", "人材定着の取組"))
    cert, ind = str(row.get("認定・健康経営", "")), row.get("業種", "")
    out = []

    def add(key, basis, evidence, url=""):
        url = "" if is_unknown(url) else f"（{url}）"
        out.append({"key": key, "basis": basis, "evidence": evidence + url})

    if ind == "税理士法人":
        add("partner", CONFIRMED, "税理士法人（顧問先を持つ士業）", row.get("公式サイト"))
    if DC_RE.search(wel):
        add("dc", CONFIRMED, "福利厚生に確定拠出年金の記載 " + _snip(wel, DC_RE), row.get("福利厚生URL"))
    if "安全大会" in wel + ret + str(row.get("地域活動", "")):
        add("safety", CONFIRMED, "安全大会の開催を公開 " + _snip(wel + ret + str(row.get("地域活動", "")), "安全大会"))
    age = re.search(r"平均年齢\s*([\d.]+)", ret + rec + wel)
    if age and float(age.group(1)) >= 45:
        add("preretire", CONFIRMED, f"平均年齢{age.group(1)}歳と公開 " + _snip(ret + rec + wel, "平均年齢"), row.get("採用URL"))
    if NEWGRAD_RE.search(rec) and not rec.startswith("募集なし"):
        add("newhire", CONFIRMED, "新卒採用を実施 " + _snip(rec, NEWGRAD_RE), row.get("採用URL"))
    if ind in ("建設業", "設備工事業") and not any(p["key"] == "safety" for p in out):
        add("safety", HYPO, "建設・設備工事業は安全大会を毎年開催するのが一般的（同社での開催は未確認）")
    if ASSET_RE.search(wel):
        add("totalreward", CONFIRMED, "制度の記載あり " + _snip(wel, ASSET_RE), row.get("福利厚生URL"))
    sv = "認定を取得 " + _snip(cert, CERT_RE) if CERT_RE.search(cert) else "全業種に提案可能な無料診断"
    add("survey", CONFIRMED if CERT_RE.search(cert) else HYPO, sv)
    return out


def route(row: dict) -> str:
    """接触経路。紹介を最優先し、営業お断り表記のある窓口は使わない。"""
    if str(row.get("紹介可能性", "")).startswith("あり"):
        return "①紹介（07_士業・紹介パートナー経由）で依頼"
    steps = ["①紹介経路を探す（既存顧客の勤務先／社労士・税理士／地域金融機関・商工会）"]
    if str(row.get("営業お断り表記", "")).startswith("あり"):
        return steps[0] + "　②紹介が得られない場合は接触しない（営業お断りの表記あり）"
    owner = "オーナー経営" in str(row.get("代表者(公開情報)", ""))
    dept = row.get("公開担当部署")
    to = "社長宛て" if owner else ("総務・人事ご担当宛て" if is_unknown(dept) else f"{dept}宛て")
    steps.append(f"②{to}に入口提案1件だけを書いた手紙（A4・1枚）")
    if not is_unknown(row.get("代表電話")):
        steps.append("③到着確認の電話（提案の可否だけを聞く）")
    return "　".join(steps)


def caution(row: dict) -> str:
    c = []
    if row.get("対象区分") == "追加調査":
        c.append(f"追加調査中（{row.get('追加調査理由', '')}）。確認後に着手")
    if str(row.get("営業お断り表記", "")).startswith("あり"):
        c.append("営業お断りの表記あり。該当窓口は使用禁止")
    if str(row.get("法人番号", "")).startswith("仮-"):
        c.append("法人番号未確認")
    emp = to_int(row.get("従業員数"))
    if emp and emp > 100:
        c.append("100名超（理想レンジ外）")
    return "／".join(c)


def build_list(store: Store) -> list[dict]:
    """11_入口提案リスト を再生成（営業停止・対象外は除外）。"""
    rows = []
    for r in store.read(S.MASTER):
        if r.get("対象区分") in ("営業停止", "対象外"):
            continue
        ps = select(r)
        p1, p2 = ps[0], (ps[1] if len(ps) > 1 else None)
        name, need, angle, timing, opener = PLAYS[p1["key"]]
        rows.append({
            "法人番号": r["法人番号"], "企業名": r["企業名"], "市区": r["市区"], "業種": r["業種"],
            "従業員数": r["従業員数"], "対象区分": r["対象区分"], "スコア": r["スコア"],
            "入口提案（第1候補）": name, "根拠区分": p1["basis"], "根拠（公開情報の該当記載）": p1["evidence"],
            "相手にとっての用事": need, "経営者への切り口": angle, "最初の一言": opener, "提案時期": timing,
            "入口提案（第2候補）": PLAYS[p2["key"]][0] + f"［{p2['basis']}］" if p2 else "",
            "接触経路": route(r), "注意点": caution(r)})
    rows.sort(key=lambda x: (x["対象区分"] != "確定対象", x["根拠区分"] != CONFIRMED, -int(x["スコア"])))
    for i, x in enumerate(rows, 1):
        x["優先順"] = i
    store.write(S.PLAYS, rows)
    return rows
