"""Tests for Phase 1: Collection Infrastructure (Intelligence & Deals)"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def temp_intel_db():
    """Create a temp SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    with patch("core.cluster.intel_collector.INTEL_DB_PATH", path):
        yield path
    os.unlink(path)


class TestIntelSchema:
    """Schema creation and table verification."""

    def test_intel_items_table_exists(self, temp_intel_db):
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='intel_items'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_deal_items_table_exists(self, temp_intel_db):
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='deal_items'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_price_history_table_exists(self, temp_intel_db):
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_model_snapshots_table_exists(self, temp_intel_db):
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='model_snapshots'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_active_hunts_table_exists(self, temp_intel_db):
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='active_hunts'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestIntelItemCRUD:
    """Intel item create/read/update operations."""

    def test_create_intel_item(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item, get_intel_items
        item_id = create_intel_item(
            title="Claude 4 released",
            source="Anthropic Blog",
            url="https://anthropic.com/claude-4",
            source_type="official",
            category="model-release",
        )
        assert item_id is not None
        items = get_intel_items()
        assert len(items) == 1
        assert items[0]["title"] == "Claude 4 released"

    def test_duplicate_url_rejected(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item
        id1 = create_intel_item(title="Test", source="src", url="https://example.com/1")
        id2 = create_intel_item(title="Test 2", source="src", url="https://example.com/1")
        assert id1 is not None
        assert id2 is None  # Duplicate URL should return None

    def test_mark_read(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item, mark_intel_read, get_intel_items
        item_id = create_intel_item(title="Test", source="src")
        mark_intel_read(item_id)
        items = get_intel_items(read=True)
        assert len(items) == 1
        assert items[0]["read"] == 1

    def test_dismiss_item(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item, dismiss_intel_item, get_intel_items
        item_id = create_intel_item(title="Test", source="src")
        dismiss_intel_item(item_id)
        # Dismissed items excluded from default query
        items = get_intel_items()
        assert len(items) == 0

    def test_get_alerts(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item, get_intel_alerts, _get_intel_db
        id1 = create_intel_item(title="Critical thing", source="src")
        id2 = create_intel_item(title="High thing", source="src")
        # Manually set priority/scored since scoring is Phase 2
        conn = _get_intel_db()
        conn.execute("UPDATE intel_items SET priority='critical', scored=1 WHERE id=?", (id1,))
        conn.execute("UPDATE intel_items SET priority='high', scored=1 WHERE id=?", (id2,))
        conn.commit()
        conn.close()
        alerts = get_intel_alerts()
        assert alerts["critical_count"] == 1
        assert alerts["high_count"] == 1

    def test_filter_by_priority(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item, get_intel_items, _get_intel_db
        id1 = create_intel_item(title="Item 1", source="src")
        id2 = create_intel_item(title="Item 2", source="src")
        conn = _get_intel_db()
        conn.execute("UPDATE intel_items SET priority='critical' WHERE id=?", (id1,))
        conn.execute("UPDATE intel_items SET priority='low' WHERE id=?", (id2,))
        conn.commit()
        conn.close()
        items = get_intel_items(priority="critical")
        assert len(items) == 1
        assert items[0]["title"] == "Item 1"

    def test_filter_by_source_type(self, temp_intel_db):
        from core.cluster.intel_collector import create_intel_item, get_intel_items
        create_intel_item(title="Official", source="Anthropic", source_type="official")
        create_intel_item(title="Community", source="Reddit", source_type="community")
        items = get_intel_items(source_type="official")
        assert len(items) == 1
        assert items[0]["title"] == "Official"


class TestDealItemCRUD:
    """Deal item create/read operations."""

    def test_create_deal_with_price_history(self, temp_intel_db):
        from core.cluster.intel_collector import (
            create_hunt, create_deal_item, get_deal_items, get_price_history
        )
        hunt_id = create_hunt(name="GPU Hunt", category="gpu", target_price=900)
        deal_id = create_deal_item(
            hunt_id=hunt_id, name="EVGA RTX 3090 FTW3",
            price=849.99, condition="Used", seller="outworld",
        )
        assert deal_id is not None

        deals = get_deal_items(hunt_id=hunt_id)
        assert len(deals) == 1
        assert deals[0]["price"] == 849.99

        history = get_price_history(deal_id)
        assert len(history) == 1
        assert history[0]["price"] == 849.99

    def test_mark_deal_read(self, temp_intel_db):
        from core.cluster.intel_collector import (
            create_hunt, create_deal_item, mark_deal_read, _get_intel_db
        )
        hunt_id = create_hunt(name="Test", category="other")
        deal_id = create_deal_item(hunt_id=hunt_id, name="Test Deal", price=100)
        mark_deal_read(deal_id)
        conn = _get_intel_db()
        row = conn.execute("SELECT read FROM deal_items WHERE id=?", (deal_id,)).fetchone()
        conn.close()
        assert row["read"] == 1

    def test_dismiss_deal(self, temp_intel_db):
        from core.cluster.intel_collector import (
            create_hunt, create_deal_item, dismiss_deal_item, get_deal_items
        )
        hunt_id = create_hunt(name="Test", category="other")
        create_deal_item(hunt_id=hunt_id, name="Test Deal", price=100)
        deals = get_deal_items()
        assert len(deals) == 1
        dismiss_deal_item(deals[0]["id"])
        deals = get_deal_items()
        assert len(deals) == 0


class TestHuntCRUD:
    """Hunt create/read/archive operations."""

    def test_create_hunt(self, temp_intel_db):
        from core.cluster.intel_collector import create_hunt, get_hunts
        hunt_id = create_hunt(
            name="RTX 3090 FTW3",
            category="gpu",
            keywords="EVGA RTX 3090 FTW3 -Ti",
            target_price=900,
            source_urls=["https://www.ebay.com/str/outworld"],
        )
        assert hunt_id is not None
        hunts = get_hunts()
        assert len(hunts) == 1
        assert hunts[0]["name"] == "RTX 3090 FTW3"
        assert hunts[0]["target_price"] == 900

    def test_archive_hunt(self, temp_intel_db):
        from core.cluster.intel_collector import create_hunt, archive_hunt, get_hunts
        hunt_id = create_hunt(name="Old Hunt", category="other")
        archive_hunt(hunt_id)
        hunts = get_hunts(active_only=True)
        assert len(hunts) == 0
        hunts = get_hunts(active_only=False)
        assert len(hunts) == 1


class TestModelSnapshots:
    """Model snapshot storage and comparison."""

    def test_save_and_retrieve_snapshot(self, temp_intel_db):
        from core.cluster.intel_collector import save_model_snapshot, get_last_model_snapshot
        models = {"claude-3-opus": {"id": "claude-3-opus"}, "claude-3-sonnet": {"id": "claude-3-sonnet"}}
        snap_id = save_model_snapshot(models, "Initial snapshot: 2 models")
        assert snap_id is not None
        last = get_last_model_snapshot()
        assert last is not None
        assert len(last["snapshot"]) == 2
        assert last["diff_summary"] == "Initial snapshot: 2 models"


class TestWebhookParsers:
    """Webhook payload parsing."""

    def test_parse_miniflux_webhook(self, temp_intel_db):
        from core.cluster.intel_collector import parse_miniflux_webhook
        payload = {
            "entries": [{
                "title": "Claude Code 1.5 Released",
                "url": "https://github.com/anthropics/claude-code/releases/v1.5",
                "content": "New features...",
                "feed": {"title": "Claude Code Releases"},
            }]
        }
        items = parse_miniflux_webhook(payload)
        assert len(items) == 1
        assert items[0]["title"] == "Claude Code 1.5 Released"

    def test_parse_miniflux_single_entry(self, temp_intel_db):
        from core.cluster.intel_collector import parse_miniflux_webhook
        payload = {
            "entry": {
                "title": "Single entry",
                "url": "https://example.com/single",
                "content": "Content",
                "feed": {"title": "Test Feed"},
            }
        }
        items = parse_miniflux_webhook(payload)
        assert len(items) == 1

    def test_parse_newreleases_webhook(self, temp_intel_db):
        from core.cluster.intel_collector import parse_newreleases_webhook
        payload = {
            "project": "anthropic-ai/sdk",
            "version": "2.1.0",
            "provider": "github",
            "url": "https://github.com/anthropic-ai/sdk/releases/v2.1.0",
        }
        items = parse_newreleases_webhook(payload)
        assert len(items) == 1
        assert "2.1.0" in items[0]["title"]

    def test_parse_f5bot_webhook(self, temp_intel_db):
        from core.cluster.intel_collector import parse_f5bot_webhook
        payload = {
            "alerts": [{
                "title": "Claude Code tip: use /compact",
                "url": "https://reddit.com/r/ClaudeAI/post123",
                "keyword": "Claude Code",
                "source": "reddit",
                "content": "Found a great tip...",
            }]
        }
        items = parse_f5bot_webhook(payload)
        assert len(items) == 1

    def test_parse_changedetection_single(self, temp_intel_db):
        from core.cluster.intel_collector import parse_changedetection_webhook, create_hunt
        hunt_id = create_hunt(
            name="GPU Hunt", category="gpu",
            source_urls=["https://www.ebay.com/str/outworld"],
        )
        payload = {
            "watch_url": "https://www.ebay.com/str/outworld",
            "title": "EVGA RTX 3090 FTW3 Ultra 24GB",
            "price": "$849.99",
            "seller": "outworld",
            "listing_url": "https://ebay.com/itm/123",
        }
        items = parse_changedetection_webhook(payload)
        assert len(items) == 1
        assert items[0]["price"] == 849.99

    def test_parse_changedetection_no_matching_hunt(self, temp_intel_db):
        from core.cluster.intel_collector import parse_changedetection_webhook
        payload = {
            "watch_url": "https://unknown-store.com",
            "title": "Some Item",
            "price": "$50",
        }
        items = parse_changedetection_webhook(payload)
        assert len(items) == 0


class TestSourceTypeClassification:
    """Source type auto-classification."""

    def test_github_is_official(self, temp_intel_db):
        from core.cluster.intel_collector import _classify_source_type
        assert _classify_source_type("GitHub Releases", "https://github.com") == "official"

    def test_reddit_is_community(self, temp_intel_db):
        from core.cluster.intel_collector import _classify_source_type
        assert _classify_source_type("reddit", "") == "community"

    def test_unknown_is_community(self, temp_intel_db):
        from core.cluster.intel_collector import _classify_source_type
        assert _classify_source_type("some-random-source", "") == "community"


class TestAPIEndpoints:
    """FastAPI endpoint integration tests."""

    @pytest.fixture
    def client(self, temp_intel_db):
        from fastapi.testclient import TestClient
        from core.cluster.node_intelligence import app
        return TestClient(app)

    def test_get_intel_items_empty(self, client, temp_intel_db):
        resp = client.get("/api/intel/items")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["items"] == []

    def test_get_intel_alerts(self, client, temp_intel_db):
        resp = client.get("/api/intel/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "critical_count" in data
        assert "high_count" in data

    def test_webhook_miniflux(self, client, temp_intel_db):
        payload = {
            "entries": [{
                "title": "Test Entry",
                "url": "https://example.com/test",
                "content": "Content",
                "feed": {"title": "Test Feed"},
            }]
        }
        resp = client.post("/api/intel/webhook/miniflux", json=payload)
        assert resp.status_code == 200
        assert resp.json()["items_created"] == 1

    def test_webhook_newreleases(self, client, temp_intel_db):
        payload = {"project": "test-project", "version": "1.0.0", "provider": "npm"}
        resp = client.post("/api/intel/webhook/newreleases", json=payload)
        assert resp.status_code == 200
        assert resp.json()["items_created"] == 1

    def test_webhook_f5bot(self, client, temp_intel_db):
        payload = {"alerts": [{"title": "Mention", "keyword": "test", "source": "reddit"}]}
        resp = client.post("/api/intel/webhook/f5bot", json=payload)
        assert resp.status_code == 200

    def test_create_and_get_hunts(self, client, temp_intel_db):
        resp = client.post("/api/deals/hunts", json={
            "name": "Test Hunt", "category": "gpu", "target_price": 500,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

        resp = client.get("/api/deals/hunts")
        assert resp.status_code == 200
        assert len(resp.json()["hunts"]) == 1

    def test_archive_hunt(self, client, temp_intel_db):
        resp = client.post("/api/deals/hunts", json={"name": "Archive Me", "category": "other"})
        hunt_id = resp.json()["id"]
        resp = client.post(f"/api/deals/hunts/{hunt_id}/archive")
        assert resp.status_code == 200

    def test_get_deals_empty(self, client, temp_intel_db):
        resp = client.get("/api/deals/items")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_mark_read_and_dismiss(self, client, temp_intel_db):
        # Create via webhook
        payload = {
            "entries": [{"title": "Read Test", "url": "https://example.com/read-test",
                         "content": "x", "feed": {"title": "Feed"}}]
        }
        resp = client.post("/api/intel/webhook/miniflux", json=payload)
        items = resp.json()["items"]
        item_id = items[0]["id"]

        resp = client.post(f"/api/intel/items/{item_id}/read")
        assert resp.status_code == 200

        resp = client.post(f"/api/intel/items/{item_id}/dismiss")
        assert resp.status_code == 200

    def test_health_endpoint(self, client, temp_intel_db):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["role"] == "intelligence"

    def test_price_history_endpoint(self, client, temp_intel_db):
        resp = client.get("/api/deals/price-history/999")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_changedetection_webhook(self, client, temp_intel_db):
        # Create a hunt first
        client.post("/api/deals/hunts", json={
            "name": "GPU", "category": "gpu",
            "source_urls": ["https://www.ebay.com/str/outworld"],
        })
        payload = {
            "watch_url": "https://www.ebay.com/str/outworld",
            "title": "RTX 3090",
            "price": "$800",
            "seller": "outworld",
        }
        resp = client.post("/api/deals/webhook/changedetection", json=payload)
        assert resp.status_code == 200
