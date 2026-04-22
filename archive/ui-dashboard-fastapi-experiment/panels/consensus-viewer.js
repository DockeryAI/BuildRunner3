/* consensus-viewer.js — recent 3-way adversarial review results (Phase 11)
   Globals: window.ConsensusViewerPanel
   No framework. No ESM. Vanilla JS only. */

(function (window) {
  'use strict';

  var _container = null;
  var _reviews = []; /* last N review items */
  var MAX_SHOWN = 10;

  /* ---------- helpers ---------- */
  function _fmtTs(ts) {
    if (!ts) return '—';
    var d = new Date(ts);
    return d.toLocaleString([], {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  function _esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function _verdictCls(v) {
    if (!v) return '';
    var s = String(v).toLowerCase();
    if (s === 'pass') return 'pass';
    if (s === 'fail') return 'fail';
    if (s === 'escalate') return 'escalate';
    return '';
  }

  /* ---------- reviewer chips ---------- */
  function _reviewerChips(reviewers) {
    if (!Array.isArray(reviewers) || !reviewers.length) return '';
    return reviewers
      .map(function (r) {
        var cls = _verdictCls(r.verdict);
        return (
          '<span class="reviewer-chip ' +
          cls +
          '" title="' +
          _esc(r.model) +
          '">' +
          _esc(r.model || '?') +
          (r.verdict ? ': ' + _esc(r.verdict) : '') +
          '</span>'
        );
      })
      .join('');
  }

  /* ---------- render single review ---------- */
  function _renderItem(item) {
    var vCls = _verdictCls(item.verdict);
    return (
      '<div class="consensus-item">' +
      '<div class="consensus-header">' +
      '<span class="consensus-phase">Phase ' +
      _esc(item.phase) +
      ' · ' +
      _esc(item.target) +
      '</span>' +
      '<span class="consensus-ts">' +
      _fmtTs(item.ts) +
      '</span>' +
      '</div>' +
      '<div style="margin-bottom:5px">' +
      '<span class="verdict-badge ' +
      vCls +
      '">' +
      _esc(item.verdict || 'pending') +
      '</span>' +
      '</div>' +
      (item.reviewers
        ? '<div class="reviewer-row">' + _reviewerChips(item.reviewers) + '</div>'
        : '') +
      (item.arbiter_note
        ? '<div class="arbiter-note">Arbiter: ' + _esc(item.arbiter_note) + '</div>'
        : '') +
      (item.summary
        ? '<div style="font-size:10px;color:var(--text-secondary);margin-top:5px">' +
          _esc(item.summary) +
          '</div>'
        : '') +
      '</div>'
    );
  }

  /* ---------- full render ---------- */
  function _renderAll() {
    if (!_container) return;
    var body = _container.querySelector('.panel-body');
    if (!body) return;

    if (!_reviews.length) {
      body.innerHTML =
        '<div class="dimmed" style="font-size:11px;padding:8px 0">No reviews yet.</div>';
      return;
    }

    body.innerHTML =
      '<div class="consensus-list">' +
      _reviews.slice(0, MAX_SHOWN).map(_renderItem).join('') +
      '</div>';
  }

  /* ---------- public API ---------- */

  function render(container) {
    _container = container;
    container.innerHTML =
      '<div class="panel">' +
      '<div class="panel-header">' +
      '<span class="panel-title">Consensus Viewer</span>' +
      '<span class="dimmed mono" style="font-size:10px">adversarial reviews</span>' +
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
      if (msg.type !== 'consensus') return;
      var d = msg.data || {};

      if (Array.isArray(d.reviews)) {
        /* newest first, cap at MAX_SHOWN */
        _reviews = d.reviews.concat(_reviews).slice(0, MAX_SHOWN);
      }
      _renderAll();
    });
  }

  window.ConsensusViewerPanel = { render: render, wire: wire };
})(window);
