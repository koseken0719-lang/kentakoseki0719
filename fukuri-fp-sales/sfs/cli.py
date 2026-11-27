"""コマンドライン入口： python -m sfs <command>"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import forms, google_api, sourcing, onboarding, outreach, pipeline, research, workbook
from . import schema as S
from .core import ROOT, Budget, BudgetExceeded, Store, get_logger, load_dotenv, load_settings, today

log = get_logger()


def _out(name: str, text: str) -> Path:
    p = ROOT / "output" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def cmd_doctor(a, store, st):
    checks = [
        ("所属代理店の承認（実運用の必須条件）", st["compliance"]["agency_approved"]),
        ("差出人情報の記入（settings.yaml sender）", not any("（" in str(v) for v in st["sender"].values())),
        ("SFS_SPREADSHEET_ID", bool(os.environ.get("SFS_SPREADSHEET_ID"))),
        ("Google認証（Sheets/Calendar: GOOGLE_APPLICATION_CREDENTIALS）", bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))),
        ("Gmail下書き用トークン（SFS_GMAIL_TOKEN_FILE）", bool(os.environ.get("SFS_GMAIL_TOKEN_FILE"))),
        ("gBizINFO APIトークン（GBIZINFO_API_TOKEN）", bool(os.environ.get("GBIZINFO_API_TOKEN"))),
    ]
    for name, ok in checks:
        print(f"[{'OK' if ok else '未設定'}] {name}")
    print("API利用状況（当月）:", json.dumps(Budget(st, store.dir).usage(), ensure_ascii=False))
    print("企業マスター件数:", len(store.read(S.MASTER)))
    print("※Python用のGoogle認証が未設定でも、Claude Codeのコネクタ（Sheets/Gmail/Calendar）経由で運用できます。")


def cmd_research_import(a, store, st):
    files = [Path(f) for f in a.files] or sorted((ROOT / "data" / "research").glob("*.json"))
    res = research.import_files(files, store, st)
    print(json.dumps(res, ensure_ascii=False, indent=1))


def cmd_research_gbiz(a, store, st):
    cli = research.GBizClient(os.environ.get("GBIZINFO_API_TOKEN", ""), st, Budget(st, store.dir))
    known = {r["法人番号"] for r in store.read(S.MASTER)}
    recs = [cli.to_record(h) for h in cli.search(city=a.city, page=a.page)
            if h.get("corporate_number") not in known]
    p = ROOT / "data" / "research" / f"gbiz_{a.city or 'tokyo'}_{today()}_p{a.page}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(recs)}社の候補を保存: {p}（公式サイト・アクセス等はWeb調査で補完してから import）")


def cmd_values(a, store, st):
    if a.direction == "export":
        v = store.to_values(a.sheet)
        if a.out:
            Path(a.out).write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
        print(f"{a.sheet}: {len(v) - 1}行" if a.out else json.dumps(v, ensure_ascii=False))
    else:
        n = store.from_values(a.sheet, json.loads(Path(a.file).read_text(encoding="utf-8")))
        print(f"{a.sheet}: {n}行を取り込み")


def main(argv=None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="sfs", description="スフェノス 福利厚生FP相談 法人開拓システム")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="環境・認証・承認状況の確認")
    p = sub.add_parser("research-import", help="調査JSONを検証して企業マスターへ取り込み（冪等）")
    p.add_argument("files", nargs="*")
    p = sub.add_parser("research-gbiz", help="gBizINFOから候補企業を取得（要トークン）")
    p.add_argument("--city", default=""), p.add_argument("--page", type=int, default=1)
    p = sub.add_parser("verify-sources", help="従業員数を出典ページと再照合（抜き取り検証）")
    p.add_argument("files", nargs="*")
    p = sub.add_parser("source", help="公開リストから候補を収集（stage1: 規模判定／needs-site: サイト未特定の一覧／stage3: レコード化）")
    p.add_argument("step", choices=["stage1", "needs-site", "stage3"]), p.add_argument("--target", type=int, default=200)
    sub.add_parser("score", help="全社を再スコアリングし優先営業リストを再生成")
    p = sub.add_parser("outreach-build", help="企業別の営業キット（下書き）を生成")
    p.add_argument("--top", type=int)
    p = sub.add_parser("gmail-drafts", help="Gmail下書き作成（送信はしない。要代理店承認）")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("activity", help="営業活動を記録")
    for x in ("corp", "channel", "result"):
        p.add_argument(x)
    p.add_argument("--content", default=""), p.add_argument("--date"), p.add_argument("--approver", default="")
    p.add_argument("--cost", type=int, default=0), p.add_argument("--note", default="")
    p = sub.add_parser("suppress", help="営業停止リストへ登録（再接触しない）")
    p.add_argument("corp"), p.add_argument("reason"), p.add_argument("--route", default=""), p.add_argument("--note", default="")
    p = sub.add_parser("daily", help="本日の営業タスクを出力")
    p.add_argument("--date")
    p = sub.add_parser("weekly-report", help="週次改善レポート（金曜）")
    p.add_argument("--date")
    p = sub.add_parser("monthly-report", help="月次レポート（月末）")
    p.add_argument("--ym")
    p = sub.add_parser("onboard-register", help="導入企業として登録")
    p.add_argument("corp"), p.add_argument("--employees", type=int), p.add_argument("--dept", default="")
    p = sub.add_parser("onboard-build", help="導入企業向け資料一式を生成")
    p.add_argument("corp")
    p = sub.add_parser("consult-record", help="FP相談件数（集計値のみ）を記録")
    p.add_argument("ym"), p.add_argument("corp"), p.add_argument("booked", type=int), p.add_argument("done", type=int)
    p.add_argument("--cancelled", type=int, default=0), p.add_argument("--themes", default="{}")
    p = sub.add_parser("usage-report", help="企業向け月間利用実績レポート（集計のみ）")
    p.add_argument("ym"), p.add_argument("corp")
    sub.add_parser("export-xlsx", help="10シートのワークブックを出力")
    p = sub.add_parser("values", help="シートの2次元配列を入出力（コネクタ連携用）")
    p.add_argument("direction", choices=["export", "import"]), p.add_argument("sheet", choices=list(S.SHEETS))
    p.add_argument("--out"), p.add_argument("--file")
    p = sub.add_parser("sync", help="Google Sheets APIで同期（要認証）")
    p.add_argument("direction", choices=["pull", "push"])
    p = sub.add_parser("form-queue", help="13_フォーム営業キューを更新（--check でフォームを取得して判定）")
    p.add_argument("--check", action="store_true")
    p = sub.add_parser("form-send", help="承認済みの行をフォームに入力（既定は試行のみ。--send で送信）")
    p.add_argument("--send", action="store_true")
    sub.add_parser("form-report", help="フォーム営業の効果測定（文面パターン別・入口提案別）")
    sub.add_parser("calendar-followups", help="次回アクションをカレンダー登録（要認証）")

    a = ap.parse_args(argv)
    st, store = load_settings(), Store()
    try:
        c = a.cmd
        if c == "doctor":
            cmd_doctor(a, store, st)
        elif c == "research-import":
            cmd_research_import(a, store, st)
        elif c == "research-gbiz":
            cmd_research_gbiz(a, store, st)
        elif c == "verify-sources":
            files = [Path(f) for f in a.files] or sorted((ROOT / "data" / "research").glob("*.json"))
            res = research.verify_sources(files, Budget(st, store.dir))
            for r in res:
                print(f"{r['result']}\t{r['name']}\t{r.get('employees', '')}\t{r.get('url', '')}")
            print(f"一致 {sum(r['result'] == '一致' for r in res)} / 照合対象 {sum('employees' in r for r in res)}")
        elif c == "source":
            if a.step == "stage1":
                print(json.dumps(sourcing.stage1(store, st, Budget(st, store.dir), a.target), ensure_ascii=False))
            elif a.step == "needs-site":
                print(json.dumps(sourcing.needs_site(store, st), ensure_ascii=False, indent=1))
            else:
                print(json.dumps(sourcing.stage3(store, st, a.target), ensure_ascii=False))
        elif c == "score":
            print(json.dumps(research.rescore(store, st), ensure_ascii=False))
        elif c == "outreach-build":
            print(f"{len(outreach.build_kits(store, st, a.top))}社の営業キットを output/outreach/ に生成")
        elif c == "gmail-drafts":
            made = google_api.create_drafts(store, st, Budget(st, store.dir), limit=a.limit)
            print(json.dumps(made, ensure_ascii=False, indent=1))
        elif c == "activity":
            print(json.dumps(pipeline.log_activity(store, st, a.corp, a.channel, a.result, a.content, a.date,
                                                   a.approver, a.cost, a.note), ensure_ascii=False))
        elif c == "suppress":
            pipeline.suppress(store, a.corp, a.reason, a.route, a.note)
            print("営業停止リストに登録しました")
        elif c == "daily":
            print(_out(f"daily/{a.date or today()}_営業タスク.md", pipeline.daily_tasks(store, st, a.date)))
        elif c == "weekly-report":
            print(json.dumps(pipeline.weekly_report(store, st, a.date), ensure_ascii=False, indent=1))
        elif c == "monthly-report":
            ym = a.ym or today()[:7]
            print(_out(f"reports/{ym}_月次営業レポート.md", pipeline.monthly_report(store, st, ym)))
        elif c == "onboard-register":
            print(json.dumps(onboarding.register(store, st, a.corp, a.employees, a.dept), ensure_ascii=False))
        elif c == "onboard-build":
            for p_ in onboarding.build(store, st, a.corp):
                print(p_)
        elif c == "consult-record":
            print(json.dumps(onboarding.record_consult(store, st, a.ym, a.corp, a.booked, a.done, a.cancelled,
                                                       json.loads(a.themes)), ensure_ascii=False))
        elif c == "usage-report":
            code = onboarding.company_code(a.corp)
            print(_out(f"onboarding/{code}/{a.ym}_月間利用実績レポート.md",
                       onboarding.usage_report(store, st, a.ym, a.corp)))
        elif c == "export-xlsx":
            print(workbook.build(store, st))
        elif c == "values":
            cmd_values(a, store, st)
        elif c == "sync":
            print(json.dumps((google_api.pull if a.direction == "pull" else google_api.push)(store), ensure_ascii=False))
        elif c == "form-queue":
            q = forms.build_queue(store, st, check=a.check, budget=Budget(st, store.dir))
            from collections import Counter
            print(json.dumps(Counter(r["フォーム判定"] for r in q), ensure_ascii=False))
        elif c == "form-send":
            print(json.dumps(forms.send(store, st, Budget(st, store.dir), dry_run=not a.send), ensure_ascii=False, indent=1))
        elif c == "form-report":
            print(json.dumps(forms.funnel(store), ensure_ascii=False, indent=1))
        elif c == "calendar-followups":
            print(f"{google_api.add_followup_events(store)}件のフォロー予定を登録")
    except (BudgetExceeded, PermissionError, RuntimeError, KeyError, ValueError) as e:
        log.error("%s: %s", type(e).__name__, e)
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
