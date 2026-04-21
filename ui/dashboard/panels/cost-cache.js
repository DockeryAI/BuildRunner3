/* cost-cache.js — 24h/7d cost totals + cache hit ratio (Phase 11)
   Globals: window.CostCachePanel
   No framework. No ESM. Vanilla JS only. */

(function (window) {
  'use strict';

  var _container = null;
  var _data = {
    last_24h: null,
    last_7d: null,
    cache_runtimes: [],
    overall_hit_rate: null,
  };

  /* ---------- helpers ---------- */
  function _fmtUsd(n) {
    if (n == null) return '$—';
    if (n < 0.01) return '$' + n.toFixed(4);
    return '$' + n.toFixed(2);
  }

  function _fmtPct(r) {
    if (r == null) return '—%';
    return Math.round(r * 100) + '%';
  }

  function _fmtTokens(n) {
    if (n == null) return '—';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
    return String(n);
  }

  function _esc(str) {
    if (!str) return '—';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ---------- cost summary cards ---------- */
  function _renderCostCards() {
    var h24 = _data.last_24h;
    var h7d = _data.last_7d;

    function card(label, w) {
      if (!w) {
        return (
          '<div class="cost-card">' +
          '<div class="cost-window">' +
          label +
          '</div>' +
          '<div class="cost-value">$—</div>' +
          '</div>'
        );
      }
      var subParts = [];
      if (w.call_count != null) subParts.push(w.call_count + ' calls');
      if (w.total_input_tokens != null) subParts.push(_fmtTokens(w.total_input_tokens) + ' in');
      if (w.total_output_tokens != null) subParts.push(_fmtTokens(w.total_output_tokens) + ' out');
      return (
        '<div class="cost-card">' +
        '<div class="cost-window">' +
        label +
        '</div>' +
        '<div class="cost-value">' +
        _fmtUsd(w.total_cost_usd) +
        '</div>' +
        '<div class="cost-sub">' +
        subParts.join(' · ') +
        '</div>' +
        '</div>'
      );
    }

    return '<div class="cost-summary">' + card('24 h', h24) + card('7 d', h7d) + '</div>';
  }

  /* ---------- cache bars per runtime ---------- */
  function _renderCacheBars() {
    var runtimes = _data.cache_runtimes || [];
    if (!runtimes.length) {
      return '<div class="dimmed" style="font-size:11px">No cache data yet.</div>';
    }

    var overall = _data.overall_hit_rate;
    var overallRow =
      overall != null
        ? '<div class="cache-bar-row" style="margin-bottom:10px">' +
          '<div class="cache-runtime">' +
          '<span style="color:var(--text-primary);font-weight:600">Overall</span>' +
          '<span class="pct">' +
          _fmtPct(overall) +
          '</span>' +
          '</div>' +
          '<div class="cache-track">' +
          '<div class="cache-fill" style="width:' +
          Math.round(overall * 100) +
          '%;background:var(--accent-green)"></div>' +
          '</div>' +
          '</div>'
        : '';

    var bars = runtimes
      .map(function (rt) {
        var pct = Math.round((rt.cache_hit_rate || 0) * 100);
        return (
          '<div class="cache-bar-row">' +
          '<div class="cache-runtime">' +
          '<span>' +
          _esc(rt.runtime) +
          '</span>' +
          '<span class="pct">' +
          _fmtPct(rt.cache_hit_rate) +
          '</span>' +
          '</div>' +
          '<div class="cache-track">' +
          '<div class="cache-fill" style="width:' +
          pct +
          '%"></div>' +
          '</div>' +
          '</div>'
        );
      })
      .join('');

    return overallRow + bars;
  }

  /* ---------- full render ---------- */
  function _renderAll() {
    if (!_container) return;
    var body = _container.querySelector('.panel-body');
    if (!body) return;
    body.innerHTML =
      _renderCostCards() +
      '<div class="section-label">Cache hit rate by runtime (7d)</div>' +
      _renderCacheBars();
  }

  /* ---------- public API ---------- */

  function render(container) {
    _container = container;
    container.innerHTML =
      '<div class="panel">' +
      '<div class="panel-header">' +
      '<span class="panel-title">Cost &amp; Cache</span>' +
      '<span class="dimmed mono" style="font-size:10px">ledger · prompt cache</span>' +
      '</div>' +
      '<div class="panel-body"></div>' +
      '</div>';
    _renderAll();
  }

  function wire(container, ws) {
    _container = container;
    ws.addEventListener('message', function (evt) {
      var msg;
      try {
        msg = JSON.parse(evt.data);
      } catch (e) {
        return;
      }
      if (msg.type !== 'cost') return;
      var d = msg.data || {};
      if (d.last_24h) _data.last_24h = d.last_24h;
      if (d.last_7d) _data.last_7d = d.last_7d;
      if (d.cache_runtimes) _data.cache_runtimes = d.cache_runtimes;
      if (d.overall_hit_rate != null) _data.overall_hit_rate = d.overall_hit_rate;
      _renderAll();
    });
  }

  window.CostCachePanel = { render: render, wire: wire };
})(window);
