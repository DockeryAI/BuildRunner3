import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { dealsAPI } from '../services/api';
import type { DealItem, Hunt, PriceHistoryPoint } from '../types';
import './DealsTab.css';

interface DealsTabProps {
  onAlertCount?: (count: number) => void;
}

// Persist accordion state across remounts (parent polling causes re-renders)
const persistedExpandedHunts = new Set<number>();

interface HuntGroup {
  hunt: Hunt;
  deals: DealItem[];
  bestDeal: DealItem | null;
  inRangeCount: number;
}

type StatusTab = 'hunting' | 'bought' | 'delivered';

// Derive status from purchased + delivery_status fields
function getDealStatus(deal: DealItem): StatusTab {
  if (deal.delivery_status === 'delivered') return 'delivered';
  if (deal.purchased === 1) return 'bought';
  return 'hunting';
}

export function DealsTab({ onAlertCount }: DealsTabProps) {
  const [hunts, setHunts] = useState<Hunt[]>([]);
  const [archivedHunts, setArchivedHunts] = useState<Hunt[]>([]);
  const [deals, setDeals] = useState<DealItem[]>([]);
  const [selectedHunt, setSelectedHunt] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<StatusTab>('hunting');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedDeal, setExpandedDeal] = useState<number | null>(null);
  const [expandedHunts, setExpandedHunts] = useState<Set<number>>(
    () => new Set(persistedExpandedHunts)
  );
  const [priceHistory, setPriceHistory] = useState<PriceHistoryPoint[]>([]);
  const [showNewHunt, setShowNewHunt] = useState(false);
  const [newHunt, setNewHunt] = useState({
    name: '',
    category: 'gpu',
    keywords: '',
    target_price: 0,
    check_interval_minutes: 60,
    source_urls: [] as string[],
  });

  // Use ref to avoid onAlertCount in useCallback deps (prevents cascading re-renders)
  const onAlertCountRef = useRef(onAlertCount);
  onAlertCountRef.current = onAlertCount;
  const lastAlertCountRef = useRef<number>(-1);

  const loadData = useCallback(async () => {
    try {
      const [huntsRes, archivedRes, dealsRes] = await Promise.all([
        dealsAPI.getHunts(),
        dealsAPI.getArchivedHunts(),
        dealsAPI.getDealItems({
          ...(selectedHunt ? { hunt_id: selectedHunt } : { limit: 100 }),
          ready_only: false,
        }),
      ]);
      setHunts(huntsRes.hunts);
      setArchivedHunts(archivedRes.hunts);
      setDeals(dealsRes.items);

      const exceptional = dealsRes.items.filter((d) => d.deal_score >= 80 && !d.read).length;
      // Only call if count changed to prevent parent re-renders
      if (exceptional !== lastAlertCountRef.current) {
        lastAlertCountRef.current = exceptional;
        onAlertCountRef.current?.(exceptional);
      }
      setError(null);
    } catch (err) {
      setError('Failed to connect to Lockwood deals service');
      console.error('Deals load error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedHunt]);

  // Polling with visibility handling - pause when tab hidden, refresh when visible
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (interval) clearInterval(interval);
      loadData();
      interval = setInterval(loadData, 30000);
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        // Tab became visible - refresh data immediately and restart polling
        startPolling();
      } else {
        // Tab hidden - pause polling to prevent stale state accumulation
        if (interval) {
          clearInterval(interval);
          interval = null;
        }
      }
    };

    // Start polling if tab is visible
    if (document.visibilityState === 'visible') {
      startPolling();
    }

    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      if (interval) clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [loadData]);

  const handleSelectHunt = (huntId: number | null) => {
    setSelectedHunt(huntId);
    setExpandedDeal(null);
  };

  const handleDismiss = async (id: number) => {
    await dealsAPI.dismissDeal(id);
    setDeals((prev) => prev.filter((d) => d.id !== id));
  };

  const handleMarkRead = async (id: number) => {
    await dealsAPI.markDealRead(id);
    setDeals((prev) => prev.map((d) => (d.id === id ? { ...d, read: true } : d)));
  };

  const handleShowHistory = async (dealId: number) => {
    if (expandedDeal === dealId) {
      setExpandedDeal(null);
      return;
    }
    setExpandedDeal(dealId);
    try {
      const res = await dealsAPI.getPriceHistory(dealId);
      setPriceHistory(res.history);
    } catch {
      setPriceHistory([]);
    }
  };

  const handleCreateHunt = async () => {
    try {
      await dealsAPI.createHunt(newHunt);
      setShowNewHunt(false);
      setNewHunt({
        name: '',
        category: 'gpu',
        keywords: '',
        target_price: 0,
        check_interval_minutes: 60,
        source_urls: [],
      });
      loadData();
    } catch (err) {
      console.error('Failed to create hunt:', err);
    }
  };

  const handleArchiveHunt = async (id: number) => {
    await dealsAPI.archiveHunt(id);
    if (selectedHunt === id) setSelectedHunt(null);
    loadData();
  };

  const handleStatusChange = async (dealId: number, newStatus: StatusTab) => {
    // Determine API fields based on status
    const updates: { purchased?: number; delivery_status?: string } = {};
    if (newStatus === 'hunting') {
      updates.purchased = 0;
      updates.delivery_status = 'none';
    } else if (newStatus === 'bought') {
      updates.purchased = 1;
      updates.delivery_status = 'none';
    } else if (newStatus === 'delivered') {
      updates.purchased = 1;
      updates.delivery_status = 'delivered';
    }
    await dealsAPI.updateDeal(dealId, updates);
    // Update local state immediately for responsiveness
    setDeals((prev) =>
      prev.map((d) =>
        d.id === dealId
          ? {
              ...d,
              purchased: updates.purchased ?? d.purchased,
              delivery_status: (updates.delivery_status ??
                d.delivery_status) as DealItem['delivery_status'],
            }
          : d
      )
    );
  };

  const toggleHuntAccordion = (huntId: number) => {
    setExpandedHunts((prev) => {
      const next = new Set(prev);
      if (next.has(huntId)) {
        next.delete(huntId);
        persistedExpandedHunts.delete(huntId);
      } else {
        next.add(huntId);
        persistedExpandedHunts.add(huntId);
      }
      return next;
    });
  };

  const isInRange = (deal: DealItem): boolean => {
    return deal.attributes?.in_range === true;
  };

  // Count deals by status for tab badges
  const statusCounts = useMemo(() => {
    const counts = { hunting: 0, bought: 0, delivered: 0 };
    deals.forEach((d) => {
      counts[getDealStatus(d)]++;
    });
    return counts;
  }, [deals]);

  // Group deals by hunt, sorted by price within each group
  // Filter: by active tab + in-stock + verified sellers (for hunting tab)
  // STABILITY FIX: Include ALL hunts even with 0 matching deals to prevent accordion state loss
  const huntGroups: HuntGroup[] = useMemo(() => {
    const grouped = new Map<number, DealItem[]>();

    // Filter deals by hunt selection and active tab
    let filteredDeals = selectedHunt ? deals.filter((d) => d.hunt_id === selectedHunt) : deals;

    // Filter by status tab
    filteredDeals = filteredDeals.filter((d) => getDealStatus(d) === activeTab);

    // For hunting tab, also filter to in-stock + verified sellers
    if (activeTab === 'hunting') {
      filteredDeals = filteredDeals.filter(
        (d) =>
          (d.in_stock === true || d.in_stock === 1) &&
          (d.seller_verified === true || d.seller_verified === 1)
      );
    }

    filteredDeals.forEach((deal) => {
      const list = grouped.get(deal.hunt_id) || [];
      list.push(deal);
      grouped.set(deal.hunt_id, list);
    });

    // Include ALL hunts (or selected hunt), even those with 0 matching deals
    // This prevents accordion state from being lost when deals are filtered out
    // For Bought/Delivered tabs, also include archived hunts since those deals still exist
    const allHunts = activeTab === 'hunting' ? hunts : [...hunts, ...archivedHunts];
    const relevantHunts = selectedHunt ? allHunts.filter((h) => h.id === selectedHunt) : allHunts;

    const groups: HuntGroup[] = relevantHunts.map((hunt) => {
      const huntDeals = grouped.get(hunt.id) || [];
      // Sort by deal_score descending (best deals first), then by price ascending as tiebreaker
      const sorted = [...huntDeals].sort((a, b) => {
        const scoreDiff = (b.deal_score || 0) - (a.deal_score || 0);
        if (scoreDiff !== 0) return scoreDiff;
        return (a.price || Infinity) - (b.price || Infinity);
      });
      return {
        hunt,
        deals: sorted,
        bestDeal: sorted[0] || null,
        inRangeCount: sorted.filter(isInRange).length,
      };
    });

    // Stable sort: hunts with in-range deals first, then by best price, then by hunt.id for determinism
    groups.sort((a, b) => {
      if (a.inRangeCount > 0 && b.inRangeCount === 0) return -1;
      if (b.inRangeCount > 0 && a.inRangeCount === 0) return 1;
      const priceCompare = (a.bestDeal?.price || Infinity) - (b.bestDeal?.price || Infinity);
      if (priceCompare !== 0) return priceCompare;
      return a.hunt.id - b.hunt.id; // Stable secondary sort by ID
    });

    return groups;
  }, [hunts, archivedHunts, deals, selectedHunt, activeTab]);

  const getVerdictClass = (verdict: string) => {
    const classes: Record<string, string> = {
      exceptional: 'verdict-exceptional',
      good: 'verdict-good',
      fair: 'verdict-fair',
      pass: 'verdict-pass',
    };
    return classes[verdict] || 'verdict-pass';
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    if (score >= 40) return '#0066cc';
    return '#888';
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

  const formatPrice = (price: number) => {
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  if (loading && deals.length === 0) {
    return <div className="deals-loading">Loading deals...</div>;
  }

  if (error && deals.length === 0) {
    return (
      <div className="deals-error">
        <div className="deals-error-icon">!</div>
        <div>{error}</div>
        <div className="deals-error-hint">Is Lockwood online? Check cluster status.</div>
      </div>
    );
  }

  return (
    <div className="deals-tab">
      {/* Hunt Management */}
      <div className="hunts-panel">
        <div className="hunts-header">
          <h2>Hunts</h2>
          <button className="btn-new-hunt" onClick={() => setShowNewHunt(!showNewHunt)}>
            {showNewHunt ? 'Cancel' : '+ New Hunt'}
          </button>
        </div>

        {showNewHunt && (
          <div className="new-hunt-form">
            <div className="form-row">
              <input
                type="text"
                placeholder="Hunt name"
                value={newHunt.name}
                onChange={(e) => setNewHunt((prev) => ({ ...prev, name: e.target.value }))}
              />
              <select
                value={newHunt.category}
                onChange={(e) => setNewHunt((prev) => ({ ...prev, category: e.target.value }))}
              >
                <option value="gpu">GPU</option>
                <option value="guitar">Guitar</option>
                <option value="lumber">Lumber</option>
                <option value="electronics">Electronics</option>
                <option value="food">Food</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="form-row">
              <input
                type="text"
                placeholder="Keywords (e.g. EVGA RTX 3090 FTW3 -Ti)"
                value={newHunt.keywords}
                onChange={(e) => setNewHunt((prev) => ({ ...prev, keywords: e.target.value }))}
              />
            </div>
            <div className="form-row">
              <input
                type="number"
                placeholder="Target price"
                value={newHunt.target_price || ''}
                onChange={(e) =>
                  setNewHunt((prev) => ({
                    ...prev,
                    target_price: parseFloat(e.target.value) || 0,
                  }))
                }
              />
              <select
                value={newHunt.check_interval_minutes}
                onChange={(e) =>
                  setNewHunt((prev) => ({
                    ...prev,
                    check_interval_minutes: parseInt(e.target.value),
                  }))
                }
              >
                <option value="15">Every 15 min</option>
                <option value="30">Every 30 min</option>
                <option value="60">Every hour</option>
                <option value="360">Every 6 hours</option>
                <option value="1440">Every 24 hours</option>
              </select>
            </div>
            <button className="btn-create-hunt" onClick={handleCreateHunt}>
              Create Hunt
            </button>
          </div>
        )}

        <div className="hunts-list">
          <button
            className={`hunt-card ${selectedHunt === null ? 'selected' : ''}`}
            onClick={() => handleSelectHunt(null)}
          >
            <div className="hunt-name">All Hunts</div>
            <div className="hunt-stat">{deals.length} items</div>
          </button>
          {hunts.map((hunt) => (
            <button
              key={hunt.id}
              className={`hunt-card ${selectedHunt === hunt.id ? 'selected' : ''}`}
              onClick={() => handleSelectHunt(hunt.id)}
            >
              <div className="hunt-card-top">
                <span className="hunt-name">{hunt.name}</span>
                <span className="hunt-category">{hunt.category}</span>
              </div>
              <div className="hunt-card-bottom">
                <span className="hunt-stat">Target: {formatPrice(hunt.target_price)}</span>
                <span className="hunt-stat">{hunt.items_count ?? 0} items</span>
                {hunt.last_checked && (
                  <span className="hunt-stat">Checked {formatTime(hunt.last_checked)}</span>
                )}
              </div>
              <button
                className="btn-archive-hunt"
                onClick={(e) => {
                  e.stopPropagation();
                  handleArchiveHunt(hunt.id);
                }}
              >
                Archive
              </button>
            </button>
          ))}
        </div>
      </div>

      {/* Deal Feed — grouped by hunt, best price + accordion */}
      <div className="deals-feed">
        <h3>
          {selectedHunt ? hunts.find((h) => h.id === selectedHunt)?.name || 'Deals' : 'All Hunts'}
          <span className="deals-count">
            ({deals.length} items across {huntGroups.length} hunts)
          </span>
        </h3>

        {/* Status tabs */}
        <div className="status-tabs">
          <button
            className={`status-tab ${activeTab === 'hunting' ? 'active' : ''}`}
            onClick={() => setActiveTab('hunting')}
          >
            Hunting <span className="tab-count">{statusCounts.hunting}</span>
          </button>
          <button
            className={`status-tab ${activeTab === 'bought' ? 'active' : ''}`}
            onClick={() => setActiveTab('bought')}
          >
            Bought <span className="tab-count">{statusCounts.bought}</span>
          </button>
          <button
            className={`status-tab ${activeTab === 'delivered' ? 'active' : ''}`}
            onClick={() => setActiveTab('delivered')}
          >
            Delivered <span className="tab-count">{statusCounts.delivered}</span>
          </button>
        </div>

        {huntGroups.length === 0 ? (
          <div className="deals-empty">
            No deals found.
            {hunts.length === 0 && ' Create a hunt to start tracking.'}
          </div>
        ) : (
          <div className="hunt-groups">
            {huntGroups.map(({ hunt, deals: huntDeals, bestDeal, inRangeCount }) => {
              const isExpanded = expandedHunts.has(hunt.id);
              const restDeals = huntDeals.slice(1, 11); // Top 10 after best

              return (
                <div
                  key={hunt.id}
                  className={`hunt-group ${inRangeCount > 0 ? 'has-in-range' : ''}`}
                >
                  {/* Hunt header */}
                  <div className="hunt-group-header">
                    <div className="hunt-group-title">
                      <span className="hunt-group-name">{hunt.name}</span>
                      <span className="hunt-group-target">
                        Target: {formatPrice(hunt.target_price)}
                      </span>
                    </div>
                    <div className="hunt-group-stats">
                      {inRangeCount > 0 && (
                        <span className="in-range-badge">{inRangeCount} in range</span>
                      )}
                      <span className="hunt-group-count">{huntDeals.length} items</span>
                    </div>
                  </div>

                  {/* Best deal — compact single row, or empty state */}
                  {bestDeal ? (
                    <BestDealRow
                      deal={bestDeal}
                      inRange={isInRange(bestDeal)}
                      targetPrice={hunt.target_price}
                      getVerdictClass={getVerdictClass}
                      getScoreColor={getScoreColor}
                      formatTime={formatTime}
                      formatPrice={formatPrice}
                      onStatusChange={handleStatusChange}
                    />
                  ) : (
                    <div className="hunt-empty-state">No verified in-stock deals available</div>
                  )}

                  {/* Accordion for remaining deals */}
                  {restDeals.length > 0 && (
                    <>
                      <button
                        className={`accordion-toggle ${isExpanded ? 'expanded' : ''}`}
                        onClick={() => toggleHuntAccordion(hunt.id)}
                      >
                        <span className="accordion-chevron">
                          {isExpanded ? '\u25B2' : '\u25BC'}
                        </span>
                        <span>{isExpanded ? 'Hide' : `Show ${restDeals.length} more`}</span>
                        <span className="accordion-price-range">
                          {formatPrice(restDeals[0].price)} —{' '}
                          {formatPrice(restDeals[restDeals.length - 1].price)}
                        </span>
                      </button>
                      {isExpanded && (
                        <div className="accordion-deals">
                          {restDeals.map((deal) => (
                            <DealCard
                              key={deal.id}
                              deal={deal}
                              isBest={false}
                              inRange={isInRange(deal)}
                              targetPrice={hunt.target_price}
                              expandedDeal={expandedDeal}
                              priceHistory={priceHistory}
                              onShowHistory={handleShowHistory}
                              onDismiss={handleDismiss}
                              onMarkRead={handleMarkRead}
                              onStatusChange={handleStatusChange}
                              getVerdictClass={getVerdictClass}
                              getScoreColor={getScoreColor}
                              formatTime={formatTime}
                              formatPrice={formatPrice}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// --- BestDealRow sub-component (compact single row) ---

interface BestDealRowProps {
  deal: DealItem;
  inRange: boolean;
  targetPrice: number;
  getVerdictClass: (v: string) => string;
  getScoreColor: (s: number) => string;
  formatTime: (ts: string) => string;
  formatPrice: (p: number) => string;
  onStatusChange: (dealId: number, status: StatusTab) => void;
}

function BestDealRow({
  deal,
  inRange,
  targetPrice,
  getVerdictClass,
  getScoreColor,
  formatTime,
  formatPrice,
  onStatusChange,
}: BestDealRowProps) {
  const priceDelta = targetPrice ? deal.price - targetPrice : 0;
  const isVerified = deal.in_stock && deal.seller_verified;
  const currentStatus = getDealStatus(deal);

  return (
    <div className={`best-deal-row ${inRange ? 'best-deal-in-range blink-highlight' : ''}`}>
      <a href={deal.listing_url} target="_blank" rel="noopener noreferrer" className="bdr-link">
        <div className="bdr-score" style={{ backgroundColor: getScoreColor(deal.deal_score) }}>
          {deal.deal_score}
        </div>
        <span className="bdr-rank">#1</span>
        <span className="bdr-name">{deal.name}</span>
        <div className="bdr-status">
          {!!deal.in_stock && (
            <span className="status-badge status-in-stock" title="In Stock">
              IN STOCK
            </span>
          )}
          {!deal.in_stock && deal.in_stock !== null ? (
            <span className="status-badge status-out-of-stock" title="Out of Stock">
              SOLD
            </span>
          ) : null}
          {!!deal.seller_verified && (
            <span className="status-badge status-verified" title="Seller Verified">
              VERIFIED
            </span>
          )}
          {!isVerified && !!deal.in_stock && (
            <span className="status-badge status-unverified" title="Not yet verified">
              UNVERIFIED
            </span>
          )}
        </div>
        <span className="bdr-seller">{deal.seller}</span>
        <span className={`bdr-verdict ${getVerdictClass(deal.verdict)}`}>{deal.verdict}</span>
        <span className="bdr-time">{formatTime(deal.collected_at)}</span>
        <div className="bdr-price-block">
          <span className={`bdr-price ${inRange ? 'price-in-range' : ''}`}>
            {formatPrice(deal.price)}
          </span>
          {targetPrice > 0 && (
            <span className={`bdr-delta ${priceDelta <= 0 ? 'delta-good' : 'delta-over'}`}>
              {priceDelta <= 0 ? '' : '+'}
              {formatPrice(Math.abs(priceDelta))} {priceDelta <= 0 ? 'under' : 'over'}
            </span>
          )}
        </div>
      </a>
      <select
        className="status-dropdown"
        value={currentStatus}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => onStatusChange(deal.id, e.target.value as StatusTab)}
      >
        <option value="hunting">Hunting</option>
        <option value="bought">Bought</option>
        <option value="delivered">Delivered</option>
      </select>
    </div>
  );
}

// --- DealCard sub-component ---

interface DealCardProps {
  deal: DealItem;
  isBest: boolean;
  inRange: boolean;
  targetPrice: number;
  expandedDeal: number | null;
  priceHistory: PriceHistoryPoint[];
  onShowHistory: (id: number) => void;
  onDismiss: (id: number) => void;
  onMarkRead: (id: number) => void;
  onStatusChange: (dealId: number, status: StatusTab) => void;
  getVerdictClass: (v: string) => string;
  getScoreColor: (s: number) => string;
  formatTime: (ts: string) => string;
  formatPrice: (p: number) => string;
}

function DealCard({
  deal,
  isBest,
  inRange,
  targetPrice,
  expandedDeal,
  priceHistory,
  onShowHistory,
  onDismiss,
  onMarkRead,
  onStatusChange,
  getVerdictClass,
  getScoreColor,
  formatTime,
  formatPrice,
}: DealCardProps) {
  const currentStatus = getDealStatus(deal);
  const priceDelta = targetPrice ? deal.price - targetPrice : 0;
  const pricePct = targetPrice ? ((deal.price / targetPrice) * 100).toFixed(0) : null;

  return (
    <div
      className={[
        'deal-card',
        getVerdictClass(deal.verdict),
        deal.read ? 'read' : '',
        isBest ? 'deal-best' : '',
        inRange ? 'deal-in-range' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="deal-card-header">
        <div className="deal-score" style={{ backgroundColor: getScoreColor(deal.deal_score) }}>
          {deal.deal_score}
        </div>
        <div className="deal-info">
          <div className="deal-name">
            {isBest && <span className="best-price-tag">#1</span>}
            {deal.name}
          </div>
          <div className="deal-meta">
            <span className="deal-seller">
              {deal.seller}
              {deal.seller_rating > 0 && (
                <span className="seller-rating"> ({deal.seller_rating}%)</span>
              )}
            </span>
            <span className="deal-condition">{deal.condition}</span>
            <span className="deal-time">{formatTime(deal.collected_at)}</span>
          </div>
          <div className="deal-status-badges">
            {!!deal.in_stock && <span className="status-badge status-in-stock">IN STOCK</span>}
            {(deal.in_stock === false || deal.in_stock === 0) && (
              <span className="status-badge status-out-of-stock">SOLD</span>
            )}
            {!!deal.seller_verified && (
              <span className="status-badge status-verified">VERIFIED</span>
            )}
            {!deal.seller_verified && !!deal.in_stock && (
              <span className="status-badge status-unverified">UNVERIFIED</span>
            )}
          </div>
        </div>
        <div className="deal-price-block">
          <div className={`deal-price ${inRange ? 'price-in-range' : ''}`}>
            {formatPrice(deal.price)}
          </div>
          {targetPrice > 0 && (
            <div className={`deal-price-delta ${priceDelta <= 0 ? 'delta-good' : 'delta-over'}`}>
              {priceDelta <= 0 ? '' : '+'}
              {formatPrice(Math.abs(priceDelta))} {priceDelta <= 0 ? 'under' : 'over'}
              {pricePct && <span className="delta-pct"> ({pricePct}%)</span>}
            </div>
          )}
        </div>
      </div>

      {inRange && <div className="in-range-highlight">IN TARGET RANGE</div>}

      <div className="deal-verdict-row">
        <span className={`verdict-badge ${getVerdictClass(deal.verdict)}`}>{deal.verdict}</span>
        {deal.attributes?.price_rank && (
          <span className="rank-badge">#{deal.attributes.price_rank} cheapest</span>
        )}
      </div>

      {deal.opus_assessment && (
        <div className="deal-opus">
          <span className="opus-tag">Opus</span> {deal.opus_assessment}
        </div>
      )}

      <div className="deal-actions">
        <select
          className="status-dropdown"
          value={currentStatus}
          onChange={(e) => onStatusChange(deal.id, e.target.value as StatusTab)}
        >
          <option value="hunting">Hunting</option>
          <option value="bought">Bought</option>
          <option value="delivered">Delivered</option>
        </select>
        <a
          href={deal.listing_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-listing"
        >
          Open Listing
        </a>
        <button className="btn-history" onClick={() => onShowHistory(deal.id)}>
          {expandedDeal === deal.id ? 'Hide History' : 'History'}
        </button>
        <button className="btn-deal-dismiss" onClick={() => onDismiss(deal.id)}>
          Dismiss
        </button>
        {!deal.read && (
          <button className="btn-deal-read" onClick={() => onMarkRead(deal.id)}>
            Mark Read
          </button>
        )}
      </div>

      {expandedDeal === deal.id && priceHistory.length > 0 && (
        <div className="price-history-section">
          <div className="price-history-label">Price History</div>
          <div className="price-history-chart">
            {priceHistory.map((point, idx) => {
              const max = Math.max(...priceHistory.map((p) => p.price));
              const min = Math.min(...priceHistory.map((p) => p.price));
              const range = max - min || 1;
              const height = ((point.price - min) / range) * 60 + 20;
              return (
                <div
                  key={idx}
                  className="price-bar"
                  style={{ height: `${height}px` }}
                  title={`${formatPrice(point.price)} — ${new Date(point.recorded_at).toLocaleDateString()}`}
                />
              );
            })}
          </div>
          <div className="price-history-range">
            <span>{formatPrice(Math.min(...priceHistory.map((p) => p.price)))}</span>
            <span>{formatPrice(Math.max(...priceHistory.map((p) => p.price)))}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default DealsTab;
