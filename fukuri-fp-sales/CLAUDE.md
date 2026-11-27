# CLAUDE.md — 福利厚生FP相談 法人開拓システム

株式会社スフェノスの法人営業支援システム。Python パッケージ `sfs`、正本データは Google スプレッドシート。

## 絶対に守ること
- **外部へ送信しない。** メールは下書きまで。Gmailの送信・返信・転送ツール、問い合わせフォーム送信、SNS投稿は使わない。
- **所属代理店（ファイナンシャルアライアンス株式会社）の承認**（`config/settings.yaml` の `compliance.agency_approved`）が false の間は、Gmail下書きも作らない。このフラグを自分で true にしない。
- **捏造しない。** 従業員数・法人番号・担当者・連絡先は、今回の調査で開いたページで確認できたものだけ。確認できなければ `未確認`。情報源URLと確認日を必ず残す。
- 10_営業停止リスト の企業には接触しない。営業お断り表記のあるフォームは使わない。
- 個人の家計・保険相談内容をスプレッドシートやリポジトリに書かない。
- このリポジトリは**公開**。`data/` `output/` `logs/` と認証情報をコミットしない（.gitignore 済み）。
- 利用規約・robots・API制限を守る。アクセス制限を回避しない。乗換案内・地図サイトを自動取得しない。

## 作業の流れ（定期実行）
1. スプレッドシート → ローカル：`python -m sfs sync pull`（認証未設定時はSheetsコネクタで各シートを読み `python -m sfs values import <シート> --file x.json`）
2. 処理（`research-import` / `daily` / `weekly-report` / `monthly-report` など）
3. ローカル → スプレッドシート：`python -m sfs sync push`（またはコネクタで `values export` の内容を書き込む）
4. 実行結果は件数と未達・失敗をそのまま報告する。成功を装わない。

企業調査の手順とJSON形式は `data/research/BRIEF.md`（なければ `docs/調査指示書.md`）。定期実行のプロンプトは `scheduled/`。

## 開発
- テスト：`pytest -q`（変更後は必ず実行）
- シートの列は `sfs/schema.py` が正。列の追加は末尾に。スプレッドシート側のヘッダーも合わせる。
- スコア配点は `sfs/research.py::score`、閾値・駅別所要時間は `config/settings.yaml`。
