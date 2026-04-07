-- BR3 Intelligence & Deals — SQLite Schema
-- Database: ~/.lockwood/intel.db
-- Used by: node_intelligence.py, intel_collector.py

-- Intelligence items from all sources (RSS, webhooks, pollers)
CREATE TABLE IF NOT EXISTS intel_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    raw_content TEXT,
    source_type TEXT NOT NULL DEFAULT 'community',  -- official/community/blog
    category TEXT,  -- api-change/model-release/community-tool/ecosystem-news/cluster-relevant/general-news
    collected_at TEXT NOT NULL DEFAULT (datetime('now')),
    scored INTEGER NOT NULL DEFAULT 0,
    score INTEGER,
    priority TEXT,  -- critical/high/medium/low
    summary TEXT,
    opus_synthesis TEXT,
    br3_improvement INTEGER NOT NULL DEFAULT 0,
    read INTEGER NOT NULL DEFAULT 0,
    dismissed INTEGER NOT NULL DEFAULT 0,
    opus_reviewed INTEGER NOT NULL DEFAULT 0,
    needs_opus_review INTEGER NOT NULL DEFAULT 0,
    url_hash TEXT  -- for deduplication
);

CREATE INDEX IF NOT EXISTS idx_intel_priority ON intel_items(priority);
CREATE INDEX IF NOT EXISTS idx_intel_category ON intel_items(category);
CREATE INDEX IF NOT EXISTS idx_intel_source_type ON intel_items(source_type);
CREATE INDEX IF NOT EXISTS idx_intel_scored ON intel_items(scored);
CREATE INDEX IF NOT EXISTS idx_intel_read ON intel_items(read);
CREATE INDEX IF NOT EXISTS idx_intel_url_hash ON intel_items(url_hash);
CREATE INDEX IF NOT EXISTS idx_intel_collected ON intel_items(collected_at);

-- Deal items from price tracking sources
CREATE TABLE IF NOT EXISTS deal_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hunt_id INTEGER,
    name TEXT NOT NULL,
    category TEXT,
    attributes TEXT,  -- JSON
    source_url TEXT,
    price REAL,
    condition TEXT,
    seller TEXT,
    seller_rating REAL,
    deal_score INTEGER,
    verdict TEXT,  -- exceptional/good/fair/pass
    below_assessment TEXT,  -- one-line assessment from Below scoring
    opus_assessment TEXT,
    listing_url TEXT,
    collected_at TEXT NOT NULL DEFAULT (datetime('now')),
    read INTEGER NOT NULL DEFAULT 0,
    dismissed INTEGER NOT NULL DEFAULT 0,
    opus_reviewed INTEGER NOT NULL DEFAULT 0,
    needs_opus_review INTEGER NOT NULL DEFAULT 0,
    verified INTEGER NOT NULL DEFAULT 0,
    link_status INTEGER,
    in_stock INTEGER,  -- 1=yes, 0=no, NULL=unknown
    last_checked TEXT,
    listing_url_hash TEXT,  -- SHA256[:16] of listing_url for dedup
    FOREIGN KEY (hunt_id) REFERENCES active_hunts(id)
);

CREATE INDEX IF NOT EXISTS idx_deal_hunt ON deal_items(hunt_id);
CREATE INDEX IF NOT EXISTS idx_deal_score ON deal_items(deal_score);
CREATE INDEX IF NOT EXISTS idx_deal_read ON deal_items(read);
CREATE INDEX IF NOT EXISTS idx_deal_verified ON deal_items(verified);
CREATE INDEX IF NOT EXISTS idx_deal_in_stock ON deal_items(in_stock);
CREATE INDEX IF NOT EXISTS idx_deal_url_hash ON deal_items(listing_url_hash);

-- Price history for tracking deals over time + market price collection
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_item_id INTEGER,  -- nullable for market-only entries (no deal item)
    hunt_id INTEGER,       -- which hunt this price belongs to
    price REAL NOT NULL,
    source TEXT,
    title TEXT,            -- listing title for market context
    url TEXT,              -- listing URL
    is_sold INTEGER DEFAULT 0,  -- 1=completed/sold transaction, 0=active listing
    condition TEXT,         -- New/Used/Refurbished etc
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deal_item_id) REFERENCES deal_items(id),
    FOREIGN KEY (hunt_id) REFERENCES active_hunts(id)
);

CREATE INDEX IF NOT EXISTS idx_price_deal ON price_history(deal_item_id);
CREATE INDEX IF NOT EXISTS idx_price_hunt ON price_history(hunt_id);
CREATE INDEX IF NOT EXISTS idx_price_sold ON price_history(is_sold);
CREATE INDEX IF NOT EXISTS idx_price_recorded ON price_history(recorded_at);

-- Model snapshots for Anthropic API model tracking
CREATE TABLE IF NOT EXISTS model_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot TEXT NOT NULL,  -- JSON
    diff_summary TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Active hunts for deal tracking
CREATE TABLE IF NOT EXISTS active_hunts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    keywords TEXT,
    target_price REAL,
    check_interval_minutes INTEGER NOT NULL DEFAULT 60,
    source_urls TEXT,  -- JSON array
    requirements TEXT,  -- JSON: filters, pair_rules, notes (see hunt_sourcer.py)
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_hunt_active ON active_hunts(active);

-- Intel improvements — BR3 actionable improvements detected by Opus review
CREATE TABLE IF NOT EXISTS intel_improvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    rationale TEXT,
    complexity TEXT NOT NULL DEFAULT 'medium',  -- simple/medium/complex
    setlist_prompt TEXT NOT NULL,
    affected_files TEXT,  -- JSON array
    source_intel_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/planned/built/archived
    build_spec_name TEXT,  -- linked BUILD spec when marked as planned
    overlap_action TEXT,  -- adopt/adapt/ignore (when overlapping existing BR3 functionality)
    overlap_notes TEXT,
    type TEXT NOT NULL DEFAULT 'fix',  -- fix/upgrade/new_capability/new_skill/research
    auto_acted INTEGER NOT NULL DEFAULT 0,  -- 1 if auto-act ran on this improvement
    auto_act_log TEXT,  -- log output from auto-act execution
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (source_intel_id) REFERENCES intel_items(id)
);

CREATE INDEX IF NOT EXISTS idx_improvements_status ON intel_improvements(status);
CREATE INDEX IF NOT EXISTS idx_improvements_source ON intel_improvements(source_intel_id);

-- Package versions for tracking npm/PyPI updates
CREATE TABLE IF NOT EXISTS package_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name TEXT NOT NULL,
    registry TEXT NOT NULL,  -- npm/pypi
    version TEXT NOT NULL,
    checked_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(package_name, registry)
);
