/* storage-health.js — Jimmy /srv/jimmy/ storage panel (Phase 11)
   Globals: window.StorageHealthPanel
   No framework. No ESM. Vanilla JS only. */

(function (window) {
  'use strict';

  var DIRS = [
    { key: 'research-library', label: 'research-library' },
    { key: 'lancedb', label: 'lancedb' },
    { key: 'memory', label: 'memory' },
    { key: 'backups/projects', label: 'backups/projects' },
    { key: 'backups/buildrunner-state', label: 'backups/br-state' },
    { key: 'backups/git-mirrors', label: 'backups/git-mirrors' },
    { key: 'backups/supabase', label: 'backups/supabase' },
    { key: 'backups/brlogger', label: 'backups/brlogger' },
    { key: 'archive/adversarial-reviews', label: 'archive/reviews' },
    { key: 'archive/cost-ledger', label: 'archive/cost-ledger' },
  ];

  var BACKUP_SOURCES = [
    { key: 'nightly-projects', label: 'nightly-projects', maxAge: 36 },
    { key: 'buildrunner-state', label: 'buildrunner-state', maxAge: 36 },
    { key: 'git-mirrors', label: 'git-mirrors', maxAge: 4 },
    { key: 'supabase', label: 'supabase', maxAge: 36 },
    { key: 'brlogger', label: 'brlogger', maxAge: 36 },
  ];

  var _container = null;
  var _data = {};

  /* ---------- helpers ---------- */
  function _fmtBytes(b) {
    if (b == null) return '—';
    if (b >= 1099511627776) return (b / 1099511627776).toFixed(1) + ' TB';
    if (b >= 1073741824) return (b / 1073741824).toFixed(1) + ' GB';
    if (b >= 1048576) return (b / 1048576).toFixed(0) + ' MB';
    return b + ' B';
  }

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

  function _ageHours(ts) {
    if (!ts) return Infinity;
    return (Date.now() - new Date(ts).getTime()) / 3600000;
  }

  function _barCls(pct) {
    if (pct >= 92) return 'crit';
    if (pct >= 80) return 'warn';
    return '';
  }

  /* ---------- disk-guard tier ---------- */
  function _tierBadge(dg) {
    if (!dg) return '';
    var cls, text;
    var pct = dg.pct || 0;
    if (pct >= 96) {
      cls = 'page';
      text = 'PAGE ≥96%';
    } else if (pct >= 92) {
      cls = 'crit';
      text = 'CRIT ' + pct + '%';
    } else if (pct >= 80) {
      cls = 'warn';
      text = 'WARN ' + pct + '%';
    } else {
      cls = 'ok';
      text = 'OK <80%';
    }
    return '<span class="tier-badge ' + cls + '">' + text + '</span>';
  }

  /* ---------- render dir bars ---------- */
  function _renderDirBars() {
    var dirs = _data.dirs || {};
    var total = _data.disk_total_bytes || 0;
    return DIRS.map(function (d) {
      var used = dirs[d.key] != null ? dirs[d.key] : null;
      var pct = total && used != null ? Math.min(100, Math.round((used / total) * 100)) : 0;
      var cls = _barCls(pct);
      return (
        '<div class="disk-bar-row">' +
        '<div class="disk-bar-label">' +
        '<span class="mono">/srv/jimmy/' +
        d.label +
        '</span>' +
        '<span class="pct">' +
        (used != null ? _fmtBytes(used) : '—') +
        '</span>' +
        '</div>' +
        '<div class="disk-bar-track">' +
        '<div class="disk-bar-fill ' +
        cls +
        '" style="width:' +
        pct +
        '%"></div>' +
        '</div>' +
        '</div>'
      );
    }).join('');
  }

  /* ---------- render backup timestamps ---------- */
  function _renderBackupTs() {
    var stamps = _data.backup_timestamps || {};
    return (
      '<div class="ts-grid">' +
      BACKUP_SOURCES.map(function (src) {
        var ts = stamps[src.key];
        var age = _ageHours(ts);
        var cls = age > src.maxAge ? 'stale' : 'ok';
        return (
          '<div class="ts-item">' +
          '<div class="ts-label">' +
          src.label +
          '</div>' +
          '<div class="ts-value ' +
          cls +
          '">' +
          _fmtTs(ts) +
          '</div>' +
          '</div>'
        );
      }).join('') +
      '</div>'
    );
  }

  /* ---------- render offsite sync ---------- */
  function _renderOffsite() {
    var o = _data.offsite_sync || {};
    var ts = o.last_run;
    var ok = o.success !== false;
    var age = _ageHours(ts);
    var stale = age > 24 * 8; /* >8 days */
    var cls = stale ? 'stale' : 'ok';
    return (
      '<div class="ts-item" style="margin-top:8px">' +
      '<div class="ts-label">off-site rclone</div>' +
      '<div class="ts-value ' +
      cls +
      '">' +
      (ok ? '✓ ' : '✗ ') +
      _fmtTs(ts) +
      '</div>' +
      '</div>'
    );
  }

  /* ---------- render cron timestamps ---------- */
  function _renderCronTs() {
    var c = _data.cron_timestamps || {};
    return (
      '<div class="ts-grid">' +
      '<div class="ts-item">' +
      '<div class="ts-label">archive-prune</div>' +
      '<div class="ts-value">' +
      _fmtTs(c.archive_prune) +
      '</div>' +
      '</div>' +
      '<div class="ts-item">' +
      '<div class="ts-label">lancedb-compact</div>' +
      '<div class="ts-value">' +
      _fmtTs(c.lancedb_compact) +
      '</div>' +
      '</div>' +
      '</div>'
    );
  }

  /* ---------- alert banners ---------- */
  function _hasStaleBacks() {
    var stamps = _data.backup_timestamps || {};
    return BACKUP_SOURCES.some(function (src) {
      return _ageHours(stamps[src.key]) > src.maxAge;
    });
  }

  function _hasStaleOffsite() {
    var o = _data.offsite_sync || {};
    return _ageHours(o.last_run) > 24 * 8;
  }

  /* ---------- full render ---------- */
  function _renderAll() {
    if (!_container) return;
    var body = _container.querySelector('.panel-body');
    if (!body) return;

    var staleBacks = _hasStaleBacks();
    var staleOffsite = _hasStaleOffsite();
    var backsPaused = !!_data.backups_paused;

    var redBanner = '';
    var magentaBanner = '';

    if (backsPaused) {
      magentaBanner =
        '<div class="alert-banner magenta visible">BACKUPS PAUSED — backups-paused flag is set</div>';
    }
    if (staleBacks || staleOffsite) {
      var msg = staleBacks ? 'Stale backup detected (>threshold)' : '';
      if (staleOffsite) msg += (msg ? ' · ' : '') + 'Off-site sync >8 days old';
      redBanner = '<div class="alert-banner red visible">' + msg + '</div>';
    }

    var dg = _data.disk_guard || null;
    var freeBytes = _data.disk_free_bytes;
    var totalBytes = _data.disk_total_bytes;
    var freePct =
      totalBytes && freeBytes != null ? Math.round((freeBytes / totalBytes) * 100) : null;

    var diskSummary =
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">' +
      '<span style="font-size:11px;color:var(--text-secondary)">Disk free: ' +
      (freeBytes != null ? _fmtBytes(freeBytes) : '—') +
      (freePct != null ? ' (' + freePct + '%)' : '') +
      '</span>' +
      _tierBadge(dg) +
      '</div>';

    body.innerHTML =
      magentaBanner +
      redBanner +
      diskSummary +
      '<div class="section-label">Directory usage</div>' +
      _renderDirBars() +
      '<div class="section-label">Last backup timestamps</div>' +
      _renderBackupTs() +
      _renderOffsite() +
      '<div class="section-label">Maintenance crons</div>' +
      _renderCronTs();
  }

  /* ---------- public API ---------- */

  function render(container) {
    _container = container;
    container.innerHTML =
      '<div class="panel" style="grid-column:span 2">' +
      '<div class="panel-header">' +
      '<span class="panel-title">Storage Health — /srv/jimmy/</span>' +
      '<span class="dimmed mono" style="font-size:10px">Jimmy 2TB NVMe</span>' +
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
      if (msg.type !== 'storage-health') return;
      if (msg.data) Object.assign(_data, msg.data);
      _renderAll();
    });
  }

  window.StorageHealthPanel = { render: render, wire: wire };
})(window);
