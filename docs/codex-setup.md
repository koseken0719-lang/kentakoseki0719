# Claude Code × Codex CLI で画像生成する（ChatGPTサブスク内）

Claude Code から Codex CLI を呼び出し、ChatGPT のサブスクの範囲で画像を生成する手順です。

## 仕組み

```
Claude Code ──(Bash)──> scripts/codex-image.sh ──> codex exec "$imagegen ..." ──> assets/xxx.png
```

- Codex CLI の画像生成機能（`image_generation`）は v0.171.0 時点で標準で有効
- **ChatGPT アカウントでログインしたときだけ**組み込みの画像生成が使えます（Plus / Pro など。無料プランは不可）
- API キーでログインした場合は組み込みの画像生成は使えません
- 使用量はサブスクの利用上限（画像生成用の枠）でカウントされます。API の従量課金にはなりません

## セットアップ（手元の PC で一度だけ）

1. Codex CLI をインストール（Node.js 18 以上が必要）

   ```bash
   npm i -g @openai/codex
   ```

2. ChatGPT アカウントでログイン

   ```bash
   codex login
   ```

   ブラウザが開けない環境（SSH 先など）では次のコマンドを使います。表示された URL とコードを別の端末で開いてください。

   ```bash
   codex login --device-auth
   ```

3. ログインと画像生成機能を確認

   ```bash
   codex login status
   ```

   ```bash
   codex features list | grep image_generation
   ```

   `image_generation  stable  true` と表示されれば OK です。

## 使い方

### Claude Code に頼む

このリポジトリでは `.claude/skills/codex-image` スキルが入っています。Claude Code で次のように頼むだけです。

> ヒーロー用の画像を作って。明るいネイビーと金、横長で

### 直接コマンドで実行

```bash
scripts/codex-image.sh "財務道場LPのヒーロー画像。明るいネイビーと金、横長16:9、文字なし" assets/hero.png
```

生成元の画像は `~/.codex/generated_images/<セッションID>/` にも残ります。

## 補足

- 以前あった `codex mcp-server`（Codex を MCP サーバーとして Claude Code に登録する方法）は 2026年9月に廃止されました。現在は今回の方法のように `codex exec` を呼び出します。
- Claude Code のクラウド環境（claude.ai/code）からは chatgpt.com に接続できないことがあります。その場合は手元の PC の Claude Code で使ってください。
- `~/.codex/auth.json` はパスワードと同じ扱いです。リポジトリにはコミットしないでください。
