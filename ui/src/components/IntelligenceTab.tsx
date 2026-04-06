/**
 * IntelligenceTab Component
 *
 * Live intelligence radar showing Claude/Anthropic capabilities,
 * community innovations, and cluster-relevant tools from Lockwood.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { intelAPI } from '../services/api';
import type { IntelItem, IntelAlerts, IntelImprovement, IntelFilters } from '../types';
import './IntelligenceTab.css';

type ImprovementStatus = 'pending' | 'planned' | 'built' | 'archived';

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const TIME_RANGES: { label: string; days: number | undefined }[] = [
  { label: '24h', days: 1 },
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: 'All', days: undefined },
];

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface IntelligenceTabProps {
  onAlertCount?: (count: number) => void;
  onImprovementCount?: (count: number) => void;
}

export function IntelligenceTab({ onAlertCount, onImprovementCount }: IntelligenceTabProps) {
  const [items, setItems] = useState<IntelItem[]>([]);
  const [alerts, setAlerts] = useState<IntelAlerts>({ critical_count: 0, high_count: 0 });
  const [improvements, setImprovements] = useState<IntelImprovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [planModalImprovement, setPlanModalImprovement] = useState<IntelImprovement | null>(null);
  const [buildSpecInput, setBuildSpecInput] = useState('');
  const [statusFilter, setStatusFilter] = useState<ImprovementStatus | ''>('');

  // Filters
  const [sourceType, setSourceType] = useState<string>('');
  const [category, setCategory] = useState<string>('');
  const [priority, setPriority] = useState<string>('');
  const [timeRange, setTimeRange] = useState<number | undefined>(7);

  const itemsIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const alertsIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadItems = useCallback(async () => {
    try {
      const filters: IntelFilters = { limit: 100 };
      if (sourceType) filters.source_type = sourceType;
      if (category) filters.category = category;
      if (priority) filters.priority = priority;
      if (timeRange) filters.days = timeRange;

      const data = await intelAPI.getIntelItems(filters);
      // Sort by priority then by collected_at desc
      const sorted = [...data.items].sort((a, b) => {
        const pa = PRIORITY_ORDER[a.priority] ?? 4;
        const pb = PRIORITY_ORDER[b.priority] ?? 4;
        if (pa !== pb) return pa - pb;
        return new Date(b.collected_at).getTime() - new Date(a.collected_at).getTime();
      });
      setItems(sorted);
      setError(null);
    } catch (err) {
      setError('Failed to load intelligence data. Is Lockwood online?');
      console.error('Intel load error:', err);
    } finally {
      setLoading(false);
    }
  }, [sourceType, category, priority, timeRange]);

  const loadAlerts = useCallback(async () => {
    try {
      const data = await intelAPI.getIntelAlerts();
      setAlerts(data);
      onAlertCount?.(data.critical_count + data.high_count);
    } catch {
      // Silent — alerts are non-critical
    }
  }, [onAlertCount]);

  const loadImprovements = useCallback(async () => {
    try {
      const status = statusFilter || undefined;
      const data = await intelAPI.getIntelImprovements(status);
      setImprovements(data.improvements);
      // Report pending count for header badge
      if (!statusFilter) {
        const pendingCount = data.improvements.filter((i) => i.status === 'pending').length;
        onImprovementCount?.(pendingCount);
      }
    } catch {
      // Silent — improvements endpoint may not exist yet
    }
  }, [onImprovementCount, statusFilter]);

  useEffect(() => {
    loadItems();
    loadAlerts();
    loadImprovements();

    // Auto-refresh: items every 30s, alerts every 15s
    itemsIntervalRef.current = setInterval(loadItems, 30000);
    alertsIntervalRef.current = setInterval(loadAlerts, 15000);

    return () => {
      if (itemsIntervalRef.current) clearInterval(itemsIntervalRef.current);
      if (alertsIntervalRef.current) clearInterval(alertsIntervalRef.current);
    };
  }, [loadItems, loadAlerts, loadImprovements]);

  const handleSaveToLibrary = async (id: number) => {
    try {
      await intelAPI.saveToLibrary(id);
    } catch (err) {
      console.error('Save to library failed:', err);
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await intelAPI.dismissIntelItem(id);
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, dismissed: true } : item))
      );
    } catch (err) {
      console.error('Dismiss failed:', err);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await intelAPI.markIntelRead(id);
      setItems((prev) => prev.map((item) => (item.id === id ? { ...item, read: true } : item)));
      loadAlerts(); // Refresh alert count
    } catch (err) {
      console.error('Mark read failed:', err);
    }
  };

  const handleCopyCommand = async (prompt: string, improvementId: number) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedId(improvementId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback for non-HTTPS contexts
      const textArea = document.createElement('textarea');
      textArea.value = prompt;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopiedId(improvementId);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const handlePlanThis = (imp: IntelImprovement) => {
    setPlanModalImprovement(imp);
    setBuildSpecInput('');
  };

  const handleClosePlanModal = () => {
    setPlanModalImprovement(null);
    setBuildSpecInput('');
  };

  const handleMarkPlanned = async (imp: IntelImprovement) => {
    if (!buildSpecInput.trim()) return;
    try {
      await intelAPI.updateImprovementStatus(imp.id, 'planned', buildSpecInput.trim());
      handleClosePlanModal();
      loadImprovements();
    } catch (err) {
      console.error('Failed to update improvement status:', err);
    }
  };

  const handleUpdateStatus = async (id: number, status: ImprovementStatus) => {
    try {
      await intelAPI.updateImprovementStatus(id, status);
      loadImprovements();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const totalAlerts = alerts.critical_count + alerts.high_count;

  if (loading && items.length === 0) {
    return (
      <div className="intelligence-tab">
        <div className="intel-loading">Loading intelligence feed...</div>
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="intelligence-tab">
        <div className="intel-error">{error}</div>
      </div>
    );
  }

  const visibleItems = items.filter((item) => !item.dismissed);

  return (
    <div className="intelligence-tab">
      <h2>
        Intelligence Radar
        <span className="intel-header-badges">
          {totalAlerts > 0 && <span className="alert-badge">{totalAlerts}</span>}
          {improvements.length > 0 && (
            <span className="improvement-badge">
              {improvements.length} improvement{improvements.length !== 1 ? 's' : ''} pending
            </span>
          )}
        </span>
      </h2>

      {/* Filter Bar */}
      <div className="intel-filter-bar">
        <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
          <option value="">All Sources</option>
          <option value="Official">Official</option>
          <option value="Community">Community</option>
          <option value="Blog">Blog</option>
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All Categories</option>
          <option value="api-change">API Change</option>
          <option value="model-release">Model Release</option>
          <option value="community-tool">Community Tool</option>
          <option value="ecosystem-news">Ecosystem News</option>
          <option value="cluster-relevant">Cluster Relevant</option>
          <option value="general-news">General News</option>
        </select>
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={timeRange ?? ''}
          onChange={(e) => setTimeRange(e.target.value ? Number(e.target.value) : undefined)}
        >
          {TIME_RANGES.map((tr) => (
            <option key={tr.label} value={tr.days ?? ''}>
              {tr.label}
            </option>
          ))}
        </select>
      </div>

      {/* Improvements Panel */}
      {improvements.length > 0 && (
        <div className="improvements-panel">
          <div className="improvements-panel-header">
            <h3>BR3 Improvements</h3>
            <select
              className="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ImprovementStatus | '')}
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="planned">Planned</option>
              <option value="built">Built</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          {improvements.map((imp) => (
            <div key={imp.id} className={`improvement-card status-${imp.status || 'pending'}`}>
              <div className="improvement-card-title">
                {imp.title}
                <span className={`complexity-badge ${imp.complexity}`}>{imp.complexity}</span>
                <span className={`status-badge status-${imp.status || 'pending'}`}>
                  {imp.status || 'pending'}
                </span>
                {imp.overlap_action && (
                  <span className={`overlap-badge overlap-${imp.overlap_action}`}>
                    {imp.overlap_action}
                  </span>
                )}
              </div>
              <div className="improvement-card-rationale">{imp.rationale}</div>
              {imp.overlap_notes && (
                <div className="improvement-card-overlap">{imp.overlap_notes}</div>
              )}
              {imp.build_spec_name && (
                <div className="improvement-card-spec">
                  Linked to: <strong>{imp.build_spec_name}</strong>
                </div>
              )}
              {imp.affected_files && imp.affected_files.length > 0 && (
                <div className="improvement-card-files">
                  Affects: {imp.affected_files.join(', ')}
                </div>
              )}
              <div className="setlist-prompt">
                <code>{imp.setlist_prompt}</code>
                <button
                  className="btn-copy"
                  onClick={() => handleCopyCommand(imp.setlist_prompt, imp.id)}
                >
                  {copiedId === imp.id ? 'Copied!' : 'Copy Command'}
                </button>
              </div>
              <div className="improvement-actions">
                {(imp.status === 'pending' || !imp.status) && (
                  <button className="btn-plan-this" onClick={() => handlePlanThis(imp)}>
                    Plan This
                  </button>
                )}
                {imp.status === 'planned' && (
                  <button
                    className="btn-mark-built"
                    onClick={() => handleUpdateStatus(imp.id, 'built')}
                  >
                    Mark Built
                  </button>
                )}
                {imp.status !== 'archived' && (
                  <button
                    className="btn-archive"
                    onClick={() => handleUpdateStatus(imp.id, 'archived')}
                  >
                    Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Plan This Modal */}
      {planModalImprovement && (
        <div className="plan-modal-overlay" onClick={handleClosePlanModal}>
          <div className="plan-modal" onClick={(e) => e.stopPropagation()}>
            <div className="plan-modal-header">
              <h3>Plan This Improvement</h3>
              <button className="plan-modal-close" onClick={handleClosePlanModal}>
                &times;
              </button>
            </div>
            <div className="plan-modal-body">
              <div className="plan-modal-field">
                <label>Improvement</label>
                <div className="plan-modal-value">{planModalImprovement.title}</div>
              </div>
              <div className="plan-modal-field">
                <label>Complexity</label>
                <span className={`complexity-badge ${planModalImprovement.complexity}`}>
                  {planModalImprovement.complexity}
                </span>
              </div>
              <div className="plan-modal-field">
                <label>Rationale</label>
                <div className="plan-modal-value">{planModalImprovement.rationale}</div>
              </div>
              {planModalImprovement.overlap_action && (
                <div className="plan-modal-field">
                  <label>Overlap</label>
                  <div className="plan-modal-value">
                    <span
                      className={`overlap-badge overlap-${planModalImprovement.overlap_action}`}
                    >
                      {planModalImprovement.overlap_action}
                    </span>
                    {planModalImprovement.overlap_notes && (
                      <span style={{ marginLeft: 8 }}>{planModalImprovement.overlap_notes}</span>
                    )}
                  </div>
                </div>
              )}
              {planModalImprovement.affected_files &&
                planModalImprovement.affected_files.length > 0 && (
                  <div className="plan-modal-field">
                    <label>Affected Systems</label>
                    <div className="plan-modal-files">
                      {planModalImprovement.affected_files.map((f, i) => (
                        <code key={i}>{f}</code>
                      ))}
                    </div>
                  </div>
                )}
              <div className="plan-modal-field">
                <label>/setlist Command</label>
                <div className="setlist-prompt">
                  <code>{planModalImprovement.setlist_prompt}</code>
                  <button
                    className="btn-copy"
                    onClick={() =>
                      handleCopyCommand(
                        planModalImprovement.setlist_prompt,
                        planModalImprovement.id
                      )
                    }
                  >
                    {copiedId === planModalImprovement.id ? 'Copied!' : 'Copy /setlist Command'}
                  </button>
                </div>
              </div>
              <div className="plan-modal-field">
                <label>BUILD Spec Name (to link)</label>
                <input
                  type="text"
                  className="plan-modal-input"
                  placeholder="e.g. BUILD_agent-teams-ga.md"
                  value={buildSpecInput}
                  onChange={(e) => setBuildSpecInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleMarkPlanned(planModalImprovement);
                  }}
                />
              </div>
            </div>
            <div className="plan-modal-footer">
              <button className="btn-cancel" onClick={handleClosePlanModal}>
                Cancel
              </button>
              <button
                className="btn-mark-planned"
                disabled={!buildSpecInput.trim()}
                onClick={() => handleMarkPlanned(planModalImprovement)}
              >
                Mark as Planned
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Items List */}
      {visibleItems.length === 0 ? (
        <div className="intel-empty">
          No intelligence items found
          <div className="intel-empty-hint">
            Items will appear as Lockwood collects from configured sources
          </div>
        </div>
      ) : (
        <div className="intel-items-list">
          {visibleItems.map((item) => (
            <div
              key={item.id}
              className={`intel-item priority-${item.priority}${item.dismissed ? ' dismissed' : ''}${item.read ? ' read-item' : ''}`}
              onClick={() => toggleExpand(item.id)}
            >
              <div className="intel-item-header">
                <span className={`priority-dot ${item.priority}`} />
                <span className="intel-item-title">{item.title}</span>
                <div className="intel-badges">
                  {item.br3_improvement && <span className="build-this-badge">Build This</span>}
                  <span className={`source-badge ${item.source_type.toLowerCase()}`}>
                    {item.source_type}
                  </span>
                  <span className="category-badge">{item.category}</span>
                </div>
                <span className="intel-timestamp">{relativeTime(item.collected_at)}</span>
              </div>

              {item.summary && <div className="intel-item-summary">{item.summary}</div>}

              {expandedId === item.id && (
                <div className="intel-item-detail">
                  <div className="opus-synthesis">
                    <h4>Opus Analysis</h4>
                    {item.opus_synthesis ? (
                      <p>{item.opus_synthesis}</p>
                    ) : (
                      <p className="no-synthesis">Awaiting Opus review...</p>
                    )}
                  </div>

                  <div className="intel-item-actions">
                    {!item.read && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMarkRead(item.id);
                        }}
                      >
                        Mark Read
                      </button>
                    )}
                    <button
                      className="btn-dismiss"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDismiss(item.id);
                      }}
                    >
                      Dismiss
                    </button>
                    <button
                      className="btn-save"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSaveToLibrary(item.id);
                      }}
                    >
                      Save to Library
                    </button>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-source"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View Source
                    </a>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default IntelligenceTab;
