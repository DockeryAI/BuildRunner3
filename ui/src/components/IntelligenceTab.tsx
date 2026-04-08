import { useEffect, useState, useCallback } from 'react';
import { intelAPI } from '../services/api';
import type { IntelItem, IntelImprovement, IntelFilters } from '../types';
import './IntelligenceTab.css';

interface IntelligenceTabProps {
  onAlertCount?: (count: number) => void;
  onImprovementCount?: (count: number) => void;
}

export function IntelligenceTab({ onAlertCount, onImprovementCount }: IntelligenceTabProps) {
  const [items, setItems] = useState<IntelItem[]>([]);
  const [improvements, setImprovements] = useState<IntelImprovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [filters, setFilters] = useState<IntelFilters>({ limit: 50 });
  const [copyFeedback, setCopyFeedback] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [itemsRes, alertsRes, improvementsRes] = await Promise.all([
        intelAPI.getIntelItems(filters),
        intelAPI.getIntelAlerts(),
        intelAPI.getIntelImprovements('pending'),
      ]);
      setItems(itemsRes.items);
      setImprovements(improvementsRes.improvements);
      onAlertCount?.(alertsRes.critical_count + alertsRes.high_count);
      onImprovementCount?.(improvementsRes.count);
      setError(null);
    } catch (err) {
      setError('Failed to connect to Lockwood intelligence service');
      console.error('Intelligence load error:', err);
    } finally {
      setLoading(false);
    }
  }, [filters, onAlertCount, onImprovementCount]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleDismiss = async (id: number) => {
    await intelAPI.dismissIntelItem(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const handleMarkRead = async (id: number) => {
    await intelAPI.markIntelRead(id);
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read: true } : i)));
  };

  const handleSaveToLibrary = async (id: number) => {
    await intelAPI.saveToLibrary(id);
  };

  const handleCopySetlist = (improvementId: number, prompt: string) => {
    navigator.clipboard.writeText(`/setlist ${prompt}`);
    setCopyFeedback(improvementId);
    setTimeout(() => setCopyFeedback(null), 2000);
  };

  const handleImprovementStatus = async (id: number, status: string) => {
    await intelAPI.updateImprovementStatus(id, status);
    setImprovements((prev) => prev.filter((i) => i.id !== id));
  };

  const updateFilter = (key: keyof IntelFilters, value: string) => {
    setFilters((prev) => {
      const next = { ...prev };
      if (value === '' || value === 'all') {
        delete next[key];
      } else if (key === 'days' || key === 'limit') {
        (next as any)[key] = parseInt(value);
      } else {
        (next as any)[key] = value;
      }
      return next;
    });
  };

  const getPriorityClass = (priority: string) => {
    return `priority-${priority}`;
  };

  const getSourceBadgeClass = (sourceType: string) => {
    return `source-badge source-${sourceType.toLowerCase()}`;
  };

  const getCategoryLabel = (cat: string) => {
    const labels: Record<string, string> = {
      'api-change': 'API',
      'model-release': 'Model',
      'community-tool': 'Tool',
      'ecosystem-news': 'Ecosystem',
      'cluster-relevant': 'Cluster',
      'general-news': 'News',
    };
    return labels[cat] || cat;
  };

  const formatTime = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  if (loading && items.length === 0) {
    return <div className="intel-loading">Loading intelligence feed...</div>;
  }

  if (error && items.length === 0) {
    return (
      <div className="intel-error">
        <div className="intel-error-icon">!</div>
        <div>{error}</div>
        <div className="intel-error-hint">Is Lockwood online? Check cluster status.</div>
      </div>
    );
  }

  return (
    <div className="intelligence-tab">
      <div className="intel-header">
        <h2>Intelligence Feed</h2>
        <div className="intel-filter-bar">
          <select
            value={filters.source_type || 'all'}
            onChange={(e) => updateFilter('source_type', e.target.value)}
          >
            <option value="all">All Sources</option>
            <option value="Official">Official</option>
            <option value="Community">Community</option>
            <option value="Blog">Blog</option>
          </select>
          <select
            value={filters.category || 'all'}
            onChange={(e) => updateFilter('category', e.target.value)}
          >
            <option value="all">All Categories</option>
            <option value="api-change">API Changes</option>
            <option value="model-release">Model Releases</option>
            <option value="community-tool">Community Tools</option>
            <option value="ecosystem-news">Ecosystem</option>
            <option value="cluster-relevant">Cluster</option>
            <option value="general-news">General</option>
          </select>
          <select
            value={filters.priority || 'all'}
            onChange={(e) => updateFilter('priority', e.target.value)}
          >
            <option value="all">All Priority</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={filters.days?.toString() || 'all'}
            onChange={(e) => updateFilter('days', e.target.value)}
          >
            <option value="all">All Time</option>
            <option value="1">24h</option>
            <option value="7">7 days</option>
            <option value="30">30 days</option>
          </select>
        </div>
      </div>

      {improvements.length > 0 && (
        <div className="intel-improvements-section">
          <h3>BR3 Improvements ({improvements.length} pending)</h3>
          <div className="improvements-list">
            {improvements.map((imp) => (
              <div key={imp.id} className="improvement-card">
                <div className="improvement-header">
                  <span className="improvement-badge">Build This</span>
                  <span className={`complexity-badge complexity-${imp.complexity}`}>
                    {imp.complexity}
                  </span>
                  <span className="improvement-title">{imp.title}</span>
                </div>
                <div className="improvement-rationale">{imp.rationale}</div>
                {imp.overlap_action && (
                  <div className="improvement-overlap">
                    Overlap: <strong>{imp.overlap_action}</strong>
                    {imp.overlap_notes && ` — ${imp.overlap_notes}`}
                  </div>
                )}
                <div className="improvement-actions">
                  <button
                    className="btn-copy-setlist"
                    onClick={() => handleCopySetlist(imp.id, imp.setlist_prompt)}
                  >
                    {copyFeedback === imp.id ? 'Copied!' : 'Copy /setlist Command'}
                  </button>
                  <button
                    className="btn-plan"
                    onClick={() => handleImprovementStatus(imp.id, 'planned')}
                  >
                    Mark Planned
                  </button>
                  <button
                    className="btn-archive-imp"
                    onClick={() => handleImprovementStatus(imp.id, 'archived')}
                  >
                    Archive
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="intel-feed">
        {items.length === 0 ? (
          <div className="intel-empty">No intelligence items match your filters.</div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className={`intel-item ${getPriorityClass(item.priority)} ${item.read ? 'read' : ''}`}
              onClick={() => {
                setExpandedId(expandedId === item.id ? null : item.id);
                if (!item.read) handleMarkRead(item.id);
              }}
            >
              <div className="intel-item-row">
                <span className={`priority-dot priority-dot-${item.priority}`} />
                <span className="intel-item-title">{item.title}</span>
                <span className={getSourceBadgeClass(item.source_type)}>{item.source_type}</span>
                <span className="category-badge">{getCategoryLabel(item.category)}</span>
                {item.br3_improvement && <span className="br3-badge">BR3</span>}
                <span className="intel-time">{formatTime(item.collected_at)}</span>
              </div>
              {item.summary && <div className="intel-item-summary">{item.summary}</div>}

              {expandedId === item.id && (
                <div className="intel-item-expanded">
                  {item.opus_synthesis && (
                    <div className="opus-synthesis">
                      <div className="opus-label">Opus Analysis</div>
                      <div className="opus-content">{item.opus_synthesis}</div>
                    </div>
                  )}
                  <div className="intel-item-meta">
                    <span>Source: {item.source}</span>
                    <span>Score: {item.score}/10</span>
                  </div>
                  <div className="intel-item-actions">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-open"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Open Source
                    </a>
                    <button
                      className="btn-save"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSaveToLibrary(item.id);
                      }}
                    >
                      Save to Library
                    </button>
                    <button
                      className="btn-dismiss"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDismiss(item.id);
                      }}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default IntelligenceTab;
