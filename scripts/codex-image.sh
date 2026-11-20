#!/usr/bin/env bash
# Codex CLI（ChatGPTサブスクでログイン済み）で画像を生成し、指定パスに保存する。
# 使い方: scripts/codex-image.sh "<プロンプト>" <出力パス.png>
#   例:   scripts/codex-image.sh "財務道場LPのヒーロー画像。明るいネイビーと金、横長16:9" assets/hero.png
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 \"<prompt>\" <output.png>" >&2
  exit 2
fi

PROMPT="$1"
OUT="$2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

command -v codex >/dev/null || { echo "codex が見つかりません: npm i -g @openai/codex" >&2; exit 1; }
if ! codex login status >/dev/null 2>&1; then
  echo "Codex に未ログインです。'codex login'（リモートなら 'codex login --device-auth'）で ChatGPT アカウントにログインしてください。" >&2
  exit 1
fi

mkdir -p "$ROOT/$(dirname "$OUT")"
MARKER="$(mktemp)"

codex exec \
  --skip-git-repo-check \
  -C "$ROOT" \
  -s workspace-write \
  "\$imagegen 次の内容で画像を1枚生成してください: ${PROMPT}
生成した画像を ${OUT} （作業ディレクトリからの相対パス）にコピーして保存してください。画像生成以外のファイル変更はしないでください。"

# Codex がコピーしなかった場合は、生成フォルダから最新の画像を拾う
if [ ! -s "$ROOT/$OUT" ]; then
  LATEST="$(find "$CODEX_HOME/generated_images" -type f -newer "$MARKER" \( -name '*.png' -o -name '*.gif' \) -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
  if [ -n "$LATEST" ]; then
    cp "$LATEST" "$ROOT/$OUT"
  fi
fi
rm -f "$MARKER"

if [ -s "$ROOT/$OUT" ]; then
  echo "saved: $OUT"
else
  echo "画像が保存されませんでした（使用上限・未対応プラン・ネットワークを確認してください）" >&2
  exit 1
fi
