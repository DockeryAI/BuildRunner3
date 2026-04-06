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
    opus_assessment TEXT,
    listing_url TEXT,
    collected_at TEXT NOT NULL DEFAULT (datetime('now')),
    read INTEGER NOT NULL DEFAULT 0,
    dismissed INTEGER NOT NULL DEFAULT 0,
    opus_reviewed INTEGER NOT NULL DEFAULT 0,
    needs_opus_review INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (hunt_id) REFERENCES active_hunts(id)
);

CREATE INDEX IF NOT EXISTS idx_deal_hunt ON deal_items(hunt_id);
CREATE INDEX IF NOT EXISTS idx_deal_score ON deal_items(deal_score);
CREATE INDEX IF NOT EXISTS idx_deal_read ON deal_items(read);

-- Price history for tracking deals over time
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_item_id INTEGER NOT NULL,
    price REAL NOT NULL,
    source TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deal_item_id) REFERENCES deal_items(id)
);

CREATE INDEX IF NOT EXISTS idx_price_deal ON price_history(deal_item_id);

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
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_hunt_active ON active_hunts(active);

-- Package versions for tracking npm/PyPI updates
CREATE TABLE IF NOT EXISTS package_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name TEXT NOT NULL,
    registry TEXT NOT NULL,  -- npm/pypi
    version TEXT NOT NULL,
    checked_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(package_name, registry)
);
