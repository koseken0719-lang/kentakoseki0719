/* =========================================================================
   共通スクリプト
   1) コンバージョン計測（data-ev 属性のクリックを送信）
      - Googleアナリティクス(gtag) / GTM(dataLayer) が入っていれば送信
      - 入っていなければ何もしない（エラーにならない）
   2) 読みもの記事カードの描画
   ========================================================================= */
(function () {
  'use strict';

  /* ---------- 1) イベント計測 ---------- */
  function track(name, params) {
    try {
      if (typeof window.gtag === 'function') {
        window.gtag('event', name, params || {});
      }
      if (Array.isArray(window.dataLayer)) {
        window.dataLayer.push(Object.assign({ event: name }, params || {}));
      }
    } catch (e) { /* 計測失敗でページ動作は止めない */ }
  }
  window.sphenosTrack = track;

  document.addEventListener('click', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-ev]') : null;
    if (el) { track(el.getAttribute('data-ev'), { link_url: el.getAttribute('href') || '' }); return; }
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (href.indexOf('mailto:') === 0) track('click_mail', { link_url: href });
    else if (href.indexOf('tel:') === 0) track('click_tel', { link_url: href });
    else if (href.indexOf('lin.ee') > -1 || href.indexOf('line.me') > -1) track('click_line', { link_url: href });
    else if (href.indexOf('note.com') > -1) track('click_note', { link_url: href });
    else if (href.indexOf('linkedin.com') > -1) track('click_linkedin', { link_url: href });
    else if (href.indexOf('facebook.com') > -1) track('click_facebook', { link_url: href });
  });

  /* ---------- 2) 読みもの記事カード ---------- */
  function fmtDate(iso) {
    var p = String(iso).split('-');
    return p.length === 3 ? p[0] + '.' + p[1] + '.' + p[2] : iso;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function renderArticles(gridId, limit) {
    var grid = document.getElementById(gridId);
    if (!grid || !Array.isArray(window.ARTICLES)) return;
    var list = window.ARTICLES.slice(0, limit || window.ARTICLES.length);
    grid.innerHTML = list.map(function (a) {
      var ext = a.external ? ' target="_blank" rel="noopener"' : '';
      var rel = a.related
        ? '<span class="for">関連：' + esc(a.related.label) + '</span>'
        : '';
      return '<a class="col-card reveal in" href="' + esc(a.url) + '"' + ext + ' data-ev="' + (a.external ? 'click_note_article' : 'click_column_article') + '">' +
        '<div class="meta"><span class="cat">' + esc(a.category) + '</span><time datetime="' + esc(a.date) + '">' + fmtDate(a.date) + '</time></div>' +
        '<h3>' + esc(a.title) + '</h3>' +
        '<p>' + esc(a.excerpt) + '</p>' +
        '<span class="for">対象：' + esc(a.audience) + '</span>' +
        rel +
        '<span class="more">' + (a.external ? 'noteで読む' : '記事を読む') +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg></span>' +
        '</a>';
    }).join('');
  }
  window.renderArticles = renderArticles;

  document.addEventListener('DOMContentLoaded', function () {
    renderArticles('col-grid', 3);
    renderArticles('col-grid-all');
  });
})();
