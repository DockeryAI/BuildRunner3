/* node-health.js — 7-tile node health grid (Phase 11)
   Globals: window.NodeHealthPanel
   No framework. No ESM. Vanilla JS only. */

(function (window) {
  'use strict';

  /* ---------- constants ---------- */
  var NODES = [
    { id: 'muddy', label: 'Muddy', role: 'Command', cls: '' },
    { id: 'lockwood', label: 'Lockwood', role: 'Reserve', cls: '' },
    { id: 'walter', label: 'Walter', role: 'Sentinel', cls: '' },
    { id: 'otis', label: 'Otis', role: 'Builder', cls: '' },
    { id: 'lomax', label: 'Lomax', role: 'Reserve', cls: '' },
    { id: 'below', label: 'Below', role: 'Inference', cls: 'below' },
    { id: 'jimmy', label: 'Jimmy', role: 'Memory/Semantic', cls: 'jimmy' },
  ];

  /* Track VRAM-low start time for Below */
  var _belowVramLowSince = null;

  /* ---------- state ---------- */
  var _container = null;
  var _data = {};

  /* ---------- helpers ---------- */
  function _fmtMs(ms) {
    if (ms == null) return '—';
    if (ms >= 1000) return (ms / 1000).toFixed(1) + 's';
    return Math.round(ms) + 'ms';
  }

  function _fmtPct(v) {
    if (v == null) return '—';
    return Math.round(v) + '%';
  }

  function _fmtGb(bytes) {
    if (bytes == null) return '—';
    return (bytes / 1073741824).toFixed(1) + 'GB';
  }

  function _relTime(ts) {
    if (!ts) return '—';
    var diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return Math.floor(diff / 3600) + 'h ago';
  }

  function _statRow(label, val) {
    return (
      '<div class="node-stat"><span>' + label + '</span><span class="val">' + val + '</span></div>'
    );
  }

  /* ---------- VRAM alert logic ---------- */
  function _checkVramAlert(nodeData) {
    if (!nodeData) return false;
    var headroom = nodeData.vram_headroom_bytes;
    if (headroom == null) return false;
    if (headroom < 1073741824) {
      /* < 1 GB */
      if (_belowVramLowSince === null) _belowVramLowSince = Date.now();
      return Date.now() - _belowVramLowSince > 30000; /* > 30s */
    }
    _belowVramLowSince = null;
    return false;
  }

  function _vramGaugeCls(headroomBytes) {
    if (headroomBytes == null) return '';
    if (headroomBytes < 1073741824) return 'crit';
    if (headroomBytes < 2147483648) return 'warn';
    return '';
  }

  /* ---------- render tile ---------- */
  function _renderTile(node) {
    var d = _data[node.id] || {};
    var online = d.online === true;
    var tileCls = ['node-tile', node.cls, online ? 'online' : 'offline'].filter(Boolean).join(' ');

    var dotCls = online ? 'online' : 'offline';
    var header =
      '<div class="node-tile-name"><span class="status-dot ' +
      dotCls +
      '"></span>' +
      node.label +
      '</div>';
    var roleSpan = '<div class="node-stat"><span>' + node.role + '</span></div>';

    var stats = '';

    /* Common stats */
    if (d.cpu_pct != null) stats += _statRow('CPU', _fmtPct(d.cpu_pct));
    if (d.ram_pct != null) stats += _statRow('RAM', _fmtPct(d.ram_pct));
    if (d.active_tasks != null) stats += _statRow('Tasks', d.active_tasks);
    if (d.last_heartbeat) stats += _statRow('HB', _relTime(d.last_heartbeat));

    /* Jimmy-specific */
    if (node.id === 'jimmy') {
      if (d.lancedb_query_depth != null) stats += _statRow('LanceDB Q', d.lancedb_query_depth);
      if (d.reranker_queue != null) stats += _statRow('Reranker Q', d.reranker_queue);
      if (d.context_api_p95_ms != null) stats += _statRow('Ctx p95', _fmtMs(d.context_api_p95_ms));
    }

    /* Below-specific — GPU + VRAM */
    var vramHtml = '';
    if (node.id === 'below') {
      if (d.gpu_pct != null) stats += _statRow('GPU', _fmtPct(d.gpu_pct));
      var headroom = d.vram_headroom_bytes;
      var used = d.vram_used_bytes;
      var total = d.vram_total_bytes;
      if (headroom != null) {
        var alert = _checkVramAlert(d);
        var gaugePct = total ? Math.round((1 - headroom / total) * 100) : 0;
        var gaugeCls = alert ? 'crit' : _vramGaugeCls(headroom);
        stats += _statRow('VRAM free', _fmtGb(headroom) + (alert ? ' ⚠' : ''));
        vramHtml =
          '<div class="vram-gauge" title="VRAM used / total">' +
          '<div class="vram-gauge-fill ' +
          gaugeCls +
          '" style="width:' +
          gaugePct +
          '%"></div>' +
          '</div>';
      }
    }

    return (
      '<div class="' +
      tileCls +
      '" data-node="' +
      node.id +
      '">' +
      header +
      roleSpan +
      stats +
      vramHtml +
      '</div>'
    );
  }

  /* ---------- render / update ---------- */
  function _renderAll() {
    if (!_container) return;
    var grid = _container.querySelector('.node-grid');
    if (!grid) return;
    grid.innerHTML = NODES.map(_renderTile).join('');
  }

  /* ---------- public API ---------- */

  function render(container) {
    _container = container;
    container.innerHTML =
      '<div class="panel">' +
      '<div class="panel-header">' +
      '<span class="panel-title">Node Health</span>' +
      '<span class="dimmed mono" style="font-size:10px">7 nodes</span>' +
      '</div>' +
      '<div class="panel-body">' +
      '<div class="node-grid"></div>' +
      '</div>' +
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
      if (msg.type !== 'node-health') return;
      if (msg.data) {
        /* data is a map keyed by node id */
        Object.assign(_data, msg.data);
      }
      _renderAll();
    });
  }

  window.NodeHealthPanel = { render: render, wire: wire };
})(window);
