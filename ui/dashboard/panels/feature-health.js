/* feature-health.js — 15-tile feature health grid (Phase 6 — cluster-activation)
   Globals: window.FeatureHealthPanel
   No framework. No ESM. Vanilla JS only.
   Tile status: green | yellow | red — never "unknown".
*/

(function (window) {
  'use strict';

  /* ---------- state ---------- */
  var _container = null;
  var _tiles = [];
  var _collectedAt = null;

  /* ---------- helpers ---------- */
  function _relTime(ts) {
    if (!ts) return '—';
    var diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return Math.floor(diff / 3600) + 'h ago';
  }

  function _statusDot(status) {
    return '<span class="status-dot ' + status + '"></span>';
  }

  /* ---------- render single tile ---------- */
  function _renderTile(tile) {
    var status = tile.status || 'yellow';
    var label = tile.label || 'Tile ' + tile.tile;
    var detail = tile.detail || '';
    var idx = tile.tile || 0;

    return (
      '<div class="fh-tile fh-' +
      status +
      '" data-tile="' +
      idx +
      '" title="' +
      _escHtml(detail) +
      '">' +
      '<div class="fh-tile-header">' +
      _statusDot(status) +
      '<span class="fh-tile-num">' +
      idx +
      '</span>' +
      '</div>' +
      '<div class="fh-tile-label">' +
      _escHtml(label) +
      '</div>' +
      '<div class="fh-tile-detail">' +
      _escHtml(detail) +
      '</div>' +
      '</div>'
    );
  }

  function _escHtml(s) {
    if (!s) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ---------- render / update ---------- */
  function _renderAll() {
    if (!_container) return;
    var grid = _container.querySelector('.fh-grid');
    if (!grid) return;

    if (!_tiles || _tiles.length === 0) {
      /* Render placeholder tiles with yellow default — never leave "unknown" */
      var placeholders = [];
      var TILE_LABELS = [
        'Role Matrix dispatch',
        'RuntimeRegistry health',
        '3-way adversarial review',
        'Cache breakpoints',
        'Codex bridge',
        'Auto-context Jimmy /retrieve',
        'Local routing Below',
        'Otis dispatch',
        'Walter gate',
        'Lomax shard',
        'Cluster daemon',
        'Node matrix consulted',
        'Dispatch log writer',
        'Context bundle parity',
        'Adversarial review cap',
      ];
      for (var i = 0; i < 15; i++) {
        placeholders.push({
          tile: i + 1,
          label: TILE_LABELS[i],
          status: 'yellow',
          detail: 'no data in last 24h',
        });
      }
      grid.innerHTML = placeholders.map(_renderTile).join('');
      return;
    }

    grid.innerHTML = _tiles.map(_renderTile).join('');

    /* Update summary counts */
    var summary = _container.querySelector('.fh-summary');
    if (summary) {
      var green = _tiles.filter(function (t) {
        return t.status === 'green';
      }).length;
      var yellow = _tiles.filter(function (t) {
        return t.status === 'yellow';
      }).length;
      var red = _tiles.filter(function (t) {
        return t.status === 'red';
      }).length;
      summary.innerHTML =
        '<span class="fh-count fh-green">' +
        green +
        ' green</span>' +
        '<span class="fh-count fh-yellow">' +
        yellow +
        ' yellow</span>' +
        '<span class="fh-count fh-red">' +
        red +
        ' red</span>' +
        (_collectedAt ? '<span class="fh-ts">updated ' + _relTime(_collectedAt) + '</span>' : '');
    }
  }

  /* ---------- public API ---------- */

  function render(container, data) {
    _container = container;

    /* First call: build shell */
    if (!container.querySelector('.fh-panel')) {
      container.innerHTML =
        '<div class="fh-panel">' +
        '<div class="panel-header">' +
        '<span class="panel-title">Feature Health</span>' +
        '<div class="fh-summary"></div>' +
        '</div>' +
        '<div class="panel-body">' +
        '<div class="fh-grid"></div>' +
        '</div>' +
        '</div>';
    }

    /* Accept data payload from WS broadcast */
    if (data && Array.isArray(data.tiles)) {
      _tiles = data.tiles;
      _collectedAt = data.collected_at || null;
    } else if (data === null) {
      /* Initial render with no data — show yellow placeholders */
      _tiles = [];
      _collectedAt = null;
    }

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
      if (msg.type !== 'feature-health') return;
      if (msg.data && Array.isArray(msg.data.tiles)) {
        _tiles = msg.data.tiles;
        _collectedAt = msg.data.collected_at || null;
      }
      _renderAll();
    });
  }

  window.FeatureHealthPanel = { render: render, wire: wire };
})(window);
