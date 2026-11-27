// 問い合わせフォームへの入力（Playwright）。標準入力のJSON 1件を処理し、結果JSONを1行出力する。
// {url, send, screenshot, values:{company,name,email,tel,subject,body,...}}
// - send=false（既定）: 入力して画面を撮影するだけ。送信ボタンは押さない。
// - CAPTCHA・営業お断りの表記・用途不明の必須項目があれば何もせず中止する（回避しない）。
const { chromium } = require('playwright');

const KEYS = [
  ['company_kana', /(会社|法人|貴社|企業).*(カナ|かな|フリガナ|ふりがな)/i],
  ['company', /会社|法人|貴社|企業|団体|御社|company|organization|corp/i],
  ['dept', /部署|所属|役職|department|division/i],
  ['name_kana', /フリガナ|ふりがな|カナ|かな|kana|furigana|ruby/i],
  ['email_confirm', /(確認|再入力|confirm).*(メール|mail)|(メール|mail).*(確認|再入力|confirm)/i],
  ['email', /メール|mail/i],
  ['tel', /電話|tel|phone|携帯/i],
  ['zip', /郵便|zip|postal/i],
  ['address', /住所|所在地|address/i],
  ['url', /URL|ホームページ|サイト|website/i],
  ['subject', /件名|題名|タイトル|subject|title/i],
  ['body', /内容|本文|詳細|メッセージ|ご用件|ご質問|お問い?合わせ|message|inquiry|comment|body/i],
  ['name', /氏名|お名前|名前|担当者|name/i],
];
const PROHIBIT = /(営業|セールス|売り?込み|勧誘|宣伝|広告)[^。\n]{0,25}(お断り|ご遠慮|禁止|対応いたしかね|受け付けて(おり|い)ません)|(お断り|ご遠慮)[^。\n]{0,12}(営業|セールス|売り?込み|勧誘)/;

function out(o) { console.log(JSON.stringify(o)); }

(async () => {
  let job;
  try { job = JSON.parse(require('fs').readFileSync(0, 'utf8')); } catch (e) { return out({ ok: false, detail: '入力JSONが不正' }); }
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ locale: 'ja-JP' });
    await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1500);
    const text = await page.evaluate(() => document.body.innerText);
    const html = await page.content();
    if (PROHIBIT.test(text)) return out({ ok: false, detail: '営業お断りの表記あり。送信しない' });
    if (/recaptcha|hcaptcha|turnstile|captcha/i.test(html)) return out({ ok: false, detail: 'CAPTCHAあり。自動送信しない' });

    // 入力欄の情報を収集
    const fields = await page.evaluate(() => {
      const forms = [...document.querySelectorAll('form')].filter(f => f.querySelector('textarea'));
      const form = forms.sort((a, b) => b.elements.length - a.elements.length)[0];
      if (!form) return null;
      form.setAttribute('data-sfs', '1');
      return [...form.querySelectorAll('input, textarea, select')].map((el, i) => {
        el.setAttribute('data-sfs-i', String(i));
        const type = (el.getAttribute('type') || el.tagName).toLowerCase();
        let label = '';
        if (el.id) { const lb = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (lb) label = lb.innerText; }
        if (!label) { const p = el.closest('label, tr, dl, li, p, div'); if (p) label = p.innerText.slice(0, 60); }
        label += ' ' + (el.placeholder || '') + ' ' + (el.getAttribute('aria-label') || '');
        const required = el.required || /必須|\*|※/.test(label) || /required/.test(el.className || '');
        const options = el.tagName === 'SELECT' ? [...el.options].map(o => o.text.trim()) : [];
        return { i, type, name: el.name || '', label, required, options, visible: !!(el.offsetWidth || el.offsetHeight) };
      });
    });
    if (!fields) return out({ ok: false, detail: '本文欄のあるフォームを検出できず' });

    const v = job.values || {};
    const filled = [];
    for (const f of fields) {
      if (['hidden', 'submit', 'button', 'image', 'reset', 'file'].includes(f.type) || !f.visible) continue;
      const loc = page.locator(`[data-sfs-i="${f.i}"]`);
      if (f.type === 'select') {
        const opt = f.options.find(o => /営業|提案|協業/.test(o)) || f.options.find(o => /その他/.test(o));
        if (opt) { await loc.selectOption({ label: opt }); filled.push('区分:' + opt); }
        else if (f.required) return out({ ok: false, detail: '必須の選択欄に該当する区分なし: ' + f.options.slice(0, 5).join('/') });
        continue;
      }
      if (f.type === 'checkbox') {
        if (/同意|プライバシー|個人情報|承諾|agree|privacy/i.test(f.label + f.name)) { await loc.check(); filled.push('同意'); }
        else if (f.required) return out({ ok: false, detail: '用途不明の必須チェック欄: ' + f.label.trim().slice(0, 30) });
        continue;
      }
      if (f.type === 'radio') {
        if (/その他|営業|提案/.test(f.label)) { await loc.check().catch(() => {}); }
        continue;
      }
      let kind = f.type === 'email' ? (/確認|confirm|再/i.test(f.label + f.name) ? 'email_confirm' : 'email')
        : f.type === 'tel' ? 'tel' : f.type === 'textarea' ? 'body' : null;
      if (!kind) { const hit = KEYS.find(([, re]) => re.test(f.label + ' ' + f.name)); kind = hit ? hit[0] : null; }
      const val = kind ? v[kind] : '';
      if (val) { await loc.fill(String(val)); filled.push(kind); }
      else if (f.required) return out({ ok: false, detail: '入力できない必須項目: ' + (kind || f.label.trim().slice(0, 30) || f.name) });
    }
    if (!filled.includes('body')) return out({ ok: false, detail: '本文欄に入力できず' });
    await page.screenshot({ path: job.screenshot, fullPage: true });
    if (!job.send) return out({ ok: true, submitted: false, detail: '入力のみ（未送信）: ' + filled.join(',') });

    // 送信（確認画面がある場合は2段階）
    const btn = /送信|確認|submit|send|次へ|進む/i;
    const click = async () => {
      const b = page.locator('[data-sfs] button, [data-sfs] input[type=submit], form button, form input[type=submit]').filter({ hasText: btn }).first();
      const alt = page.locator('form input[type=submit], form button[type=submit]').first();
      const t = (await b.count()) ? b : alt;
      if (!(await t.count())) return false;
      await Promise.all([page.waitForLoadState('domcontentloaded').catch(() => {}), t.click()]);
      await page.waitForTimeout(2500);
      return true;
    };
    if (!(await click())) return out({ ok: false, detail: '送信ボタンを特定できず' });
    let body = await page.evaluate(() => document.body.innerText);
    const done = /ありがとうございま|送信(が)?完了|受け付けました|送信しました|thank you/i;
    if (!done.test(body) && /確認|内容でよろし|修正/.test(body)) { await click(); body = await page.evaluate(() => document.body.innerText); }
    await page.screenshot({ path: job.screenshot, fullPage: true });
    if (done.test(body)) return out({ ok: true, submitted: true, detail: '送信完了を確認' });
    return out({ ok: false, submitted: false, detail: '送信完了の表示を確認できず（未送信の可能性。画面を確認して手動対応）' });
  } catch (e) {
    return out({ ok: false, detail: 'エラー: ' + String(e.message || e).slice(0, 120) });
  } finally { await browser.close(); }
})();
