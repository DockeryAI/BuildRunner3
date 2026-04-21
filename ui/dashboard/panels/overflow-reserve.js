/* overflow-reserve.js — Lockwood + Lomax reserve state panel (Phase 11)
   Globals: window.OverflowReservePanel
   No framework. No ESM. Vanilla JS only. */

(function (window) {
  'use strict';

  var RESERVE_NODES = ['lockwood', 'lomax'];
  var STATES = ['idle', 'warming', 'active', 'draining'];

  var _container = null;
  var _nodeState = {
    lockwood: { state: 'idle', since: null },
    lomax: { state: 'idle', since: null },
  };
  var _events = []; /* last 20 wake/drain events */
  var _freq = {}; /* { date: count } — overflow frequency per 24h bucket */

  /* ---------- helpers ---------- */
  function _relTime(ts) {
    if (!ts) return '—';
    var diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return Math.floor(diff / 3600) + 'h ago';
  }

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

  /* ---------- render reserve tile ---------- */
  function _renderReserveTile(nodeId) {
    var s = _nodeState[nodeId] || { state: 'idle', since: null };
    var label = nodeId.charAt(0).toUpperCase() + nodeId.slice(1);
    var sinceTxt = s.since ? _relTime(s.since) : '—';

    return (
      '<div class="reserve-tile">' +
      '<div style="font-size:12px;font-weight:700;margin-bottom:4px">' +
      label +
      '</div>' +
      '<div><span class="reserve-state ' +
      s.state +
      '">' +
      s.state.toUpperCase() +
      '</span></div>' +
      '<div style="font-size:10px;color:var(--text-muted);margin-top:5px">since ' +
      sinceTxt +
      '</div>' +
      '</div>'
    );
  }

  /* ---------- render event log ---------- */
  function _renderEventLog() {
    if (!_events.length) {
      return '<div class="dimmed" style="font-size:11px;padding:6px 0">No events yet.</div>';
    }
    var rows = _events
      .slice(0, 20)
      .map(function (e) {
        var dirCls = e.direction === 'wake' ? 'wake' : 'drain';
        return (
          '<div class="event-row">' +
          '<span class="event-ts">' +
          _shortTs(e.ts) +
          '</span>' +
          '<span class="event-node">' +
          (e.node || '—') +
          '</span>' +
          '<span class="event-dir ' +
          dirCls +
          '">' +
          (e.direction || '—') +
          '</span>' +
          '<span class="event-cause">' +
          (e.cause || '—') +
          '</span>' +
          '</div>'
        );
      })
      .join('');
    return '<div class="event-log">' + rows + '</div>';
  }

  /* ---------- render freq ---------- */
  function _renderFreq() {
    var keys = Object.keys(_freq).sort().slice(-7);
    if (!keys.length) return '';
    var rows = keys
      .map(function (k) {
        return (
          '<div class="freq-row"><span>' +
          k +
          '</span><span class="freq-val">' +
          _freq[k] +
          '</span></div>'
        );
      })
      .join('');
    return '<div class="section-label">Overflow frequency (per day)</div>' + rows;
  }

  /* ---------- full render ---------- */
  function _renderAll() {
    if (!_container) return;
    var body = _container.querySelector('.panel-body');
    if (!body) return;

    var tiles =
      '<div class="reserve-tiles">' + RESERVE_NODES.map(_renderReserveTile).join('') + '</div>';

    var logSection =
      '<div class="section-label">Wake / drain events (last 20)</div>' + _renderEventLog();

    var freqSection = _renderFreq();

    body.innerHTML = tiles + logSection + freqSection;
  }

  /* ---------- public API ---------- */

  function render(container) {
    _container = container;
    container.innerHTML =
      '<div class="panel">' +
      '<div class="panel-header">' +
      '<span class="panel-title">Overflow Reserve</span>' +
      '<span class="dimmed mono" style="font-size:10px">Lockwood · Lomax</span>' +
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
      if (msg.type !== 'overflow-reserve') return;
      var d = msg.data || {};

      /* node states */
      if (d.nodes) {
        RESERVE_NODES.forEach(function (id) {
          if (d.nodes[id]) {
            _nodeState[id] = d.nodes[id];
          }
        });
      }

      /* event log — prepend new events, keep last 20 */
      if (Array.isArray(d.events)) {
        _events = d.events.concat(_events).slice(0, 20);
      }

      /* overflow frequency */
      if (d.freq) {
        Object.assign(_freq, d.freq);
      }

      _renderAll();
    });
  }

  window.OverflowReservePanel = { render: render, wire: wire };
})(window);
