---
name: codex-image
description: Codex CLI（ChatGPTサブスク）で画像を生成してリポジトリに保存する。LP用の画像・バナー・アイコン・イラストなどを「作って」「生成して」と頼まれたときに使う。
---

# Codex で画像生成

ChatGPT のサブスク（Plus / Pro など）でログインした Codex CLI の組み込み画像生成（`$imagegen`）を使う。API キーは使わず、サブスクの利用枠内で動く。

## 手順

1. 依頼内容から英語または日本語の具体的なプロンプトを作る（用途、構図、縦横比、色＝このLPは明るいネイビー×金、入れたくない要素）。
2. 保存先を決める。原則 `assets/<わかりやすい名前>.png`。
3. 実行する（数十秒〜数分かかるので timeout は長めに）:

   ```bash
   scripts/codex-image.sh "<プロンプト>" assets/<name>.png
   ```

4. 生成された画像を Read で確認し、必要なら `index.html` に組み込む。
5. 失敗したらエラー内容をそのままユーザーに伝える。よくある原因:
   - 未ログイン → `codex login`（リモート環境は `codex login --device-auth`）
   - 無料プラン・API キーでのログイン → 組み込みの画像生成は使えない
   - 使用上限（`UsageLimitExceeded`）→ リセット時刻まで待つ

## 注意

- `OPENAI_API_KEY` を使うフォールバック（従量課金）は、ユーザーが明示的に頼んだとき以外は使わない。
- Claude Code のクラウド環境は chatgpt.com に接続できないことがある。その場合は手元の PC で実行する。
