/* routing-ledger.js — last 50 skill routing decisions (Phase 11)
   Globals: window.RoutingLedgerPanel
   No framework. No ESM. Vanilla JS only. */

(function (window) {
  'use strict';

  var _container = null;
  var _rows = []; /* last 50 routing decisions */

  /* ---------- helpers ---------- */
  function _shortTs(ts) {
    if (!ts) return '—';
    var d = new Date(ts);
    return d.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }

  function _fmtMs(ms) {
    if (ms == null) return '—';
    if (ms >= 1000) return (ms / 1000).toFixed(1) + 's';
    return Math.round(ms) + 'ms';
  }

  function _esc(str) {
    if (!str) return '—';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ---------- render ---------- */
  function _renderTable() {
    if (!_rows.length) {
      return '<div class="dimmed" style="font-size:11px;padding:8px 0">No routing decisions yet.</div>';
    }
    var headerRow =
      '<tr>' +
      '<th>Time</th>' +
      '<th>Skill</th>' +
      '<th>Phase</th>' +
      '<th>Model</th>' +
      '<th>Runtime</th>' +
      '<th>Reason</th>' +
      '</tr>';

    var bodyRows = _rows
      .slice(0, 50)
      .map(function (r) {
        return (
          '<tr>' +
          '<td class="col-ts">' +
          _shortTs(r.ts) +
          '</td>' +
          '<td class="col-skill">' +
          _esc(r.skill) +
          '</td>' +
          '<td class="mono">' +
          _esc(r.phase) +
          '</td>' +
          '<td class="col-model">' +
          _esc(r.model) +
          '</td>' +
          '<td class="mono">' +
          _fmtMs(r.runtime_ms) +
          '</td>' +
          '<td class="col-reason" title="' +
          _esc(r.reason) +
          '">' +
          _esc(r.reason) +
          '</td>' +
          '</tr>'
        );
      })
      .join('');

    return (
      '<div class="ledger-scroll">' +
      '<table class="ledger-table">' +
      '<thead>' +
      headerRow +
      '</thead>' +
      '<tbody>' +
      bodyRows +
      '</tbody>' +
      '</table>' +
      '</div>'
    );
  }

  function _renderAll() {
    if (!_container) return;
    var body = _container.querySelector('.panel-body');
    if (!body) return;
    body.innerHTML = _renderTable();
  }

  /* ---------- public API ---------- */

  function render(container) {
    _container = container;
    container.innerHTML =
      '<div class="panel">' +
      '<div class="panel-header">' +
      '<span class="panel-title">Routing Ledger</span>' +
      '<span class="dimmed mono" style="font-size:10px">last 50</span>' +
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
      if (msg.type !== 'routing') return;
      var d = msg.data || {};

      if (Array.isArray(d.decisions)) {
        /* prepend newest, keep 50 */
        _rows = d.decisions.concat(_rows).slice(0, 50);
      }
      _renderAll();
    });
  }

  window.RoutingLedgerPanel = { render: render, wire: wire };
})(window);
