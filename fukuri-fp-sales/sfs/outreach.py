"""企業別の営業キット生成（営業理由・メリット・接触方法・メール・電話・SNS・郵送・反論対応・フォロー）。

生成物はすべて「下書き」。外部送信は人間の承認後に人が行う。
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import schema as S
from . import plays
from .core import ROOT, Store, get_logger, is_unknown, to_int

log = get_logger()

OBJECTIONS = [
    ("なぜ無料なのですか。", "相談の結果、ご本人が希望された場合に限り、保険等の金融商品をご提案することがあり、その際に保険会社等から受け取る手数料で運営しています。この点は従業員の皆さまにも事前に明示します。商品の購入は利用の条件ではなく、相談のみのご利用で終了いただいて構いません。"),
    ("結局は保険の営業ではないですか。", "ご相談の中心は住宅・教育・老後・家計といったライフプランです。金融商品のご提案はご本人の希望がある場合に限り、登録募集人として法令と所属代理店（ファイナンシャルアライアンス株式会社）のルールに沿って行います。勧誘を目的とした一斉案内や、断りにくい状況での提案は行いません。"),
    ("従業員の相談内容が会社に伝わるのは困ります。", "個別の相談内容は勤務先には一切開示しません。会社にご報告するのは、利用件数など個人が特定されない集計情報のみです（少人数の内訳は非表示にします）。"),
    ("すでに福利厚生サービスに加入しています。", "既存の福利厚生サービスと競合せず、併用いただけます。割引型サービスでは手薄になりがちな「個別のお金の相談」を、費用負担なしで追加するものです。"),
    ("担当者の手間が増えるのは避けたいです。", "社内告知文・案内資料・予約ページ（QRコード）はすべて当方でご用意します。ご担当者さまには初回の社内告知をお願いするだけで、予約受付・リマインド・実施は当方で完結します。"),
    ("今は忙しいので検討できません。", "承知しました。資料のみお送りし、ご都合のよい時期に改めてご連絡します。今後のご案内が不要な場合はその旨お知らせください。以後のご連絡は控えます。"),
]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), undefined=StrictUndefined,
                       trim_blocks=True, lstrip_blocks=True)


def benefits(row: dict) -> list[str]:
    emp = to_int(row.get("従業員数"))
    out = [
        "導入費用・月額費用・従業員の相談費用がすべて無料（予算措置・稟議の負担が小さい）",
        "従業員とご家族が、住宅購入・教育資金・老後資金・資産形成・家計管理・生命保険を個別に相談できる",
        "採用ページ・求人票に記載できる福利厚生メニューが1つ増える",
        "お金の不安の軽減を通じた定着支援（相談内容は会社に非開示のため安心して利用できる）",
        "社内告知文・案内PDF・予約用QRコードは当方で用意し、ご担当者の運用負担はほぼない",
    ]
    if not is_unknown(row.get("認定・健康経営")):
        out.append(f"「{str(row['認定・健康経営'])[:30]}」等の取り組みと連動した従業員支援施策として位置付けられる")
    if emp:
        out.append(f"従業員約{emp}名規模なら、社内説明会（30分）＋個別相談枠の設定で全員に案内が届く")
    return out


def context(row: dict, settings: dict) -> dict:
    owner = "オーナー経営" in str(row.get("代表者(公開情報)", ""))
    rep = str(row.get("代表者(公開情報)", "")).split("／")[0]
    dept = row.get("公開担当部署")
    steps = settings["followup"]["steps"]
    return {
        "c": row, "s": settings["sender"], "approved": settings["compliance"]["agency_approved"],
        "rep": "代表者" if is_unknown(rep) else rep, "owner": owner,
        "dept": "総務・人事ご担当者" if is_unknown(dept) else f"{dept} ご担当者",
        "benefits": benefits(row), "objections": OBJECTIONS, "steps": steps,
        "has_recruit": not is_unknown(row.get("採用情報")) and not str(row["採用情報"]).startswith("募集なし"),
        "has_cert": not is_unknown(row.get("認定・健康経営")),
        "form_prohibited": str(row.get("営業お断り表記", "")).startswith("あり"),
        "unknown": is_unknown, "route": plays.route(row), "m": plays.render_messages(row, settings),
        "plays": [{**p, **dict(zip(("name", "need", "angle", "timing", "opener"), plays.PLAYS[p["key"]]))}
                  for p in plays.select(row)[:3]],
    }


def render_kit(row: dict, settings: dict) -> str:
    return _env().get_template("outreach_kit.md.j2").render(**context(row, settings))


def render_email(row: dict, settings: dict) -> tuple[str, str]:
    """(件名, 本文)。Gmail下書き用。入口提案（第1候補）の文面＋署名・配信停止の案内。"""
    m = plays.render_messages(row, settings)
    footer = _env().get_template("_footer.j2").render(**context(row, settings))
    return m["subject"], m["email"] + "\n\n" + footer


def eligible(store: Store) -> list[dict]:
    """営業キット作成対象：優先営業リスト掲載かつ営業停止でない企業。"""
    suppressed = {r["法人番号"] for r in store.read(S.SUPPRESS)}
    master = {r["法人番号"]: r for r in store.read(S.MASTER)}
    return [master[p["法人番号"]] for p in store.read(S.PRIORITY)
            if p["法人番号"] not in suppressed and p["法人番号"] in master]


def build_kits(store: Store, settings: dict, top: int | None = None,
               out_dir: Path | None = None) -> list[Path]:
    out = Path(out_dir or ROOT / "output" / "outreach")
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, row in enumerate(eligible(store)[:top], 1):
        p = out / f"{i:03d}_{row['ランク']}_{row['企業名'].replace('/', '／')}.md"
        for old in out.glob(f"*_{row['企業名'].replace('/', '／')}.md"):
            old.unlink()  # 順位変動時の重複ファイルを残さない
        p.write_text(render_kit(row, settings), encoding="utf-8")
        paths.append(p)
    log.info("営業キット生成: %d社 → %s", len(paths), out)
    return paths
