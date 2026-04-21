/* app.js — Cluster Max Dashboard WebSocket client (Phase 11)
   Vanilla JS. No ESM. Loaded after all panel scripts.
   Contract:
     - WS URL: ws://<host>:4400/ws
     - Exponential backoff: 500ms → 30s cap, retry indefinitely
     - Heartbeat: ping every 15s, force-close if no pong in 30s
     - On connect/reconnect: send {"type":"resync"} to replay full state
     - Messages: {"type": "<event>", "data": {...}} dispatched to panel by event type
*/

(function (window, document) {
  'use strict';

  var EVENT_TO_PANEL = {
    'node-health': { global: 'NodeHealthPanel', mount: 'p-node-health' },
    'overflow-reserve': { global: 'OverflowReservePanel', mount: 'p-overflow-reserve' },
    'storage-health': { global: 'StorageHealthPanel', mount: 'p-storage-health' },
    consensus: { global: 'ConsensusViewerPanel', mount: 'p-consensus' },
  };

  var BACKOFF_SCHEDULE = [500, 1000, 2000, 4000, 8000, 16000, 30000];
  var HEARTBEAT_INTERVAL_MS = 15000;
  var HEARTBEAT_TIMEOUT_MS = 30000;

  var _ws = null;
  var _attempt = 0;
  var _pingTimer = null;
  var _pongDeadline = 0;
  var _pongWatchdog = null;
  var _lastPingSent = 0;

  /* Boot every panel once — each panel keeps its own internal state. */
  function _bootPanels() {
    Object.keys(EVENT_TO_PANEL).forEach(function (evt) {
      var spec = EVENT_TO_PANEL[evt];
      var mount = document.getElementById(spec.mount);
      var panel = window[spec.global];
      if (!mount || !panel || typeof panel.render !== 'function') return;
      try {
        panel.render(mount, null);
      } catch (e) {
        console.error('render', evt, e);
      }
    });
  }

  function _dispatch(evt, data) {
    var spec = EVENT_TO_PANEL[evt];
    if (!spec) return;
    var mount = document.getElementById(spec.mount);
    var panel = window[spec.global];
    if (!mount || !panel) return;
    try {
      if (typeof panel.render === 'function') panel.render(mount, data);
    } catch (e) {
      console.error('dispatch', evt, e);
    }
  }

  function _setState(state) {
    var el = document.getElementById('ws-state');
    if (!el) return;
    el.className = 'ws-state ws-' + state;
    el.textContent = state;
  }

  function _setLatency(ms) {
    var el = document.getElementById('ws-latency');
    if (!el) return;
    el.textContent = ms == null ? '—' : Math.round(ms) + 'ms';
  }

  function _clearHeartbeat() {
    if (_pingTimer) {
      clearInterval(_pingTimer);
      _pingTimer = null;
    }
    if (_pongWatchdog) {
      clearInterval(_pongWatchdog);
      _pongWatchdog = null;
    }
    _lastPingSent = 0;
    _pongDeadline = 0;
  }

  function _startHeartbeat(ws) {
    _clearHeartbeat();
    _pongDeadline = Date.now() + HEARTBEAT_TIMEOUT_MS;
    _pingTimer = setInterval(function () {
      if (ws.readyState !== 1) return;
      _lastPingSent = Date.now();
      try {
        ws.send(JSON.stringify({ type: 'ping' }));
      } catch (e) {
        /* ignore */
      }
    }, HEARTBEAT_INTERVAL_MS);
    _pongWatchdog = setInterval(function () {
      if (Date.now() > _pongDeadline) {
        try {
          ws.close();
        } catch (e) {
          /* ignore */
        }
      }
    }, 2000);
  }

  function _onMessage(raw) {
    var msg;
    try {
      msg = JSON.parse(raw);
    } catch (e) {
      return;
    }
    if (!msg || !msg.type) return;
    if (msg.type === 'pong') {
      _pongDeadline = Date.now() + HEARTBEAT_TIMEOUT_MS;
      if (_lastPingSent) _setLatency(Date.now() - _lastPingSent);
      return;
    }
    _dispatch(msg.type, msg.data);
  }

  function _scheduleReconnect() {
    var delay = BACKOFF_SCHEDULE[Math.min(_attempt, BACKOFF_SCHEDULE.length - 1)];
    _attempt += 1;
    _setState('reconnecting');
    setTimeout(_connect, delay);
  }

  function _wsUrl() {
    var proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var host = window.location.hostname || '10.0.1.106';
    return proto + '//' + host + ':4400/ws';
  }

  function _connect() {
    _clearHeartbeat();
    _setState('connecting');
    try {
      _ws = new WebSocket(_wsUrl());
    } catch (e) {
      _scheduleReconnect();
      return;
    }
    _ws.addEventListener('open', function () {
      _attempt = 0;
      _setState('connected');
      _startHeartbeat(_ws);
      try {
        _ws.send(JSON.stringify({ type: 'resync' }));
      } catch (e) {
        /* ignore */
      }
    });
    _ws.addEventListener('message', function (ev) {
      _onMessage(ev.data);
    });
    _ws.addEventListener('close', function () {
      _clearHeartbeat();
      _setState('disconnected');
      _setLatency(null);
      _scheduleReconnect();
    });
    _ws.addEventListener('error', function () {
      try {
        _ws.close();
      } catch (e) {
        /* ignore */
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      _bootPanels();
      _connect();
    });
  } else {
    _bootPanels();
    _connect();
  }

  window.ClusterMaxDashboard = {
    reconnect: function () {
      try {
        _ws && _ws.close();
      } catch (e) {}
    },
  };
})(window, document);
