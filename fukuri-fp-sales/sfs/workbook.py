"""10シート構成のワークブック（xlsx）を生成。Googleドライブへアップロードするとスプレッドシートに変換される。"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import schema as S
from .core import ROOT, Store, today

HEAD_FILL = PatternFill("solid", fgColor="12335F")
HEAD_FONT = Font(bold=True, color="FFFFFF")
WIDE = {"所在地": 34, "事業概要": 40, "採用情報": 40, "福利厚生情報": 40, "認定・健康経営": 30,
        "人材定着の取組": 34, "地域活動": 30, "情報源": 50, "スコア内訳": 44, "営業仮説": 60,
        "推奨アプローチ": 44, "内容": 44, "所見": 60, "改善案": 60, "翌週アクション": 44,
        "企業名": 28, "入口提案（第1候補）": 40, "根拠（公開情報の該当記載）": 50, "相手にとっての用事": 40,
        "経営者への切り口": 44, "最初の一言": 50, "提案時期": 30, "入口提案（第2候補）": 40, "接触経路": 50, "注意点": 34, "根拠区分": 20, "公式サイト": 30, "接触先": 34, "代表者(公開情報)": 30, "備考": 30}
VALIDATIONS = {
    (S.MASTER, "営業ステータス"): S.STATUS_VALUES, (S.MASTER, "対象区分"): S.TARGET_CLASSES,
    (S.ACTIVITY, "チャネル"): S.CHANNELS, (S.ACTIVITY, "結果"): S.RESULTS,
    (S.ACTIVITY, "送信承認"): ["未", "済"], (S.DEALS, "フェーズ"): S.DEAL_PHASES,
    (S.SUPPRESS, "理由"): S.SUPPRESS_REASONS,
    (S.ADOPTED, "ステータス"): ["準備中", "稼働中", "休止", "終了"],
}


def col(sheet: str, name: str) -> str:
    return get_column_letter(S.SHEETS[sheet].index(name) + 1)


def ref(sheet: str, name: str) -> str:
    c = col(sheet, name)
    return f"'{sheet}'!{c}:{c}"


def dashboard_rows(settings: dict) -> list[list]:
    """[指標, 実績(数式), 目標, 達成率(数式), 備考]。B2 の対象年月（YYYY-MM）で月次指標を切り替える。"""
    t = settings["targets"]
    ym = '$B$2&"*"'
    A, D, M, AD, C = S.ACTIVITY, S.DEALS, S.MASTER, S.ADOPTED, S.CONSULT
    acts = f'COUNTIFS({ref(A, "日付")},{ym},{ref(A, "結果")},"<>下書き")'
    replies = (f'(COUNTIFS({ref(A, "日付")},{ym},{ref(A, "結果")},"返信あり")'
               f'+COUNTIFS({ref(A, "日付")},{ym},{ref(A, "結果")},"アポ獲得"))')
    deals = f'COUNTIFS({ref(D, "商談日")},{ym})'
    adopts = f'COUNTIFS({ref(AD, "導入決定日")},{ym})'
    done = f'SUMIFS({ref(C, "実施件数")},{ref(C, "年月")},$B$2)'
    covered = (f'(SUMIFS({ref(AD, "対象従業員数")},{ref(AD, "ステータス")},"稼働中")'
               f'+SUMIFS({ref(AD, "対象従業員数")},{ref(AD, "ステータス")},"準備中"))')
    cost = f'SUMIFS({ref(A, "費用(円)")},{ref(A, "日付")},{ym})'
    rate = lambda a, b: f'=IF({b}=0,"データなし",ROUND({a}/{b}*100,1))'
    return [
        ["対象年月（YYYY-MM）", today()[:7], "", "", "この値を変更すると月次指標が切り替わります"],
        ["【累計】企業マスター登録数", f'=COUNTA({ref(M, "法人番号")})-1', "", "", ""],
        ["【累計】確定対象数", f'=COUNTIF({ref(M, "対象区分")},"確定対象")', "", "", ""],
        ["【累計】追加調査リスト", f'=COUNTIF({ref(M, "対象区分")},"追加調査")', "", "", "従業員数・移動時間が未確認"],
        ["【累計】Sランク（確定対象）", f'=COUNTIFS({ref(M, "ランク")},"S",{ref(M, "対象区分")},"確定対象")', "", "", "80点以上"],
        ["【累計】Aランク（確定対象）", f'=COUNTIFS({ref(M, "ランク")},"A",{ref(M, "対象区分")},"確定対象")', "", "", "65点以上"],
        ["【累計】Bランク（確定対象）", f'=COUNTIFS({ref(M, "ランク")},"B",{ref(M, "対象区分")},"確定対象")', "", "", "50点以上"],
        ["【累計】営業停止リスト", f'=COUNTA({ref(S.SUPPRESS, "法人番号")})-1', "", "", ""],
        ["【月次】新規企業発掘数", f'=COUNTIFS({ref(M, "初回登録日")},{ym})', t["weekly_new_research"] * 4, "", ""],
        ["【月次】アプローチ件数（延べ）", f"={acts}", t["monthly_outreach"], "", "社数（重複除外）は月次レポート参照"],
        ["【月次】返信件数", f"={replies}", "", "", ""],
        ["【月次】返信率(%)", rate(replies, acts), "", "", ""],
        ["【月次】法人商談数", f"={deals}", t["monthly_meetings"], "", ""],
        ["【月次】法人商談化率(%)", rate(deals, acts), "", "", ""],
        ["【月次】新規導入数", f"={adopts}", t["monthly_adoptions"], "", ""],
        ["【月次】福利厚生導入率(%)", rate(adopts, deals), "", "", ""],
        ["【累計】導入企業数", f'=COUNTA({ref(AD, "法人番号")})-1', t["adopted_companies"], "", ""],
        ["【累計】利用対象従業員数", f"={covered}", t["covered_employees"], "", ""],
        ["【月次】FP相談予約件数", f'=SUMIFS({ref(C, "予約件数")},{ref(C, "年月")},$B$2)', "", "", ""],
        ["【月次】FP相談実施件数", f"={done}", t["monthly_consultations"], "", ""],
        ["【月次】FP相談利用率(%)", rate(done, covered), "", "", "実施件数÷利用対象従業員数"],
        ["【月次】営業費用(円)", f"={cost}", "", "", ""],
        ["【月次】実施面談1件あたり獲得原価(円)", f'=IF({done}=0,"データなし",ROUND({cost}/{done},0))', "", "", ""],
    ]


def build(store: Store, settings: dict, path: Path | None = None, only: list[str] | None = None) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    for sheet, cols in S.SHEETS.items():
        if only and sheet not in only:
            continue
        ws = wb.create_sheet(sheet)
        ws.append(cols)
        if sheet == S.DASHBOARD:
            for i, r in enumerate(dashboard_rows(settings), start=2):
                if r[2] != "":
                    r[3] = f'=IF(ISNUMBER(B{i}),ROUND(B{i}/C{i}*100,1)&"%","")'
                ws.append(r)
            ws.column_dimensions["A"].width, ws.column_dimensions["E"].width = 40, 46
            for c in "BCD":
                ws.column_dimensions[c].width = 16
            ws["B2"].number_format = "@"
        else:
            for r in store.read(sheet):
                ws.append([r.get(c, "") for c in cols])
            for i, c in enumerate(cols, 1):
                ws.column_dimensions[get_column_letter(i)].width = WIDE.get(c, 14)
                if c.endswith("日") or c in ("日付", "年月", "法人番号", "週(月曜日)", "代表電話"):
                    for cell in ws[get_column_letter(i)]:
                        cell.number_format = "@"  # 日付・番号は文字列として保持
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
            ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.fill, cell.font = HEAD_FILL, HEAD_FONT
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.freeze_panes = "C2" if sheet in (S.MASTER, S.PRIORITY, S.PLAYS) else "A2"
    for (sheet, name), values in VALIDATIONS.items():
        if sheet not in wb.sheetnames:
            continue
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        c = col(sheet, name)
        dv.add(f"{c}2:{c}2000")
        wb[sheet].add_data_validation(dv)
    path = Path(path or ROOT / "output" / "スフェノス_福利厚生FP相談_法人営業管理.xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
