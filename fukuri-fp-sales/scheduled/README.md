# 定期実行（Claude Code Scheduled Tasks）

Claude Code の Scheduled Tasks（クラウド環境）に、以下の4本を「毎回新しいセッションで実行」として登録する。
コネクタは Google Sheets / Gmail / Google Calendar / Google Drive を許可する。時刻は日本時間。

| 名称 | スケジュール（例） | プロンプト |
|---|---|---|
| 平日：営業支援・フォロー管理 | `CRON_TZ=Asia/Tokyo 43 7 * * 1-5` | `daily.md` |
| 月曜：新規企業調査 | `CRON_TZ=Asia/Tokyo 12 13 * * 1` | `monday_research.md` |
| 金曜：営業活動分析 | `CRON_TZ=Asia/Tokyo 17 16 * * 5` | `friday_review.md` |
| 月末：月次集計 | `CRON_TZ=Asia/Tokyo 23 18 28-31 * *`（プロンプト内で月末日か判定） | `month_end.md` |

**登録は、30社テストの結果を確認し、所属代理店の承認とスプレッドシートIDの設定が済んでから行う。**
月曜の調査は最初は30社で開始し、取り込み拒否率・未確認率を見て100社へ引き上げる（`monday_research.md` の社数を変更）。
