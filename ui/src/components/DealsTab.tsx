/**
 * DealsTab Component
 *
 * Universal price tracker starting with RTX 3090 GPUs for the Below upgrade.
 * Hunt management, deal feed with scoring, price history sparklines.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { dealsAPI } from '../services/api';
import type { DealItem, Hunt, PriceHistoryPoint, DealFilters } from '../types';
import './DealsTab.css';

const CATEGORY_OPTIONS = [
  { value: 'gpu', label: 'GPU' },
  { value: 'guitar', label: 'Guitar' },
  { value: 'lumber', label: 'Lumber' },
  { value: 'electronics', label: 'Electronics' },
  { value: 'food', label: 'Food' },
  { value: 'other', label: 'Other' },
];

const INTERVAL_OPTIONS = [
  { value: 15, label: '15 min' },
  { value: 30, label: '30 min' },
  { value: 60, label: '1 hr' },
  { value: 360, label: '6 hr' },
  { value: 1440, label: '24 hr' },
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

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

interface DealsTabProps {
  onAlertCount?: (count: number) => void;
}

interface NewHuntForm {
  name: string;
  category: string;
  keywords: string;
  target_price: string;
  check_interval_minutes: number;
  source_urls: string;
}

const EMPTY_HUNT_FORM: NewHuntForm = {
  name: '',
  category: 'gpu',
  keywords: '',
  target_price: '',
  check_interval_minutes: 15,
  source_urls: '',
};

export function DealsTab({ onAlertCount }: DealsTabProps) {
  const [deals, setDeals] = useState<DealItem[]>([]);
  const [hunts, setHunts] = useState<Hunt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedHuntId, setSelectedHuntId] = useState<number | null>(null);
  const [expandedDealId, setExpandedDealId] = useState<number | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistoryPoint[]>([]);
  const [priceHistoryDealId, setPriceHistoryDealId] = useState<number | null>(null);
  const [showAddHunt, setShowAddHunt] = useState(false);
  const [huntForm, setHuntForm] = useState<NewHuntForm>(EMPTY_HUNT_FORM);
  const [creating, setCreating] = useState(false);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadHunts = useCallback(async () => {
    try {
      const data = await dealsAPI.getHunts();
      setHunts(data.hunts);

      // Auto-create default GPU hunt if none exist
      if (data.hunts.length === 0) {
        try {
          await dealsAPI.createHunt({
            name: 'RTX 3090 FTW3 for Below Upgrade',
            category: 'gpu',
            keywords: 'EVGA RTX 3090 FTW3 Ultra 24GB -Ti',
            target_price: 900,
            check_interval_minutes: 15,
            source_urls: ['https://www.ebay.com/str/outworld'],
          });
          const refreshed = await dealsAPI.getHunts();
          setHunts(refreshed.hunts);
        } catch {
          // Silent — auto-create is best-effort
        }
      }
    } catch (err) {
      console.error('Failed to load hunts:', err);
    }
  }, []);

  const loadDeals = useCallback(async () => {
    try {
      const filters: DealFilters = { limit: 100 };
      if (selectedHuntId) filters.hunt_id = selectedHuntId;

      const data = await dealsAPI.getDealItems(filters);
      const sorted = [...data.items].sort((a, b) => {
        return (b.deal_score ?? 0) - (a.deal_score ?? 0);
      });
      setDeals(sorted);
      setError(null);

      // Count unread exceptional deals for alert badge
      const exceptionalUnread = sorted.filter(
        (d) => d.deal_score >= 80 && !d.read && !d.dismissed
      ).length;
      onAlertCount?.(exceptionalUnread);
    } catch (err) {
      setError('Failed to load deals. Is Lockwood online?');
      console.error('Deals load error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedHuntId, onAlertCount]);

  useEffect(() => {
    loadHunts();
  }, [loadHunts]);

  useEffect(() => {
    loadDeals();
    pollIntervalRef.current = setInterval(loadDeals, 30000);
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [loadDeals]);

  const handleCreateHunt = async () => {
    if (!huntForm.name || !huntForm.keywords) return;
    setCreating(true);
    try {
      const sourceUrls = huntForm.source_urls
        .split('\n')
        .map((u) => u.trim())
        .filter(Boolean);
      await dealsAPI.createHunt({
        name: huntForm.name,
        category: huntForm.category,
        keywords: huntForm.keywords,
        target_price: parseFloat(huntForm.target_price) || 0,
        check_interval_minutes: huntForm.check_interval_minutes,
        source_urls: sourceUrls,
      });
      setHuntForm(EMPTY_HUNT_FORM);
      setShowAddHunt(false);
      await loadHunts();
    } catch (err) {
      console.error('Failed to create hunt:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleArchiveHunt = async (id: number) => {
    try {
      await dealsAPI.archiveHunt(id);
      setHunts((prev) => prev.filter((h) => h.id !== id));
      if (selectedHuntId === id) setSelectedHuntId(null);
    } catch (err) {
      console.error('Archive hunt failed:', err);
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await dealsAPI.dismissDeal(id);
      setDeals((prev) => prev.map((d) => (d.id === id ? { ...d, dismissed: true } : d)));
    } catch (err) {
      console.error('Dismiss deal failed:', err);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await dealsAPI.markDealRead(id);
      setDeals((prev) => prev.map((d) => (d.id === id ? { ...d, read: true } : d)));
    } catch (err) {
      console.error('Mark read failed:', err);
    }
  };

  const handleShowPriceHistory = async (dealId: number) => {
    if (priceHistoryDealId === dealId) {
      setPriceHistoryDealId(null);
      setPriceHistory([]);
      return;
    }
    try {
      const data = await dealsAPI.getPriceHistory(dealId);
      setPriceHistory(data.history);
      setPriceHistoryDealId(dealId);
    } catch (err) {
      console.error('Price history failed:', err);
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedDealId((prev) => (prev === id ? null : id));
  };

  const getVerdictClass = (verdict: string): string => {
    switch (verdict) {
      case 'exceptional':
        return 'verdict-exceptional';
      case 'good':
        return 'verdict-good';
      case 'fair':
        return 'verdict-fair';
      default:
        return 'verdict-pass';
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    if (score >= 40) return '#0066cc';
    return '#9e9e9e';
  };

  const visibleDeals = deals.filter((d) => !d.dismissed);

  if (loading && deals.length === 0) {
    return (
      <div className="deals-tab">
        <div className="deals-loading">Loading deals feed...</div>
      </div>
    );
  }

  if (error && deals.length === 0) {
    return (
      <div className="deals-tab">
        <div className="deals-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="deals-tab">
      <h2>Deal Tracker</h2>

      {/* Hunt Management Panel */}
      <div className="hunts-panel">
        <div className="hunts-header">
          <h3>Active Hunts</h3>
          <button className="btn-add-hunt" onClick={() => setShowAddHunt(!showAddHunt)}>
            {showAddHunt ? 'Cancel' : '+ Add Hunt'}
          </button>
        </div>

        {/* Add Hunt Modal */}
        {showAddHunt && (
          <div className="add-hunt-form">
            <div className="form-row">
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={huntForm.name}
                  onChange={(e) => setHuntForm({ ...huntForm, name: e.target.value })}
                  placeholder="e.g. Fender Telecaster"
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <select
                  value={huntForm.category}
                  onChange={(e) => setHuntForm({ ...huntForm, category: e.target.value })}
                >
                  {CATEGORY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group flex-2">
                <label>Keywords</label>
                <input
                  type="text"
                  value={huntForm.keywords}
                  onChange={(e) => setHuntForm({ ...huntForm, keywords: e.target.value })}
                  placeholder="e.g. Fender Telecaster American -Squier"
                />
              </div>
              <div className="form-group">
                <label>Target Price</label>
                <input
                  type="number"
                  value={huntForm.target_price}
                  onChange={(e) => setHuntForm({ ...huntForm, target_price: e.target.value })}
                  placeholder="$"
                />
              </div>
              <div className="form-group">
                <label>Check Interval</label>
                <select
                  value={huntForm.check_interval_minutes}
                  onChange={(e) =>
                    setHuntForm({
                      ...huntForm,
                      check_interval_minutes: parseInt(e.target.value),
                    })
                  }
                >
                  {INTERVAL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group flex-2">
                <label>Source URLs (one per line, optional)</label>
                <textarea
                  value={huntForm.source_urls}
                  onChange={(e) => setHuntForm({ ...huntForm, source_urls: e.target.value })}
                  placeholder="https://www.ebay.com/str/..."
                  rows={2}
                />
              </div>
              <div className="form-group form-actions">
                <button
                  className="btn-create-hunt"
                  onClick={handleCreateHunt}
                  disabled={creating || !huntForm.name || !huntForm.keywords}
                >
                  {creating ? 'Creating...' : 'Create Hunt'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Hunt Cards */}
        <div className="hunts-grid">
          <div
            className={`hunt-card ${selectedHuntId === null ? 'selected' : ''}`}
            onClick={() => setSelectedHuntId(null)}
          >
            <div className="hunt-card-name">All Hunts</div>
            <div className="hunt-card-stat">{deals.filter((d) => !d.dismissed).length} deals</div>
          </div>
          {hunts.map((hunt) => (
            <div
              key={hunt.id}
              className={`hunt-card ${selectedHuntId === hunt.id ? 'selected' : ''}`}
              onClick={() => setSelectedHuntId(hunt.id)}
            >
              <div className="hunt-card-header">
                <span className="hunt-card-name">{hunt.name}</span>
                <button
                  className="btn-archive-hunt"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleArchiveHunt(hunt.id);
                  }}
                  title="Archive hunt"
                >
                  ×
                </button>
              </div>
              <div className="hunt-card-meta">
                <span className="hunt-category-badge">{hunt.category}</span>
                <span className="hunt-target">Target: {formatPrice(hunt.target_price)}</span>
              </div>
              <div className="hunt-card-stats">
                <span>{hunt.items_count ?? 0} items</span>
                {hunt.last_checked && (
                  <span className="hunt-last-checked">
                    Checked {relativeTime(hunt.last_checked)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Deal Feed */}
      {visibleDeals.length === 0 ? (
        <div className="deals-empty">
          No deals found
          <div className="deals-empty-hint">
            Deals will appear as changedetection.io and collectors find listings
          </div>
        </div>
      ) : (
        <div className="deals-list">
          {visibleDeals.map((deal) => (
            <div
              key={deal.id}
              className={`deal-card ${getVerdictClass(deal.verdict)}${deal.read ? ' read-deal' : ''}`}
              onClick={() => toggleExpand(deal.id)}
            >
              <div className="deal-card-header">
                <div className="deal-card-left">
                  <span className="deal-name">{deal.name}</span>
                  <div className="deal-meta">
                    <span className="deal-seller">
                      {deal.seller}
                      {deal.seller_rating > 0 && (
                        <span className="seller-rating"> ({deal.seller_rating.toFixed(1)}%)</span>
                      )}
                    </span>
                    <span className="deal-condition">{deal.condition}</span>
                    <span className="deal-timestamp">{relativeTime(deal.collected_at)}</span>
                  </div>
                </div>
                <div className="deal-card-right">
                  <span className="deal-price">{formatPrice(deal.price)}</span>
                  <span
                    className="deal-score-badge"
                    style={{ backgroundColor: getScoreColor(deal.deal_score) }}
                  >
                    {deal.deal_score}
                  </span>
                  <span className={`deal-verdict ${deal.verdict}`}>{deal.verdict}</span>
                </div>
              </div>

              {deal.opus_assessment && (
                <div className="deal-assessment-preview">
                  {deal.opus_assessment.slice(0, 120)}
                  {deal.opus_assessment.length > 120 ? '...' : ''}
                </div>
              )}

              {expandedDealId === deal.id && (
                <div className="deal-detail">
                  {deal.opus_assessment && (
                    <div className="deal-opus-section">
                      <h4>Opus Assessment</h4>
                      <p>{deal.opus_assessment}</p>
                    </div>
                  )}

                  {deal.attributes && Object.keys(deal.attributes).length > 0 && (
                    <div className="deal-attributes">
                      <h4>Attributes</h4>
                      <div className="attributes-grid">
                        {Object.entries(deal.attributes).map(([key, value]) => (
                          <div key={key} className="attribute-item">
                            <span className="attribute-key">{key}</span>
                            <span className="attribute-value">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Price History Sparkline */}
                  {priceHistoryDealId === deal.id && priceHistory.length > 0 && (
                    <div className="price-history-chart">
                      <h4>Price History</h4>
                      <ResponsiveContainer width="100%" height={120}>
                        <AreaChart
                          data={priceHistory.map((p) => ({
                            date: new Date(p.recorded_at).toLocaleDateString(),
                            price: p.price,
                          }))}
                        >
                          <defs>
                            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#0066cc" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#0066cc" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11, fill: '#999' }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Tooltip
                            contentStyle={{
                              background: '#0f1520',
                              border: 'none',
                              borderRadius: '6px',
                              color: '#e0e0e0',
                              fontSize: '13px',
                            }}
                            formatter={(value: number) => [formatPrice(value), 'Price']}
                          />
                          <Area
                            type="monotone"
                            dataKey="price"
                            stroke="#0066cc"
                            strokeWidth={2}
                            fill="url(#priceGradient)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <div className="deal-actions">
                    <button
                      className="btn-history"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleShowPriceHistory(deal.id);
                      }}
                    >
                      {priceHistoryDealId === deal.id ? 'Hide History' : 'Price History'}
                    </button>
                    {!deal.read && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMarkRead(deal.id);
                        }}
                      >
                        Mark Read
                      </button>
                    )}
                    <button
                      className="btn-dismiss"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDismiss(deal.id);
                      }}
                    >
                      Dismiss
                    </button>
                    <a
                      href={deal.listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-open-listing"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Open Listing
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

export default DealsTab;
