# 株式会社スフェノス｜福利厚生FP相談 法人開拓システム（sfs）

企業向け無料福利厚生FP相談の導入企業を継続的に獲得するための営業支援システム。
企業発掘 → 調査 → 評価 → 営業文面作成 → 進捗管理 → 効果測定 → 改善 を一気通貫で扱う。

> **このリポジトリは公開設定です。** 企業データ・営業文面・ログ・認証情報は `.gitignore` で除外し、
> 正本は Google スプレッドシート（非公開）に置きます。`data/` `output/` `logs/` `.env` はコミットしないでください。

## 構成

```
config/settings.yaml   目標値・対象地域/業種・スコア閾値・駅別所要時間表・API上限・差出人・承認フラグ
sfs/schema.py          11シートの列定義・キー
sfs/core.py            設定、ログ（秘匿情報マスク）、状態ストア（冪等upsert）、API月間上限
sfs/research.py        調査データ検証（出典必須・法人番号チェックデジット）、移動時間、スコアリング、gBizINFO
sfs/plays.py           入口提案の選定（11_入口提案リスト。01・02の「入口提案」列と連動）
sfs/outreach.py        企業別営業キット（入口提案＋9項目）生成
sfs/pipeline.py        活動履歴、営業停止、フォロー、日次タスク、週次/月次KPI・改善提案
sfs/onboarding.py      導入企業向け 案内PDF・QR・告知文・予約ページ・規約ひな形・利用実績レポート
sfs/google_api.py      Sheets同期、Gmail下書き（送信機能なし）、Calendar
sfs/workbook.py        10シートのxlsx出力（ダッシュボード数式つき）
templates/             営業文面・導入資料テンプレート（Jinja2）
scheduled/             定期実行（Claude Code Scheduled Tasks）用プロンプト
docs/                  設計書・運用マニュアル
tests/                 pytest（17件）
```

## クイックスタート

```bash
pip install -r requirements.txt
python -m sfs doctor                       # 環境・認証・承認状況
python -m sfs research-import              # data/research/*.json を検証して取り込み・スコアリング
python -m sfs outreach-build               # 営業キット（下書き）→ output/outreach/
python -m sfs export-xlsx                  # 10シートのワークブック → output/
python -m sfs daily                        # 本日の営業タスク
python -m sfs weekly-report                # 金曜：週次改善レポート
python -m sfs monthly-report --ym 2026-11  # 月末：月次レポート
pytest -q
```

その他のコマンドは `python -m sfs -h`、運用手順は `docs/運用マニュアル.md` を参照。

## 安全設計（要点）

| ルール | 実装 |
|---|---|
| 無断送信しない | Gmailは下書き作成のみ。送信APIの呼び出しコードは存在しない |
| 所属代理店の承認が必須 | `compliance.agency_approved: false` の間、Gmail下書き作成を拒否し、全資料に「承認前」表示 |
| 捏造しない | 出典URL・確認日のないレコード、チェックデジット不一致の法人番号、出典のない従業員数は取り込み拒否 |
| 未確認は確定対象にしない | 従業員数・移動時間が未確認 → 「追加調査」。優先営業リストに載らない |
| 営業お断り・受信拒否 | お断り表記のあるフォームは記録・使用不可。受信拒否は自動で 10_営業停止リスト へ、以後すべての処理から除外 |
| 個人情報を営業シートに置かない | 相談内容を示す語の混入を検知して書き込み拒否。06は件数のみ |
| 企業向けレポートは集計のみ | 3件未満の内訳は秘匿表示 |
| 再実行で重複しない | 法人番号・活動ID・週・年月をキーに upsert |
| API費用の上限 | `budget` の月間回数・金額上限を超えると停止 |
