"""data/sources.json の公式資料を取得し、前回からの変化を検知する。

使い方: python3 cyber-insurance/check_sources.py
  - 取得結果のハッシュ等を data/sources_state.json に保存する。
  - 変化・新規・取得失敗をまとめて標準出力に出す（終了コードは常に0）。
  - PDF/HTMLの本体は cyber-insurance/.cache/ に保存する（git管理外）。
HTMLは日付やトークンで毎回変わることがあるため、タグを除いた本文テキストでハッシュを取る。
"""
import hashlib
import html as htmlmod
import json
import pathlib
import re
import subprocess
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
STATE = ROOT / "data/sources_state.json"


def fetch(url, out):
    r = subprocess.run(
        ["curl", "-s", "-L", "-m", "60", "-A", "cyber-insurance-monitor/1.0", "-o", str(out), "-w", "%{http_code} %{content_type}", url],
        capture_output=True, text=True,
    )
    code, _, ctype = r.stdout.partition(" ")
    return code, ctype


def text_hash(path, ctype):
    data = path.read_bytes()
    if "pdf" in ctype or data[:4] == b"%PDF":
        return hashlib.sha256(data).hexdigest(), "pdf"
    t = data.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", "", t)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
    # 照会日・アクセス時刻など毎回変わる日付を除外
    t = re.sub(r"\d{4}[/.-]\d{1,2}[/.-]\d{1,2}|\d{1,2}:\d{2}(:\d{2})?", "", t)
    t = re.sub(r"\s+", " ", t)
    return hashlib.sha256(t.encode()).hexdigest(), "html"


def main():
    CACHE.mkdir(exist_ok=True)
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))["sources"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    report = {"changed": [], "new": [], "failed": [], "same": 0}
    for s in sources:
        url = s["url"]
        key = hashlib.sha1(url.encode()).hexdigest()[:12]
        out = CACHE / key
        code, ctype = fetch(url, out)
        if code != "200" or not out.exists() or out.stat().st_size < 1000:
            report["failed"].append(f"[{s['id']}] {code} {url}")
            continue
        h, kind = text_hash(out, ctype)
        prev = state.get(url)
        entry = {"id": s["id"], "kind": s["kind"], "hash": h, "type": kind, "size": out.stat().st_size,
                 "cache": str(out.relative_to(ROOT)), "checked": date.today().isoformat(),
                 "changed": prev["changed"] if prev and prev["hash"] == h else date.today().isoformat()}
        if prev is None:
            report["new"].append(f"[{s['id']}] {url}")
        elif prev["hash"] != h:
            report["changed"].append(f"[{s['id']}] {s['kind']} {url}（前回変更 {prev['changed']}）")
        else:
            report["same"] += 1
        state[url] = entry
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("changed", "new", "failed"):
        print(f"## {k} ({len(report[k])})")
        for line in report[k]:
            print("-", line)
    print(f"## unchanged: {report['same']}")


if __name__ == "__main__":
    main()
