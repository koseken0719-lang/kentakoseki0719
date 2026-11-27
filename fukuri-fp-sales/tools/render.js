// ページをブラウザで描画し、HTML（iframe内を含む）を標準出力に返す。読み取りのみで、入力・送信はしない。
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ locale: 'ja-JP' });
    await page.goto(process.argv[2], { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(2000);
    let html = await page.content();
    for (const f of page.frames().slice(1)) { try { html += '\n<!--frame-->' + await f.content(); } catch (e) {} }
    process.stdout.write(html);
  } catch (e) { process.exitCode = 1; } finally { await browser.close(); }
})();
