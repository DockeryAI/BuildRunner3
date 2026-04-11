import { useEffect, useState, useCallback, useMemo } from 'react';
import { dealsAPI } from '../services/api';
import type { DealItem, Hunt, PriceHistoryPoint } from '../types';
import './DealsTab.css';

interface DealsTabProps {
  onAlertCount?: (count: number) => void;
}

interface HuntGroup {
  hunt: Hunt;
  deals: DealItem[];
  bestDeal: DealItem | null;
  inRangeCount: number;
}

export function DealsTab({ onAlertCount }: DealsTabProps) {
  const [hunts, setHunts] = useState<Hunt[]>([]);
  const [deals, setDeals] = useState<DealItem[]>([]);
  const [selectedHunt, setSelectedHunt] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedDeal, setExpandedDeal] = useState<number | null>(null);
  const [expandedHunts, setExpandedHunts] = useState<Set<number>>(new Set());
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

  const loadData = useCallback(async () => {
    try {
      const [huntsRes, dealsRes] = await Promise.all([
        dealsAPI.getHunts(),
        dealsAPI.getDealItems(selectedHunt ? { hunt_id: selectedHunt } : { limit: 50 }),
      ]);
      setHunts(huntsRes.hunts);
      setDeals(dealsRes.items);

      const exceptional = dealsRes.items.filter((d) => d.deal_score >= 80 && !d.read).length;
      onAlertCount?.(exceptional);
      setError(null);
    } catch (err) {
      setError('Failed to connect to Lockwood deals service');
      console.error('Deals load error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedHunt, onAlertCount]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
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

  const toggleHuntAccordion = (huntId: number) => {
    setExpandedHunts((prev) => {
      const next = new Set(prev);
      if (next.has(huntId)) next.delete(huntId);
      else next.add(huntId);
      return next;
    });
  };

  const isInRange = (deal: DealItem): boolean => {
    return deal.attributes?.in_range === true;
  };

  // Group deals by hunt, sorted by price within each group
  const huntGroups: HuntGroup[] = useMemo(() => {
    const huntMap = new Map<number, Hunt>();
    hunts.forEach((h) => huntMap.set(h.id, h));

    const grouped = new Map<number, DealItem[]>();
    const filteredDeals = selectedHunt ? deals.filter((d) => d.hunt_id === selectedHunt) : deals;

    filteredDeals.forEach((deal) => {
      const list = grouped.get(deal.hunt_id) || [];
      list.push(deal);
      grouped.set(deal.hunt_id, list);
    });

    const groups: HuntGroup[] = [];
    grouped.forEach((huntDeals, huntId) => {
      const hunt = huntMap.get(huntId);
      if (!hunt) return;
      const sorted = [...huntDeals].sort((a, b) => (a.price || Infinity) - (b.price || Infinity));
      groups.push({
        hunt,
        deals: sorted,
        bestDeal: sorted[0] || null,
        inRangeCount: sorted.filter(isInRange).length,
      });
    });

    // Hunts with in-range deals first, then by best price
    groups.sort((a, b) => {
      if (a.inRangeCount > 0 && b.inRangeCount === 0) return -1;
      if (b.inRangeCount > 0 && a.inRangeCount === 0) return 1;
      return (a.bestDeal?.price || Infinity) - (b.bestDeal?.price || Infinity);
    });

    return groups;
  }, [hunts, deals, selectedHunt]);

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

                  {/* Best deal — compact single row */}
                  {bestDeal && (
                    <BestDealRow
                      deal={bestDeal}
                      inRange={isInRange(bestDeal)}
                      targetPrice={hunt.target_price}
                      getVerdictClass={getVerdictClass}
                      getScoreColor={getScoreColor}
                      formatTime={formatTime}
                      formatPrice={formatPrice}
                    />
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
}

function BestDealRow({
  deal,
  inRange,
  targetPrice,
  getVerdictClass,
  getScoreColor,
  formatTime,
  formatPrice,
}: BestDealRowProps) {
  const priceDelta = targetPrice ? deal.price - targetPrice : 0;
  const isVerified = deal.in_stock && deal.seller_verified;

  return (
    <a
      href={deal.listing_url}
      target="_blank"
      rel="noopener noreferrer"
      className={`best-deal-row ${inRange ? 'best-deal-in-range blink-highlight' : ''}`}
    >
      <div className="bdr-score" style={{ backgroundColor: getScoreColor(deal.deal_score) }}>
        {deal.deal_score}
      </div>
      <span className="bdr-rank">#1</span>
      <span className="bdr-name">{deal.name}</span>
      <div className="bdr-status">
        {deal.in_stock === true && (
          <span className="status-badge status-in-stock" title="In Stock">
            IN STOCK
          </span>
        )}
        {deal.in_stock === false && (
          <span className="status-badge status-out-of-stock" title="Out of Stock">
            SOLD
          </span>
        )}
        {deal.seller_verified && (
          <span className="status-badge status-verified" title="Seller Verified">
            VERIFIED
          </span>
        )}
        {!isVerified && deal.in_stock !== false && (
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
  getVerdictClass,
  getScoreColor,
  formatTime,
  formatPrice,
}: DealCardProps) {
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
            {deal.in_stock === true && (
              <span className="status-badge status-in-stock">IN STOCK</span>
            )}
            {deal.in_stock === false && (
              <span className="status-badge status-out-of-stock">SOLD</span>
            )}
            {deal.seller_verified && <span className="status-badge status-verified">VERIFIED</span>}
            {!deal.seller_verified && deal.in_stock !== false && (
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
