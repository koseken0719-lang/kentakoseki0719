"""Google Workspace 連携（Sheets 同期 / Gmail 下書き / Calendar）。

- 認証情報は環境変数で指定したファイルから読む。コード・ログ・リポジトリには保存しない。
- Gmail は「下書き作成」のみ実装し、送信機能は意図的に持たない（送信は人が承認して行う）。
- service 引数にフェイクを渡せるためテスト可能。
"""
from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText

from . import schema as S
from .core import Budget, Store, get_logger, is_unknown, today
from .outreach import eligible, render_email
from .pipeline import is_suppressed, log_activity

log = get_logger()
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.compose"]
SCOPES_CAL = ["https://www.googleapis.com/auth/calendar.events"]


def _build(api: str, version: str, scopes: list[str], token_env: str | None = None):
    try:
        from googleapiclient.discovery import build
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("google-api-python-client が未インストールです: pip install -r requirements.txt") from e
    token_file = os.environ.get(token_env or "", "")
    if token_file:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    else:
        sa = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not sa:
            raise RuntimeError("Google認証が未設定です（GOOGLE_APPLICATION_CREDENTIALS か "
                               f"{token_env or 'トークンファイル'} を設定。docs/運用マニュアル.md 参照）")
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(sa, scopes=scopes)
    return build(api, version, credentials=creds, cache_discovery=False)


def spreadsheet_id() -> str:
    from .core import load_settings
    sid = os.environ.get("SFS_SPREADSHEET_ID", "") or load_settings().get("spreadsheet_id", "")
    if not sid:
        raise RuntimeError("スプレッドシートIDが未設定です（SFS_SPREADSHEET_ID または settings.yaml の spreadsheet_id）")
    return sid


# ---------- Sheets ----------
SYNC_SHEETS = [s for s in S.SHEETS if s != S.DASHBOARD]  # 11は毎回再生成（pullしても上書きされる）  # ダッシュボードは数式のため同期対象外


def pull(store: Store, service=None, sheets: list[str] | None = None) -> dict:
    """スプレッドシート（正本）→ ローカル状態。"""
    svc = service or _build("sheets", "v4", SCOPES_SHEETS)
    out = {}
    for sh in sheets or SYNC_SHEETS:
        res = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id(), range=f"'{sh}'!A1:AZ",
            valueRenderOption="UNFORMATTED_VALUE").execute()
        out[sh] = store.from_values(sh, res.get("values", []))
    log.info("Sheets pull: %s", out)
    return out


def push(store: Store, service=None, sheets: list[str] | None = None) -> dict:
    """ローカル状態 → スプレッドシート。シート全体を置き換える（再実行しても重複しない）。"""
    svc = service or _build("sheets", "v4", SCOPES_SHEETS)
    out = {}
    for sh in sheets or SYNC_SHEETS:
        values = store.to_values(sh)
        svc.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id(), range=f"'{sh}'!A1:AZ", body={}).execute()
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id(), range=f"'{sh}'!A1", valueInputOption="RAW",
            body={"values": values}).execute()
        out[sh] = len(values) - 1
    log.info("Sheets push: %s", out)
    return out


# ---------- Gmail（下書きのみ） ----------
def create_drafts(store: Store, settings: dict, budget: Budget, service=None,
                  limit: int = 20) -> list[dict]:
    """優先営業リスト上位の「未着手」企業に初回メールの下書きを作成する。送信はしない。

    条件：所属代理店承認済み／差出人情報が記入済み／公開メールあり／営業停止でない。
    作成済み（活動履歴に下書き記録あり）の企業は再実行してもスキップする。
    """
    if not settings["compliance"]["agency_approved"]:
        raise PermissionError("所属代理店の承認が未登録のため、Gmail下書きを作成できません"
                              "（config/settings.yaml の compliance.agency_approved）")
    if any("（" in str(v) for v in settings["sender"].values()):
        raise PermissionError("差出人情報（config/settings.yaml の sender）に未記入の項目があります")
    svc = service or _build("gmail", "v1", SCOPES_GMAIL, "SFS_GMAIL_TOKEN_FILE")
    done = {str(a["法人番号"]) for a in store.read(S.ACTIVITY) if a["チャネル"] == "メール"}
    made = []
    for row in eligible(store):
        if len(made) >= limit:
            break
        corp = str(row["法人番号"])
        if corp in done or is_suppressed(store, corp) or is_unknown(row.get("公開メール")) \
                or row.get("営業ステータス") not in ("未着手", ""):
            continue
        budget.charge("gmail_drafts")
        subject, body = render_email(row, settings)
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"], msg["Subject"] = row["公開メール"], subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        d = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        log_activity(store, settings, corp, "メール", "下書き",
                     content=f"初回メール下書き（Gmail draft {d.get('id', '')}）")
        made.append({"法人番号": corp, "企業名": row["企業名"], "draft_id": d.get("id", "")})
    log.info("Gmail下書き作成: %d件（未送信・要承認）", len(made))
    return made


# ---------- Calendar ----------
def add_followup_events(store: Store, service=None, on: str | None = None) -> int:
    """当日以降の次回アクションを自分のカレンダーに終日予定として登録（招待は送らない）。"""
    svc = service or _build("calendar", "v3", SCOPES_CAL)
    cal = os.environ.get("SFS_CALENDAR_ID", "primary")
    n = 0
    for r in store.read(S.MASTER):
        d = str(r.get("次回アクション日", ""))
        if not d or d < (on or today()) or r.get("営業ステータス") == "営業停止":
            continue
        eid = "sfs" + "".join(c for c in f"{r['法人番号']}{d}".lower() if c in "0123456789abcdefghijklmnopqrstuv")
        body = {"id": eid, "summary": f"[営業フォロー] {r['企業名']}",
                "description": f"ステータス：{r['営業ステータス']}\n{r['推奨アプローチ']}",
                "start": {"date": d}, "end": {"date": d}}
        try:
            svc.events().insert(calendarId=cal, body=body, sendUpdates="none").execute()
            n += 1
        except Exception as e:  # 409 = 登録済み（冪等）
            if "409" not in str(e) and "duplicate" not in str(e).lower():
                raise
    return n


def count_consultations(service, ym: str, code: str) -> dict:
    """予定タイトルの企業コードタグ [FP相談:CODE] から件数のみ集計（個人名・内容は取得結果に残さない）。"""
    cal = os.environ.get("SFS_CALENDAR_ID", "primary")
    y, m = map(int, ym.split("-"))
    end = f"{y + m // 12}-{m % 12 + 1:02d}-01T00:00:00+09:00"
    res = service.events().list(calendarId=cal, q=f"[FP相談:{code}]", singleEvents=True,
                                showDeleted=True, timeMin=f"{ym}-01T00:00:00+09:00",
                                timeMax=end, maxResults=2500).execute()
    items = res.get("items", [])
    cancelled = sum(1 for e in items if e.get("status") == "cancelled" or "キャンセル" in e.get("summary", ""))
    done = sum(1 for e in items if "実施済" in e.get("summary", ""))
    return {"予約件数": len(items), "実施件数": done, "キャンセル件数": cancelled}
