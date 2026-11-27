"""導入企業向けの資料一式（案内PDF・社内告知文・予約ページ・QR・規約ひな形・月次利用レポート）。

企業向けレポートは個人が特定されない集計のみ。少数セルは秘匿する。
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import schema as S
from .core import ROOT, Store, get_logger, short_hash, to_int, today

log = get_logger()
THEMES = ["住宅", "教育資金", "老後資金", "資産形成", "家計管理", "保険", "その他"]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), undefined=StrictUndefined,
                       trim_blocks=True, lstrip_blocks=True, autoescape=False)


def company_code(corp: str) -> str:
    """予約ページ・カレンダータグ用の企業コード（法人番号を直接露出しない）。"""
    return "C" + short_hash("sphenos-fp", str(corp), n=8).upper()


def register(store: Store, settings: dict, corp: str, employees: int | None = None,
             dept: str = "", decided: str | None = None) -> dict:
    """05_福利厚生導入企業 に登録（冪等）。"""
    m = next((r for r in store.read(S.MASTER) if str(r["法人番号"]) == str(corp)), None)
    if m is None:
        raise KeyError(f"企業マスターに {corp} がありません")
    code = company_code(corp)
    base = settings["sender"]["booking_base_url"].rstrip("/")
    row = {"導入ID": f"A-{code}", "法人番号": corp, "企業名": m["企業名"],
           "導入決定日": decided or today(), "利用開始日": "",
           "対象従業員数": employees or to_int(m.get("従業員数")) or "",
           "窓口部署": dept, "企業コード": code, "予約ページURL": f"{base}/{code}/",
           "案内資料": f"output/onboarding/{code}/", "社内告知日": "",
           "規約・同意書の版": "v1.0（ひな形・要レビュー）", "ステータス": "準備中",
           "月次レポート送付日": "", "備考": ""}
    store.upsert(S.ADOPTED, row, keep=["導入決定日", "利用開始日", "社内告知日", "ステータス",
                                       "窓口部署", "月次レポート送付日", "備考"])
    masters = store.read(S.MASTER)
    for r in masters:
        if str(r["法人番号"]) == str(corp):
            r["営業ステータス"] = "導入決定"
    store.write(S.MASTER, masters)
    return next(r for r in store.read(S.ADOPTED) if str(r["法人番号"]) == str(corp))


FONT_CANDIDATES = ["/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
                   "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
                   "/Library/Fonts/Arial Unicode.ttf", "C:/Windows/Fonts/meiryo.ttc"]


def _register_font(pdfmetrics) -> str:
    """日本語フォントを埋め込む（SFS_PDF_FONT で指定可）。見つからなければ非埋め込みCIDフォント。"""
    import os
    from reportlab.pdfbase.ttfonts import TTFont
    for fp in [os.environ.get("SFS_PDF_FONT", "")] + FONT_CANDIDATES:
        if fp and Path(fp).exists():
            try:
                pdfmetrics.registerFont(TTFont("SfsJP", fp))
                return "SfsJP"
            except Exception:  # 読めないフォントは次の候補へ
                continue
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    log.warning("埋め込み可能な日本語フォントが見つかりません。閲覧環境によっては文字が表示されない可能性があります")
    return "HeiseiKakuGo-W5"


def _pdf(path: Path, ctx: dict, qr_png: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen import canvas
    f = _register_font(pdfmetrics)
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    s = ctx["s"]
    c.setFillColorRGB(0.07, 0.2, 0.4)
    c.rect(0, h - 42 * mm, w, 42 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(f, 11)
    c.drawString(18 * mm, h - 16 * mm, f"{ctx['a']['企業名']} 従業員・ご家族の皆さまへ")
    c.setFont(f, 22)
    c.drawString(18 * mm, h - 30 * mm, "無料FP相談（福利厚生）のご案内")
    c.setFillColorRGB(0.1, 0.1, 0.1)
    y = h - 56 * mm

    def para(title: str, lines: list[str]):
        nonlocal y
        c.setFont(f, 13)
        c.setFillColorRGB(0.07, 0.2, 0.4)
        c.drawString(18 * mm, y, "■ " + title)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont(f, 10.5)
        y -= 7 * mm
        for ln in lines:
            c.drawString(22 * mm, y, ln)
            y -= 5.6 * mm
        y -= 4 * mm

    para("ご相談いただける内容", ["住宅購入・住宅ローン／教育資金／老後資金・年金／資産形成（NISA・iDeCo等）",
                               "家計管理・家計の見直し／生命保険の確認・見直し　など"])
    para("ご利用について", ["・相談費用は無料です。従業員ご本人とご家族がご利用いただけます。",
                           "・相談は個別・予約制（オンラインまたは対面）、1回あたり約60分です。",
                           "・ご利用は任意です。利用の有無が人事評価等に影響することはありません。"])
    para("安心してご利用いただくために", ["・相談内容や個人情報を勤務先にお伝えすることはありません。",
                                     "　（勤務先へのご報告は、利用件数など個人が特定されない集計のみです）",
                                     "・ご本人が希望された場合に限り、保険等の金融商品をご提案することがあります。",
                                     "　商品の購入は利用の条件ではなく、相談のみで終了いただけます。",
                                     f"・保険募集は{s['agency']}所属の登録募集人として行います。"])
    para("ご予約方法", ["右のQRコード、または下記URLの予約ページからご希望の日時をお選びください。",
                       ctx["a"]["予約ページURL"]])
    c.drawImage(str(qr_png), w - 62 * mm, 30 * mm, 42 * mm, 42 * mm)
    c.setFont(f, 9)
    c.drawString(18 * mm, 24 * mm, f"運営：{s['company']}　{s['title']} {s['name']}　{s['address']}")
    c.drawString(18 * mm, 19 * mm, f"TEL {s['phone']}　MAIL {s['email']}　{s['website']}")
    if not ctx["approved"]:
        c.setFillColorRGB(0.8, 0.1, 0.1)
        c.setFont(f, 10)
        c.drawString(18 * mm, 10 * mm, "【案】所属代理店の承認前ドラフト。従業員への配布不可。")
    c.save()


def build(store: Store, settings: dict, corp: str, out_dir: Path | None = None) -> list[Path]:
    """企業別の案内PDF・QR・社内告知文・予約ページ・規約ひな形を生成。"""
    import qrcode
    a = next((r for r in store.read(S.ADOPTED) if str(r["法人番号"]) == str(corp)), None)
    if a is None:
        raise KeyError(f"05_福利厚生導入企業 に {corp} がありません（先に onboard register）")
    out = Path(out_dir or ROOT / "output" / "onboarding") / a["企業コード"]
    out.mkdir(parents=True, exist_ok=True)
    ctx = {"a": a, "s": settings["sender"], "approved": settings["compliance"]["agency_approved"],
           "today": today(), "themes": THEMES}
    qr = out / "予約QRコード.png"
    qrcode.make(a["予約ページURL"]).save(qr)
    pdf = out / "サービス案内.pdf"
    _pdf(pdf, ctx, qr)
    paths = [qr, pdf]
    env = _env()
    for tpl, name in (("onboard_announce.txt.j2", "社内告知メール文面.txt"),
                      ("onboard_booking.html.j2", "index.html"),
                      ("legal_privacy.md.j2", "個人情報保護方針（ひな形）.md"),
                      ("legal_terms.md.j2", "利用規約・同意事項（ひな形）.md")):
        p = out / name
        p.write_text(env.get_template(tpl).render(**ctx), encoding="utf-8")
        paths.append(p)
    log.info("導入資料生成: %s → %s", a["企業名"], out)
    return paths


def record_consult(store: Store, settings: dict, ym: str, corp: str, booked: int, done: int,
                   cancelled: int = 0, themes: dict | None = None) -> dict:
    """06_FP相談件数集計 に月次の件数のみを記録（冪等）。個人情報は受け取らない。"""
    a = next((r for r in store.read(S.ADOPTED) if str(r["法人番号"]) == str(corp)), None)
    if a is None:
        raise KeyError(f"導入企業に {corp} がありません")
    themes = themes or {}
    if set(themes) - set(THEMES):
        raise ValueError(f"テーマは {THEMES} のみ")
    emp = to_int(a["対象従業員数"])
    row = {"年月": ym, "法人番号": corp, "企業名": a["企業名"], "対象従業員数": emp or "",
           "予約件数": booked, "実施件数": done, "キャンセル件数": cancelled,
           "利用率(%)": round(done / emp * 100, 1) if emp else "", "備考": "",
           **{t: themes.get(t, 0) for t in THEMES}}
    store.upsert(S.CONSULT, row)
    return row


def usage_report(store: Store, settings: dict, ym: str, corp: str) -> str:
    """企業向け月間利用実績レポート（集計のみ・少数セル秘匿）。"""
    k = settings["compliance"]["min_cell_size"]
    rows = [r for r in store.read(S.CONSULT) if str(r["法人番号"]) == str(corp) and str(r["年月"]) <= ym]
    cur = next((r for r in rows if str(r["年月"]) == ym), None)
    if cur is None:
        raise KeyError(f"{ym} の集計がありません")
    total_done = sum(to_int(r["実施件数"]) or 0 for r in rows)
    mask = lambda n: "0件" if (to_int(n) or 0) == 0 else f"{k}件未満" if to_int(n) < k else f"{to_int(n)}件"
    theme_lines = [f"| {t} | {mask(cur.get(t, 0))} |" for t in THEMES]
    return "\n".join([
        f"# 福利厚生FP相談 月間利用実績レポート（{ym}）", "", f"{cur['企業名']} 御中", "",
        "本レポートは個人が特定されない集計情報のみを記載しています。"
        f"相談者の氏名・相談内容は含みません。{k}件未満の内訳は「{k}件未満」と表示します。", "",
        "| 項目 | 当月 |", "|---|---|",
        f"| 対象従業員数 | {cur['対象従業員数']}名 |", f"| 相談予約件数 | {cur['予約件数']}件 |",
        f"| 相談実施件数 | {cur['実施件数']}件 |", f"| 利用率（実施÷対象従業員） | {cur['利用率(%)']}% |",
        f"| 利用開始からの累計実施件数 | {total_done}件 |", "",
        "## 相談テーマ別（当月・複数該当あり）", "", "| テーマ | 件数 |", "|---|---|", *theme_lines, "",
        "## 利用促進のご提案", "- 社内告知文の再配信（給与明細配布・年末調整・新入社員研修のタイミング）",
        "- 社内説明会（30分・オンライン可）の開催", "",
        f"{settings['sender']['company']}　{settings['sender']['name']}", ""])
