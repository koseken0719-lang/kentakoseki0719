"""data/sources.json の公式資料を取得し、前回からの変化を検知する。

使い方: python3 cyber-insurance/check_sources.py
  - 取得結果のハッシュ等を data/sources_state.json に保存する。
  - 変化・新規・取得失敗をまとめて標準出力に出す（終了コードは常に0）。
  - PDF/HTMLの本体は cyber-insurance/.cache/ に保存する（git管理外）。

sources.json の各項目で使えるオプション:
  extra_ca  : 中間証明書を送ってこないサーバー用。certs/ の中間証明書をシステムのCAに足して検証する
              （検証を無効にはしない）。
  flow=tcon : 東京海上のTコンシェル。カタログ頁を開いてセッションを作り、頁内のPDFダウンロードリンクをたどる。
  keywords  : ニュース一覧など。キーワードを含む行だけでハッシュを取り、新しく出てきた行を報告する。
HTMLは日付やトークンで毎回変わることがあるため、タグを除いた本文テキストでハッシュを取る。
ボット対策で拒否するサイト（損保ジャパン公式など）に対し、ブラウザを装う等の回避はしない。
"""
import hashlib
import html as htmlmod
import json
import pathlib
import re
import subprocess
import time
from datetime import date
from urllib.parse import urljoin

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
STATE = ROOT / "data/sources_state.json"
UA = "cyber-insurance-monitor/1.0"
SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"


def curl(url, out, extra=None):
    cmd = ["curl", "-s", "-L", "-m", "90", "-A", UA, "-o", str(out), "-w", "%{http_code} %{content_type}"]
    cmd += extra or []
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    code, _, ctype = r.stdout.partition(" ")
    return code, ctype


def ca_bundle(extra_ca):
    bundle = CACHE / ("bundle-" + pathlib.Path(extra_ca).stem + ".pem")
    bundle.write_bytes(pathlib.Path(SYSTEM_CA).read_bytes() + (ROOT / extra_ca).read_bytes())
    return ["--cacert", str(bundle)]


def fetch(s, out):
    extra = ca_bundle(s["extra_ca"]) if s.get("extra_ca") else []
    if s.get("flow") == "tcon":
        jar = CACHE / "tcon-cookies.txt"
        page = CACHE / "tcon-page.html"
        session = extra + ["-c", str(jar), "-b", str(jar)]
        code, _ = curl(s["url"], page, session)
        if code != "200":
            return code, ""
        t = page.read_text("utf-8", "ignore").replace("&amp;", "&")
        m = re.search(r"CatalogDownload\.tcon\?method=downloadPdfCatalog[^\"' ]*", t)
        if not m:
            return "no-link", ""
        return curl(urljoin(s["url"], m.group(0)), out, session + ["-e", s["url"]])
    code, ctype = curl(s["url"], out, extra)
    # <meta http-equiv="refresh"> で年度別ページへ飛ばすニュース一覧に対応
    if code == "200" and out.stat().st_size < 2000:
        m = re.search(r'http-equiv="refresh"[^>]*URL=([^"]+)"', out.read_text("utf-8", "ignore"), re.I)
        if m:
            code, ctype = curl(urljoin(s["url"], m.group(1)), out, extra)
    return code, ctype


def page_text(data):
    t = data.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", "", t)
    t = re.sub(r"(?i)<(br|/p|/li|/tr|/h\d|/div|/dd|/dt|/a)[^>]*>", "\n", t)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
    return [re.sub(r"\s+", " ", x).strip() for x in t.split("\n") if x.strip()]


def fingerprint(path, ctype, keywords):
    data = path.read_bytes()
    if "pdf" in ctype or data[:4] == b"%PDF":
        return hashlib.sha256(data).hexdigest(), "pdf", []
    lines = page_text(data)
    if keywords:
        lines = sorted({x for x in lines if any(k in x for k in keywords)})
    # 照会日・アクセス時刻など毎回変わる日付を除外（keywords指定時は日付も情報なので残す）
    body = "\n".join(lines) if keywords else re.sub(
        r"\d{4}[/.-]\d{1,2}[/.-]\d{1,2}|\d{1,2}:\d{2}(:\d{2})?", "", " ".join(lines))
    return hashlib.sha256(body.encode()).hexdigest(), "html", lines if keywords else []


def main():
    CACHE.mkdir(exist_ok=True)
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))["sources"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    report = {"changed": [], "new": [], "failed": [], "same": 0}
    today = date.today().isoformat()
    for s in sources:
        url = s["url"]
        out = CACHE / hashlib.sha1(url.encode()).hexdigest()[:12]
        code, ctype = fetch(s, out)
        if code != "200" and code != "403":  # 一時的な400/タイムアウトは1回だけ再試行（403=拒否は再試行しない）
            time.sleep(10)
            code, ctype = fetch(s, out)
        if code != "200" or not out.exists() or out.stat().st_size < 1000:
            report["failed"].append(f"[{s['id']}] {code} {url}" + (f"（{s['memo']}）" if s.get("memo") else ""))
            continue
        h, kind, lines = fingerprint(out, ctype, s.get("keywords"))
        prev = state.get(url)
        entry = {"id": s["id"], "kind": s["kind"], "hash": h, "type": kind, "size": out.stat().st_size,
                 "cache": str(out.relative_to(ROOT)), "checked": today,
                 "changed": prev["changed"] if prev and prev["hash"] == h else today}
        if lines:
            entry["lines"] = lines
        if prev is None:
            report["new"].append(f"[{s['id']}] {url}")
        elif prev["hash"] != h:
            msg = f"[{s['id']}] {s['kind']} {url}（前回変更 {prev['changed']}）"
            added = [x for x in lines if x not in set(prev.get("lines", []))]
            if added:
                msg += "\n    新着: " + "\n    新着: ".join(added[:10])
            report["changed"].append(msg)
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
