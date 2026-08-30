#!/usr/bin/env python3
"""note/LinkedIn用ヘッダー画像ジェネレーター（財務道場ブランド）

使い方:
  python3 make_header.py config.json

config.json の例:
{
  "title": ["経営者との", "《初回面談》で、", "《保険の話》をしない理由"],
  "subtitle": "商品より先に、《会社の未来》を見る。",
  "tagline": "10年後も相談される営業へ。",
  "out": "header.png"
}

《...》で囲んだ部分が金色になる。
出力は 2560x1340px（note推奨1280x670の2倍解像度）。
"""
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROMIUM = "/opt/pw-browsers/chromium"
FONT_PATH = Path.home() / ".fonts" / "NotoSerifJP.ttf"
FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
            "notoserifjp/NotoSerifJP%5Bwght%5D.ttf")

LOGO_SVG = """
<svg class="mark" viewBox="0 0 100 100" aria-hidden="true">
  <defs>
    <linearGradient id="logo-gold-h" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#A97F2E"/>
      <stop offset=".55" stop-color="#C9A45C"/>
      <stop offset="1" stop-color="#E4C87E"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="47.5" fill="#fff" stroke="#C6CBD3" stroke-width="3"/>
  <path d="M91.07 34.23 A44 44 0 1 1 65.77 8.93" fill="none" stroke="#16324F" stroke-width="7" stroke-linecap="round"/>
  <rect x="28.5" y="53" width="10" height="20" fill="#16324F"/>
  <rect x="45" y="44" width="10" height="29" fill="#16324F"/>
  <rect x="61.5" y="35" width="10" height="38" fill="#16324F"/>
  <path d="M26 68.5 L78 20.5" stroke="#fff" stroke-width="13" stroke-linecap="round"/>
  <path d="M25 70 L74 24.2" stroke="url(#logo-gold-h)" stroke-width="7" stroke-linecap="round"/>
  <polygon points="85,14 79.4,30 68.5,18.3" fill="url(#logo-gold-h)"/>
</svg>
"""


def spans(text: str) -> str:
    """《...》を金色spanに変換する。"""
    out = []
    for part in re.split(r"(《[^》]*》)", text):
        if not part:
            continue
        if part.startswith("《") and part.endswith("》"):
            out.append(f'<span class="g">{html.escape(part[1:-1])}</span>')
        else:
            out.append(html.escape(part))
    return "".join(out)


def build_html(cfg: dict) -> str:
    title_lines = cfg["title"]
    max_chars = max(len(re.sub(r"[《》]", "", l)) for l in title_lines)
    cap = 102 if len(title_lines) <= 2 else 82  # 3行以上はフッターと重ならないよう小さく
    size = cfg.get("title_size") or max(56, min(cap, int(1080 / max_chars)))
    title_html = "".join(f'<div class="tl">{spans(l)}</div>' for l in title_lines)
    subtitle = cfg.get("subtitle", "")
    subtitle_html = f'<div class="subtitle">{spans(subtitle)}</div>' if subtitle else ""
    tagline = html.escape(cfg.get("tagline", "10年後も相談される営業へ。"))

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
@font-face {{
  font-family: 'NSJP';
  src: url('file://{FONT_PATH}') format('truetype-variations');
  font-weight: 200 900;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ zoom:2; }} /* 1280x670レイアウトを2倍解像度で出力する */
html,body {{ width:1280px; height:670px; overflow:hidden; }}
body {{
  font-family:'NSJP', serif;
  background:
    radial-gradient(ellipse 900px 520px at 50% 40%, rgba(46,80,140,.50), transparent 65%),
    radial-gradient(ellipse 1400px 900px at 50% 115%, rgba(6,12,26,.85), transparent 60%),
    linear-gradient(135deg, #0C1B36 0%, #13294E 52%, #0D1F3E 100%);
  position:relative; color:#fff;
}}
/* 飾り罫（二重の金枠＋四隅） */
.frame-outer {{ position:absolute; inset:24px; border:1.6px solid rgba(206,170,100,.80); }}
.frame-inner {{ position:absolute; inset:32px; border:1px solid rgba(206,170,100,.38); }}
.corner {{ position:absolute; width:14px; height:14px; border:1.6px solid rgba(222,188,118,.9); transform:rotate(45deg); background:#0e2244; }}
.corner.tl {{ top:17px; left:17px; }} .corner.tr {{ top:17px; right:17px; }}
.corner.bl {{ bottom:17px; left:17px; }} .corner.br {{ bottom:17px; right:17px; }}
/* 背景モチーフ */
.decor {{ position:absolute; pointer-events:none; }}
.chart {{ top:58px; left:64px; opacity:.85; }}
.bars-bg {{ bottom:70px; right:70px; opacity:.5; }}
.map {{ top:60px; right:80px; opacity:.55; }}
.arc {{ position:absolute; right:-180px; top:50%; width:560px; height:560px; margin-top:-280px;
  border:1.4px solid rgba(206,170,100,.28); border-radius:50%; }}
/* 本文 */
.stage {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:64px 90px 56px; text-align:center; }}
.title {{ font-weight:640; line-height:1.30; letter-spacing:.015em;
  font-size:{size}px; text-shadow:0 3px 18px rgba(0,0,0,.45); }}
.g {{ background:linear-gradient(180deg,#EAD08F 8%,#D7B266 55%,#B98F3F 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent; }}
.divider {{ display:flex; align-items:center; gap:14px; margin:30px 0 24px; width:520px; }}
.divider .line {{ flex:1; height:1px; background:linear-gradient(90deg,transparent,rgba(214,178,102,.9),transparent); }}
.divider .dia {{ width:8px; height:8px; transform:rotate(45deg); border:1.2px solid #D7B266; }}
.subtitle {{ font-weight:520; font-size:31px; letter-spacing:.10em; color:rgba(255,255,255,.94); }}
.brand {{ position:absolute; left:0; right:0; bottom:58px; display:flex; align-items:center; justify-content:center; gap:16px; }}
.brand .mark {{ width:46px; height:46px; filter:drop-shadow(0 2px 8px rgba(0,0,0,.4)); }}
.brand .name {{ font-weight:640; font-size:30px; letter-spacing:.12em; }}
.brand .sep {{ width:1px; height:30px; background:rgba(206,170,100,.65); }}
.brand .tag {{ font-weight:480; font-size:20px; letter-spacing:.12em; color:rgba(255,255,255,.88); }}
</style></head><body>
<div class="arc"></div>
<svg class="decor chart" width="300" height="170" viewBox="0 0 300 170" fill="none">
  <rect x="12" y="96" width="26" height="62" fill="rgba(38,68,120,.55)"/>
  <rect x="52" y="76" width="26" height="82" fill="rgba(38,68,120,.55)"/>
  <rect x="92" y="52" width="26" height="106" fill="rgba(38,68,120,.55)"/>
  <rect x="132" y="70" width="26" height="88" fill="rgba(38,68,120,.55)"/>
  <polyline points="14,120 62,88 108,102 158,58 206,72 258,22" stroke="#C9A45C" stroke-width="2.6"/>
  <g fill="#D7B266">
    <circle cx="14" cy="120" r="4.4"/><circle cx="62" cy="88" r="4.4"/><circle cx="108" cy="102" r="4.4"/>
    <circle cx="158" cy="58" r="4.4"/><circle cx="206" cy="72" r="4.4"/><circle cx="258" cy="22" r="4.4"/>
  </g>
</svg>
<svg class="decor map" width="340" height="180" viewBox="0 0 340 180" fill="rgba(58,92,150,.65)">
  <defs><pattern id="dots" width="11" height="11" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="2.1"/></pattern></defs>
  <path d="M18 38 Q40 12 78 20 Q110 6 128 26 Q150 18 160 40 Q140 66 112 60 Q92 84 66 72 Q34 78 24 58 Z" fill="url(#dots)"/>
  <path d="M170 60 Q200 30 250 38 Q296 24 322 52 Q330 84 300 96 Q272 122 236 108 Q198 118 182 92 Q164 78 170 60 Z" fill="url(#dots)"/>
  <path d="M90 100 Q120 92 132 112 Q140 140 116 152 Q88 158 76 136 Q74 110 90 100 Z" fill="url(#dots)"/>
</svg>
<svg class="decor bars-bg" width="240" height="130" viewBox="0 0 240 130" fill="none">
  <g stroke="rgba(120,150,200,.5)" stroke-width="1"><path d="M0 129h240M0 96h240M0 63h240M0 30h240"/></g>
  <rect x="18" y="76" width="30" height="53" fill="rgba(55,90,150,.6)"/>
  <rect x="70" y="56" width="30" height="73" fill="rgba(55,90,150,.6)"/>
  <rect x="122" y="66" width="30" height="63" fill="rgba(55,90,150,.6)"/>
  <rect x="174" y="34" width="30" height="95" fill="rgba(55,90,150,.6)"/>
</svg>
<div class="frame-outer"></div><div class="frame-inner"></div>
<div class="corner tl"></div><div class="corner tr"></div><div class="corner bl"></div><div class="corner br"></div>
<div class="stage">
  <div class="title">{title_html}</div>
  <div class="divider"><div class="line"></div><div class="dia"></div><div class="line"></div></div>
  {subtitle_html}
</div>
<div class="brand">{LOGO_SVG}<span class="name">財務道場</span><span class="sep"></span><span class="tag">{tagline}</span></div>
</body></html>"""


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not FONT_PATH.exists():
        FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sSL", "--retry", "3", "-o", str(FONT_PATH), FONT_URL], check=True)
    out = Path(cfg.get("out", "header.png")).resolve()
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(build_html(cfg))
        html_path = f.name
    subprocess.run([
        CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--window-size=2560,1340",
        f"--screenshot={out}", f"file://{html_path}",
    ], check=True, capture_output=True)
    print(out)


if __name__ == "__main__":
    main()
