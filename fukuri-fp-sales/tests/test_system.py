import datetime as dt
import json

import pytest

from conftest import make_number, rec
from sfs import google_api, onboarding, outreach, pipeline, research, workbook
from sfs import schema as S
from sfs.core import Budget, BudgetExceeded

N = lambda i: make_number(f"{i:012d}")


# ---------- 調査・検証 ----------
def test_corporate_number_check_digit():
    assert research.valid_corporate_number(N(1))
    bad = str((int(N(1)[0]) % 9) + 1) + N(1)[1:]
    assert not research.valid_corporate_number(bad)
    assert not research.valid_corporate_number("123")


def test_validation_rejects_unsourced_or_fabricated():
    assert research.validate_record(rec(1)) == []
    assert research.validate_record(rec(1, sources=[]))
    assert research.validate_record(rec(1, website="未確認"))
    assert research.validate_record(rec(1, employees_url="未確認"))       # 従業員数に出典なし
    assert research.validate_record(rec(1, corporate_number="1234567890123"))  # CD不一致
    assert research.validate_record(rec(1, verified_date=""))


def test_travel_time(settings):
    assert research.travel_minutes("武蔵小金井駅", 5, settings)[0] == 5
    assert research.travel_minutes("JR中央線 国分寺駅", 8, settings)[0] == 11
    assert research.travel_minutes("京王八王子", 2, settings)[0] == 32
    assert research.travel_minutes("ひばりが丘", 3, settings)[0] == 43
    assert research.travel_minutes("国分寺", None, settings)[0] is None
    assert research.travel_minutes("存在しない", 3, settings)[0] is None


def test_import_classification_and_rank(loaded, settings):
    store, _ = loaded
    m = {r["企業名"]: r for r in store.read(S.MASTER)}
    assert m["テスト株式会社1"]["対象区分"] == "確定対象" and m["テスト株式会社1"]["ランク"] == "S"
    assert m["テスト株式会社1"]["スコア"] == 100
    assert m["テスト株式会社2"]["対象区分"] == "追加調査" and "従業員数未確認" in m["テスト株式会社2"]["追加調査理由"]
    assert m["テスト株式会社3"]["対象区分"] == "追加調査" and "移動時間未確認" in m["テスト株式会社3"]["追加調査理由"]
    assert m["テスト株式会社5"]["対象区分"] == "対象外"
    assert m["テスト株式会社6"]["ランク"] == "C"
    pri = [p["企業名"] for p in store.read(S.PRIORITY)]
    assert "テスト株式会社2" not in pri and "テスト株式会社3" not in pri and pri[0] == "テスト株式会社1"


def test_reimport_is_idempotent_and_keeps_human_fields(loaded, settings):
    store, p = loaded
    rows = store.read(S.MASTER)
    rows[0]["営業ステータス"] = "アプローチ中"
    rows[2]["移動時間(分)"], rows[2]["移動時間区分"] = 20, "乗換案内で確認"
    store.write(S.MASTER, rows)
    res = research.import_files([p], store, settings)
    assert res["insert"] == 0 and len(store.read(S.MASTER)) == 6
    after = store.read(S.MASTER)
    assert after[0]["営業ステータス"] == "アプローチ中"
    assert after[2]["移動時間(分)"] == 20 and after[2]["対象区分"] == "確定対象"  # 人が補完→確定対象へ


def test_unverified_number_gets_provisional_key(store, settings, tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([rec(9, corporate_number="未確認")], ensure_ascii=False))
    research.import_files([p], store, settings)
    r = store.read(S.MASTER)[0]
    assert r["法人番号"].startswith("仮-") and "法人番号未確認" in r["追加調査理由"]


def test_referral_gets_priority(loaded, settings):
    store, _ = loaded
    store.write(S.PARTNERS, [{"パートナーID": "P1", "区分": "税理士", "名称": "X",
                              "紹介可能企業(法人番号)": N(4)}])
    research.rescore(store, settings)
    assert store.read(S.PRIORITY)[0]["法人番号"] == N(4)


# ---------- 営業文面 ----------
def test_kit_contains_all_sections_and_disclosures(loaded, settings):
    store, _ = loaded
    kit = outreach.render_kit(store.read(S.MASTER)[0], settings)
    for sec in ("1. なぜこの企業", "2. 福利厚生FP相談の導入メリット", "3. 最も適切な接触方法", "4. 初回営業メール案",
                "5. 電話営業スクリプト", "6. SNSメッセージ案", "7. 社長宛て郵送文案", "8. 想定される反論", "9. 次回フォローアップ"):
        assert sec in kit
    for must in ("ファイナンシャルアライアンス株式会社", "購入は利用の条件ではありません", "承認が未登録", "以後のご連絡は控えます"):
        assert must in kit


def test_prohibited_form_not_recommended(loaded, settings):
    store, _ = loaded
    r = next(x for x in store.read(S.MASTER) if x["法人番号"] == N(4))
    assert "使用禁止" in r["推奨アプローチ"] and "問い合わせフォーム（営業可否" not in r["推奨アプローチ"]
    with pytest.raises(PermissionError):
        pipeline.log_activity(store, settings, N(4), "フォーム", "未返信")


# ---------- 営業管理 ----------
def test_activity_followup_and_optout(loaded, settings):
    store, _ = loaded
    a = pipeline.log_activity(store, settings, N(1), "メール", "未返信", date="2026-11-02")
    assert a["次回アクション日"] == "2026-11-06" and "電話" in a["次回アクション"]
    pipeline.log_activity(store, settings, N(1), "メール", "未返信", date="2026-11-02", seq=1)  # 再実行
    assert len(store.read(S.ACTIVITY)) == 1
    assert "テスト株式会社1" in pipeline.daily_tasks(store, settings, "2026-11-06")
    pipeline.log_activity(store, settings, N(1), "電話", "受信拒否", date="2026-11-06")
    assert pipeline.is_suppressed(store, N(1))
    assert N(1) not in [p["法人番号"] for p in store.read(S.PRIORITY)]
    with pytest.raises(PermissionError):
        pipeline.log_activity(store, settings, N(1), "メール", "未返信")
    research.rescore(store, settings)  # 再スコア後も復活しない
    assert next(r for r in store.read(S.MASTER) if r["法人番号"] == N(1))["対象区分"] == "営業停止"
    assert all(r["法人番号"] != N(1) for r in outreach.eligible(store))


def test_personal_data_guard(loaded, settings):
    store, _ = loaded
    with pytest.raises(ValueError):
        pipeline.log_activity(store, settings, N(1), "電話", "返信あり", note="担当者の年収と保険証券の話")


def test_metrics_and_reports(loaded, settings):
    store, _ = loaded
    for i in (1, 4):
        pipeline.log_activity(store, settings, N(i), "メール", "未返信", date="2026-11-04", cost=100)
    pipeline.log_activity(store, settings, N(1), "電話", "アポ獲得", date="2026-11-10")
    store.write(S.DEALS, [{"商談ID": "D1", "法人番号": N(1), "企業名": "テスト株式会社1", "商談日": "2026-11-17",
                           "フェーズ": "導入決定", "獲得チャネル": "電話"}])
    onboarding.register(store, settings, N(1), decided="2026-11-20")
    onboarding.record_consult(store, settings, "2026-11", N(1), booked=5, done=4, themes={"住宅": 2, "保険": 2})
    m = pipeline.metrics(store, dt.date(2026, 11, 1), dt.date(2026, 11, 30))
    assert m["法人アプローチ数"] == 2 and m["返信率"] == 50.0 and m["法人商談化率"] == 50.0
    assert m["福利厚生導入率"] == 100.0 and m["利用対象従業員数(累計)"] == 80
    assert m["FP相談実施件数"] == 4 and m["FP相談利用率"] == 5.0
    assert m["実施面談1件あたり獲得原価(円)"] == 50
    rep = pipeline.monthly_report(store, settings, "2026-11")
    assert "翌月の改善案" in rep and "営業チャネル別" in rep
    w1 = pipeline.weekly_report(store, settings, "2026-11-06")
    pipeline.weekly_report(store, settings, "2026-11-06")
    assert w1["週(月曜日)"] == "2026-11-02" and len(store.read(S.WEEKLY)) == 1


def test_empty_metrics_report_no_fake_success(store, settings):
    m = pipeline.metrics(store, dt.date(2026, 11, 1), dt.date(2026, 11, 30))
    assert m["返信率"] is None and m["実施面談1件あたり獲得原価(円)"] is None
    assert "データなし" in pipeline.monthly_report(store, settings, "2026-11")
    assert pipeline.diagnose(m, settings)[0][0] == "アプローチ実績なし"


# ---------- 導入後 ----------
def test_onboarding_assets_and_anonymous_report(loaded, settings, tmp_path):
    store, _ = loaded
    a = onboarding.register(store, settings, N(1), dept="総務部")
    onboarding.register(store, settings, N(1))
    assert len(store.read(S.ADOPTED)) == 1 and N(1) not in a["予約ページURL"]
    paths = onboarding.build(store, settings, N(1), tmp_path / "ob")
    assert {p.suffix for p in paths} >= {".pdf", ".png", ".html", ".txt", ".md"}
    assert all(p.stat().st_size > 0 for p in paths)
    html = next(p for p in paths if p.suffix == ".html").read_text(encoding="utf-8")
    assert "勤務先に開示されず" in html and "承認前ドラフト" in html
    onboarding.record_consult(store, settings, "2026-11", N(1), 6, 5, themes={"住宅": 1, "保険": 4})
    rep = onboarding.usage_report(store, settings, "2026-11", N(1))
    assert "3件未満" in rep and "| 保険 | 4件 |" in rep and "| 住宅 | 1件 |" not in rep
    with pytest.raises(ValueError):
        onboarding.record_consult(store, settings, "2026-11", N(1), 1, 1, themes={"山田さんの相談": 1})


# ---------- Google連携・上限 ----------
class FakeGmail:
    def __init__(self):
        self.created = []

    def users(self): return self
    def drafts(self): return self

    def create(self, userId, body):
        self.created.append(body)
        return self

    def execute(self): return {"id": f"d{len(self.created)}"}

    def __getattr__(self, name):  # send 等が呼ばれたら失敗させる
        raise AssertionError(f"禁止されたGmail API呼び出し: {name}")


def test_gmail_drafts_gated_and_idempotent(loaded, settings, tmp_path):
    store, _ = loaded
    b, g = Budget(settings, tmp_path), FakeGmail()
    with pytest.raises(PermissionError):
        google_api.create_drafts(store, settings, b, g)
    settings["compliance"]["agency_approved"] = True
    with pytest.raises(PermissionError):            # 差出人未記入
        google_api.create_drafts(store, settings, b, g)
    settings["sender"] = {k: "記入済" for k in settings["sender"]}
    made = google_api.create_drafts(store, settings, b, g)
    assert made and N(4) not in [m["法人番号"] for m in made]   # 公開メールなしは対象外
    assert all(a["結果"] == "下書き" and a["送信承認"] == "未" for a in store.read(S.ACTIVITY))
    assert google_api.create_drafts(store, settings, b, g) == []  # 再実行で重複なし
    assert not hasattr(google_api, "send") and "messages().send" not in open(google_api.__file__).read()


def test_budget_cap(settings, tmp_path):
    settings["budget"]["websearch"] = {"max_calls": 2, "yen_per_call": 1}
    b = Budget(settings, tmp_path)
    b.charge("websearch"), b.charge("websearch")
    with pytest.raises(BudgetExceeded):
        b.charge("websearch")
    settings["budget"]["monthly_yen_cap"] = 1
    with pytest.raises(BudgetExceeded):
        Budget(settings, tmp_path).charge("websearch")


class FakeSheets:
    def __init__(self): self.data, self._r = {}, None
    def spreadsheets(self): return self
    def values(self): return self
    def clear(self, spreadsheetId, range, body): self.data.pop(range.split("!")[0], None); return self
    def update(self, spreadsheetId, range, valueInputOption, body): self.data[range.split("!")[0]] = body["values"]; return self
    def get(self, spreadsheetId, range, valueRenderOption): self._r = {"values": self.data.get(range.split("!")[0], [])}; return self
    def execute(self): r, self._r = self._r or {}, None; return r


def test_sheets_roundtrip_and_workbook(loaded, settings, tmp_path, monkeypatch):
    store, _ = loaded
    monkeypatch.setenv("SFS_SPREADSHEET_ID", "dummy")
    fake = FakeSheets()
    before = store.read(S.MASTER)
    google_api.push(store, fake)
    google_api.push(store, fake)
    store.write(S.MASTER, [])
    google_api.pull(store, fake)
    assert [r["法人番号"] for r in store.read(S.MASTER)] == [r["法人番号"] for r in before]
    from openpyxl import load_workbook
    wb = load_workbook(workbook.build(store, settings, tmp_path / "w.xlsx"))
    assert wb.sheetnames == list(S.SHEETS) and wb[S.MASTER].max_row == 7
    assert str(wb[S.DASHBOARD]["B4"].value).startswith("=COUNTIF")
