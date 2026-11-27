"""営業管理：活動履歴、営業停止、フォローアップ、日次タスク、週次・月次KPIと改善提案。"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from . import schema as S
from .core import Store, get_logger, is_unknown, to_int, today

log = get_logger()
REPLIED = {"返信あり", "アポ獲得"}
OUTBOUND_EXCLUDE = {"下書き"}  # 下書きは未送信なのでアプローチ数に数えない


def _d(s: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s)[:10].replace("/", "-"))
    except ValueError:
        return None


def is_suppressed(store: Store, corp: str) -> bool:
    return any(str(r["法人番号"]) == str(corp) for r in store.read(S.SUPPRESS))


def suppress(store: Store, corp: str, reason: str, route: str = "", note: str = "",
             channels: str = "全て") -> None:
    """営業停止リストに登録（冪等）。企業マスターのステータスも営業停止にする。"""
    if reason not in S.SUPPRESS_REASONS:
        raise ValueError(f"理由は {S.SUPPRESS_REASONS} から選択してください")
    master = store.read(S.MASTER)
    name = next((r["企業名"] for r in master if str(r["法人番号"]) == str(corp)), S.UNKNOWN)
    store.upsert(S.SUPPRESS, {"法人番号": corp, "企業名": name, "登録日": today(), "理由": reason,
                              "経路": route, "対象チャネル": channels, "備考": note}, keep=["登録日"])
    for r in master:
        if str(r["法人番号"]) == str(corp):
            r.update({"営業ステータス": "営業停止", "対象区分": "営業停止", "次回アクション日": ""})
    store.write(S.MASTER, master)
    store.write(S.PRIORITY, [r for r in store.read(S.PRIORITY) if str(r["法人番号"]) != str(corp)])
    log.info("営業停止登録: %s（%s）", corp, reason)


def log_activity(store: Store, settings: dict, corp: str, channel: str, result: str,
                 content: str = "", date: str | None = None, approver: str = "",
                 cost: int = 0, note: str = "", seq: int | None = None) -> dict:
    """営業活動を記録（活動IDで冪等）。受信拒否は自動で営業停止リストへ。"""
    if channel not in S.CHANNELS or result not in S.RESULTS:
        raise ValueError(f"チャネルは{S.CHANNELS}、結果は{S.RESULTS}から選択してください")
    if is_suppressed(store, corp) and result not in ("受信拒否", "辞退"):
        raise PermissionError(f"{corp} は営業停止リスト登録済みのため、活動を記録・実施できません")
    master = store.read(S.MASTER)
    m = next((r for r in master if str(r["法人番号"]) == str(corp)), None)
    if m is None:
        raise KeyError(f"企業マスターに {corp} がありません")
    if channel == "フォーム" and str(m.get("営業お断り表記", "")).startswith("あり"):
        raise PermissionError("営業お断り表記のある問い合わせフォームは使用できません")
    date = date or today()
    acts = [a for a in store.read(S.ACTIVITY) if str(a["法人番号"]) == str(corp)]
    n = seq or len(acts) + 1
    acts = [a for a in acts if a["活動ID"] != f"{corp}-{n:02d}"]  # 同一IDの再実行は上書き（冪等）
    sent = [a for a in acts if a["結果"] not in OUTBOUND_EXCLUDE]
    steps = settings["followup"]["steps"]
    touch = len(sent) + (0 if result in OUTBOUND_EXCLUDE else 1)
    nxt, nxt_date = "", ""
    if result in ("未返信", "不在") and touch < min(len(steps), settings["followup"]["max_touches"]):
        first = min([_d(a["日付"]) for a in sent if _d(a["日付"])] + [_d(date)])
        st = steps[touch]
        nxt, nxt_date = st["label"], max(first + dt.timedelta(days=st["after_days"]),
                                         _d(date) + dt.timedelta(days=1)).isoformat()
    elif result == "下書き":
        nxt, nxt_date = "下書きを確認・承認して送信", date
    elif result in REPLIED:
        nxt, nxt_date = "商談日程の調整・04_法人商談管理へ登録", date
    row = {"活動ID": f"{corp}-{n:02d}", "日付": date, "法人番号": corp, "企業名": m["企業名"],
           "チャネル": channel, "内容": content, "結果": result,
           "送信承認": "未" if result == "下書き" else "済", "承認者": approver,
           "次回アクション": nxt, "次回アクション日": nxt_date, "費用(円)": cost, "備考": note}
    store.upsert(S.ACTIVITY, row)
    status = {"下書き": "下書き作成済", "未返信": "アプローチ中", "不在": "アプローチ中",
              "返信あり": "返信あり", "アポ獲得": "商談設定", "辞退": "見送り", "受信拒否": "営業停止"}[result]
    if result in ("未返信", "不在") and not nxt:
        status = "ナーチャリング"
    m.update({"営業ステータス": status, "次回アクション日": nxt_date, "最終更新日": today()})
    store.write(S.MASTER, master)
    pri = store.read(S.PRIORITY)
    for p in pri:
        if str(p["法人番号"]) == str(corp):
            p.update({"営業ステータス": status, "次回アクション日": nxt_date})
    store.write(S.PRIORITY, pri)
    if result == "受信拒否":
        suppress(store, corp, "受信拒否", route=channel, note=note)
    return row


def daily_tasks(store: Store, settings: dict, on: str | None = None, new_quota: int = 15) -> str:
    """本日の営業タスク（期限到来フォロー＋新規着手候補）をMarkdownで返す。"""
    d = _d(on or today())
    suppressed = {str(r["法人番号"]) for r in store.read(S.SUPPRESS)}
    master = [r for r in store.read(S.MASTER) if str(r["法人番号"]) not in suppressed]
    due = [r for r in master if _d(r.get("次回アクション日", "")) and _d(r["次回アクション日"]) <= d
           and r.get("営業ステータス") not in ("見送り", "営業停止", "導入決定")]
    latest = {}
    for a in store.read(S.ACTIVITY):
        latest[str(a["法人番号"])] = a
    fresh = [p for p in store.read(S.PRIORITY)
             if p.get("営業ステータス") in ("未着手", "") and str(p["法人番号"]) not in suppressed]
    deals = [x for x in store.read(S.DEALS) if _d(x.get("次回予定日", "")) and _d(x["次回予定日"]) <= d
             and x.get("フェーズ") not in ("導入決定", "見送り")]
    out = [f"# 本日の営業タスク（{d.isoformat()}）", ""]
    if not settings["compliance"]["agency_approved"]:
        out += ["> ⚠ 所属代理店の承認が未登録です。外部への送信・架電は承認後に開始してください。", ""]
    out += [f"## 1. フォローアップ期限到来（{len(due)}件）"]
    for r in sorted(due, key=lambda r: r["次回アクション日"]):
        a = latest.get(str(r["法人番号"]), {})
        out.append(f"- [ ] {r['企業名']}（{r['ランク']}／{r['営業ステータス']}）：{a.get('次回アクション', '要確認')}"
                   f"［期限 {r['次回アクション日']}・前回 {a.get('チャネル', '-')} {a.get('結果', '-')}］")
    out += ["", f"## 2. 商談フォロー（{len(deals)}件）"]
    out += [f"- [ ] {x['企業名']}（{x['フェーズ']}）：{x.get('次のステップ', '')}" for x in deals]
    out += ["", f"## 3. 新規着手候補（上位{min(new_quota, len(fresh))}社／未着手{len(fresh)}社）"]
    for p in fresh[:new_quota]:
        out.append(f"- [ ] {p['順位']}位 {p['企業名']}（{p['ランク']} {p['スコア']}点・{p['市区']}・"
                   f"{p['従業員数']}名）：{p['推奨アプローチ']}")
    out += ["", "※送信・投函前に、営業キットの内容と最新の公開情報を確認し、承認者を 03_営業活動履歴 に記録すること。"]
    return "\n".join(out) + "\n"


# ---------- KPI ----------
def _pct(a: float, b: float) -> float | None:
    return round(a / b * 100, 1) if b else None


def metrics(store: Store, start: dt.date, end: dt.date) -> dict:
    """期間[start, end]のKPI。分母0の率は None（データなし）とし、0%と区別する。"""
    inr = lambda s: (x := _d(s)) is not None and start <= x <= end
    master = store.read(S.MASTER)
    mi = {str(r["法人番号"]): r for r in master}
    acts = [a for a in store.read(S.ACTIVITY) if inr(a["日付"]) and a["結果"] not in OUTBOUND_EXCLUDE]
    deals = [x for x in store.read(S.DEALS) if inr(x["商談日"])]
    adopted = [x for x in store.read(S.ADOPTED) if inr(x["導入決定日"])]
    months = {f"{start.year}-{m:02d}" for m in range(start.month, end.month + 1)} \
        if start.year == end.year else {start.isoformat()[:7], end.isoformat()[:7]}
    cons = [c for c in store.read(S.CONSULT) if str(c["年月"])[:7] in months]
    approached = {str(a["法人番号"]) for a in acts}
    replied = {str(a["法人番号"]) for a in acts if a["結果"] in REPLIED}
    met = {str(x["法人番号"]) for x in deals}
    booked = sum(to_int(c["予約件数"]) or 0 for c in cons)
    done = sum(to_int(c["実施件数"]) or 0 for c in cons)
    live = [x for x in store.read(S.ADOPTED) if x.get("ステータス") in ("稼働中", "準備中")]
    covered = sum(to_int(x["対象従業員数"]) or 0 for x in live)
    cost = sum(to_int(a.get("費用(円)")) or 0 for a in acts)

    def breakdown(keyfn):
        g = defaultdict(lambda: {"アプローチ": set(), "返信": set(), "商談": set(), "導入": set()})
        for a in acts:
            k = keyfn(a)
            g[k]["アプローチ"].add(str(a["法人番号"]))
            if a["結果"] in REPLIED:
                g[k]["返信"].add(str(a["法人番号"]))
        return g

    by_ch = breakdown(lambda a: a["チャネル"])
    by_ind = breakdown(lambda a: mi.get(str(a["法人番号"]), {}).get("業種", S.UNKNOWN))
    by_area = breakdown(lambda a: mi.get(str(a["法人番号"]), {}).get("市区", S.UNKNOWN))
    for x in deals:
        m = mi.get(str(x["法人番号"]), {})
        by_ch[x.get("獲得チャネル") or S.UNKNOWN]["商談"].add(str(x["法人番号"]))
        by_ind[m.get("業種", S.UNKNOWN)]["商談"].add(str(x["法人番号"]))
        by_area[m.get("市区", S.UNKNOWN)]["商談"].add(str(x["法人番号"]))
    for x in adopted:
        m = mi.get(str(x["法人番号"]), {})
        by_ind[m.get("業種", S.UNKNOWN)]["導入"].add(str(x["法人番号"]))
        by_area[m.get("市区", S.UNKNOWN)]["導入"].add(str(x["法人番号"]))
    flat = lambda g: {k: {m: len(v) for m, v in d.items()} for k, d in g.items()}
    return {
        "期間": f"{start}〜{end}",
        "新規企業発掘数": sum(1 for r in master if inr(r.get("初回登録日", ""))),
        "確定対象数": sum(1 for r in master if inr(r.get("初回登録日", "")) and r.get("対象区分") == "確定対象"),
        "法人アプローチ数": len(approached), "アプローチ件数(延べ)": len(acts),
        "返信社数": len(replied), "返信率": _pct(len(replied), len(approached)),
        "法人商談数": len(met), "法人商談化率": _pct(len(met), len(approached)),
        "新規導入数": len(adopted), "福利厚生導入率": _pct(len(adopted), len(met)),
        "利用対象従業員数(累計)": covered, "導入企業数(累計)": len(live),
        "FP相談予約件数": booked, "FP相談実施件数": done,
        "FP相談利用率": _pct(done, covered),
        "営業費用(円)": cost, "実施面談1件あたり獲得原価(円)": round(cost / done) if done else None,
        "チャネル別": flat(by_ch), "業種別": flat(by_ind), "地域別": flat(by_area),
    }


def diagnose(m: dict, settings: dict, monthly: bool = True) -> list[tuple[str, str, str]]:
    """(課題, 想定原因, 改善案) のリスト。データがない指標は「判定不能」と明示する。"""
    t, scale = settings["targets"], 1 if monthly else 12 / 52
    out = []
    if m["法人アプローチ数"] == 0:
        return [("アプローチ実績なし", "送信・架電が未実施、または 03_営業活動履歴 への記録漏れ",
                 "所属代理店の承認状況を確認し、優先営業リスト上位から下書きを承認・送信する。実施分は必ず活動履歴に記録する")]
    if m["法人アプローチ数"] < t["monthly_outreach"] * scale * 0.7:
        out.append((f"アプローチ数が目標の7割未満（{m['法人アプローチ数']}社）",
                    "確定対象の在庫不足、または承認・送信の作業時間不足",
                    "月曜の調査で確定対象を補充。下書き承認を毎朝15分に固定し、郵送は週1回まとめて投函する"))
    if m["返信率"] is not None and m["返信率"] < 3:
        out.append((f"返信率が低い（{m['返信率']}%）", "件名・冒頭が汎用的／宛先が代表アドレスのみ／メール単独で電話フォローがない",
                    "企業固有の一文（採用・認定）を冒頭に置く。初回接触の4日後に電話フォローを徹底。オーナー企業は郵送を先行させる"))
    if m["法人商談化率"] is not None and m["法人商談化率"] < t["monthly_meetings"] / t["monthly_outreach"] * 100:
        out.append((f"商談化率が目標未満（{m['法人商談化率']}%）", "返信後の日程提示が遅い／紹介経由の比率が低い",
                    "返信当日に候補日3つを提示。07_士業・紹介パートナーへの紹介依頼を週2件行う"))
    if m["福利厚生導入率"] is not None and m["福利厚生導入率"] < t["monthly_adoptions"] / t["monthly_meetings"] * 100:
        out.append((f"導入率が目標未満（{m['福利厚生導入率']}%）", "無料の理由・情報の取扱いへの懸念が解消できていない／決裁者不在の商談",
                    "商談資料に「無料の理由」「会社への非開示」「運用負担ゼロ」を1枚で明示。初回から決裁者同席を依頼する"))
    if m["利用対象従業員数(累計)"] and (m["FP相談利用率"] or 0) < 1.3:
        out.append((f"FP相談利用率が低い（{m['FP相談利用率']}%）", "社内告知が1回のみ／予約導線が分かりにくい",
                    "導入企業へ告知文の再送（給与明細配布時期・年末調整期）と社内説明会30分を提案する"))
    for name, g in (("チャネル", m["チャネル別"]), ("業種", m["業種別"]), ("地域", m["地域別"])):
        for k, v in g.items():
            if v["アプローチ"] >= 10 and v["返信"] == 0:
                out.append((f"{name}「{k}」は{v['アプローチ']}社に接触して返信0",
                            "訴求と対象のミスマッチ、または接触手段が不適切",
                            f"翌月は{name}「{k}」の配分を半減し、返信のあった区分へ振り替える。文面を1案だけ変えて比較する"))
    return out or [("大きな未達なし", "-", "現行施策を継続し、返信のあった業種・地域の配分を1〜2割増やす")]


def week_start(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())


def weekly_report(store: Store, settings: dict, on: str | None = None) -> dict:
    """金曜実行。当週（月〜日）のKPIと改善案を 09_週次改善レポート に冪等で記録。"""
    d = _d(on or today())
    ws = week_start(d)
    m = metrics(store, ws, ws + dt.timedelta(days=6))
    diag = diagnose(m, settings, monthly=False)
    row = {"週(月曜日)": ws.isoformat(), "新規調査数": m["新規企業発掘数"], "確定対象数": m["確定対象数"],
           "アプローチ数": m["法人アプローチ数"], "返信数": m["返信社数"],
           "返信率(%)": "データなし" if m["返信率"] is None else m["返信率"],
           "商談数": m["法人商談数"], "導入数": m["新規導入数"],
           "所見": "／".join(f"{a}（{b}）" for a, b, _ in diag),
           "改善案": "／".join(c for _, _, c in diag),
           "翌週アクション": f"月曜：新規{settings['targets']['weekly_new_research']}社調査、"
                       f"平日：下書き承認とフォロー（目安 週{round(settings['targets']['monthly_outreach'] / 4.3)}社）"}
    store.upsert(S.WEEKLY, row)
    return row


def monthly_report(store: Store, settings: dict, ym: str | None = None) -> str:
    ym = ym or today()[:7]
    y, mo = map(int, ym.split("-"))
    start = dt.date(y, mo, 1)
    end = (dt.date(y + mo // 12, mo % 12 + 1, 1) - dt.timedelta(days=1))
    m, t = metrics(store, start, end), settings["targets"]
    f = lambda v, u="": "データなし" if v is None else f"{v:,}{u}" if isinstance(v, (int, float)) else str(v)
    rows = [("新規企業発掘数", f(m["新規企業発掘数"], "社"), f"{t['weekly_new_research'] * 4}社"),
            ("法人アプローチ数", f(m["法人アプローチ数"], "社"), f"{t['monthly_outreach']}社"),
            ("返信率", f(m["返信率"], "%"), "-"),
            ("法人商談数／商談化率", f"{m['法人商談数']}件／{f(m['法人商談化率'], '%')}", f"{t['monthly_meetings']}件"),
            ("新規導入数／導入率", f"{m['新規導入数']}社／{f(m['福利厚生導入率'], '%')}", f"{t['monthly_adoptions']}社"),
            ("導入企業数（累計）", f(m["導入企業数(累計)"], "社"), f"{t['adopted_companies']}社"),
            ("利用対象従業員数（累計）", f(m["利用対象従業員数(累計)"], "名"), f"{t['covered_employees']:,}名"),
            ("FP相談予約件数", f(m["FP相談予約件数"], "件"), "-"),
            ("FP相談実施件数", f(m["FP相談実施件数"], "件"), f"{t['monthly_consultations']}件"),
            ("FP相談利用率（実施÷対象従業員）", f(m["FP相談利用率"], "%"), "-"),
            ("実施面談1件あたり獲得原価", f(m["実施面談1件あたり獲得原価(円)"], "円"), "-")]
    out = [f"# 月次営業レポート {ym}", "", f"集計期間：{m['期間']}（03〜06シートの記録に基づく実績。記録のない指標は「データなし」）", "",
           "| 指標 | 実績 | 月間目標（初期仮説） |", "|---|---|---|"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    for title, g in (("営業チャネル別", m["チャネル別"]), ("業種別", m["業種別"]), ("地域別", m["地域別"])):
        out += ["", f"## {title}", "", "| 区分 | アプローチ社数 | 返信 | 商談 | 導入 |", "|---|---|---|---|---|"]
        out += [f"| {k} | {v['アプローチ']} | {v['返信']} | {v['商談']} | {v['導入']} |"
                for k, v in sorted(g.items(), key=lambda x: -x[1]["アプローチ"])] or ["| （実績なし） | - | - | - | - |"]
    out += ["", "## 課題・原因分析と翌月の改善案", "", "| 課題 | 想定原因 | 翌月の改善案 |", "|---|---|---|"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in diagnose(m, settings)]
    return "\n".join(out) + "\n"
