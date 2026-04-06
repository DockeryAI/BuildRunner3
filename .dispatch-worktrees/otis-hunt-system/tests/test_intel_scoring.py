"""
Tests for intel_scoring.py — Below Scoring Pipeline (Phase 2)
"""

import json
import math
import sqlite3
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# --- Helpers ---

def _setup_test_db():
    """Create temp DB with schema for testing."""
    import tempfile
    tmp = tempfile.mktemp(suffix=".db")
    os.environ["INTEL_DB"] = tmp
    # Reload module to pick up new path
    import importlib
    import core.cluster.intel_collector as ic
    importlib.reload(ic)
    conn = ic._get_intel_db()
    return conn


# --- Intel Scoring Tests ---

class TestIntelScoring:
    """Tests for score_intel_items function."""

    def test_build_intel_scoring_prompt(self):
        """Scoring prompt includes title, source, and raw_content."""
        from core.cluster.intel_scoring import _build_intel_prompt
        item = {
            "id": 1,
            "title": "New Anthropic model: claude-opus-4-6-20260320",
            "source": "Anthropic Models API",
            "raw_content": '{"id": "claude-opus-4-6-20260320"}',
        }
        prompt = _build_intel_prompt(item)
        assert "claude-opus-4-6-20260320" in prompt
        assert "relevance" in prompt.lower()
        assert "urgency" in prompt.lower()
        assert "actionability" in prompt.lower()
        assert "priority" in prompt.lower()
        assert "summary" in prompt.lower()

    def test_parse_intel_score_valid(self):
        """Parse valid JSON scoring response from Below."""
        from core.cluster.intel_scoring import _parse_intel_score
        response = json.dumps({
            "relevance": 8,
            "urgency": 6,
            "actionability": 7,
            "category": "model-release",
            "priority": "high",
            "summary": "New Claude model released with improved capabilities."
        })
        result = _parse_intel_score(response)
        assert result is not None
        assert result["score"] == 7  # average of 8+6+7
        assert result["priority"] == "high"
        assert result["category"] == "model-release"
        assert result["summary"] == "New Claude model released with improved capabilities."

    def test_parse_intel_score_malformed(self):
        """Malformed JSON returns None (triggers needs_opus_review)."""
        from core.cluster.intel_scoring import _parse_intel_score
        result = _parse_intel_score("not json at all")
        assert result is None

    def test_parse_intel_score_missing_fields(self):
        """Partial JSON with missing required fields returns None."""
        from core.cluster.intel_scoring import _parse_intel_score
        response = json.dumps({"relevance": 5})
        result = _parse_intel_score(response)
        assert result is None

    def test_parse_intel_score_out_of_range(self):
        """Scores outside 1-10 range returns None."""
        from core.cluster.intel_scoring import _parse_intel_score
        response = json.dumps({
            "relevance": 15,
            "urgency": -1,
            "actionability": 5,
            "category": "general-news",
            "priority": "low",
            "summary": "Something happened."
        })
        result = _parse_intel_score(response)
        assert result is None


# --- Deal Scoring Tests ---

class TestDealScoring:
    """Tests for score_deal_items function."""

    def test_build_deal_scoring_prompt(self):
        """Deal scoring prompt includes item details and hunt target price."""
        from core.cluster.intel_scoring import _build_deal_prompt
        item = {
            "id": 1,
            "name": "EVGA RTX 3090 FTW3 Ultra",
            "price": 750.0,
            "condition": "Used - Good",
            "seller": "outworld_systems",
            "seller_rating": 99.5,
        }
        hunt = {
            "target_price": 900.0,
            "category": "gpu",
        }
        prompt = _build_deal_prompt(item, hunt)
        assert "750" in prompt
        assert "900" in prompt
        assert "FTW3" in prompt
        assert "condition" in prompt.lower()

    def test_parse_deal_score_valid(self):
        """Parse valid deal scoring JSON response."""
        from core.cluster.intel_scoring import _parse_deal_score
        response = json.dumps({
            "score": 87,
            "verdict": "exceptional",
            "assessment": "Great price for FTW3, well below target. Reputable seller."
        })
        result = _parse_deal_score(response)
        assert result is not None
        assert result["score"] == 87
        assert result["verdict"] == "exceptional"
        assert "FTW3" in result["assessment"]

    def test_parse_deal_score_malformed(self):
        """Malformed deal JSON returns None."""
        from core.cluster.intel_scoring import _parse_deal_score
        result = _parse_deal_score("random text")
        assert result is None

    def test_parse_deal_score_invalid_verdict(self):
        """Invalid verdict value returns None."""
        from core.cluster.intel_scoring import _parse_deal_score
        response = json.dumps({
            "score": 50,
            "verdict": "amazing",  # not in valid set
            "assessment": "Test."
        })
        result = _parse_deal_score(response)
        assert result is None

    def test_parse_deal_score_out_of_range(self):
        """Score outside 0-100 returns None."""
        from core.cluster.intel_scoring import _parse_deal_score
        response = json.dumps({
            "score": 150,
            "verdict": "exceptional",
            "assessment": "Test."
        })
        result = _parse_deal_score(response)
        assert result is None


# --- Deduplication Tests ---

class TestDeduplication:
    """Tests for deduplication logic."""

    def test_cosine_similarity_identical(self):
        """Identical vectors should have similarity 1.0."""
        from core.cluster.intel_scoring import _cosine_similarity
        v = [1.0, 0.0, 0.5]
        assert abs(_cosine_similarity(v, v) - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors should have similarity 0.0."""
        from core.cluster.intel_scoring import _cosine_similarity
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert abs(_cosine_similarity(v1, v2)) < 0.001

    def test_cosine_similarity_threshold(self):
        """Similar but not identical vectors above 0.92 threshold."""
        from core.cluster.intel_scoring import _cosine_similarity
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.98, 0.1, 0.05]
        sim = _cosine_similarity(v1, v2)
        # Should be high but below 1
        assert sim > 0.9


# --- Confidence Flagging Tests ---

class TestConfidenceFlagging:
    """Tests for confidence flagging on parse failures."""

    def test_flag_intel_item_for_opus_review(self):
        """When scoring fails, item should be flagged needs_opus_review."""
        from core.cluster.intel_scoring import _flag_needs_opus_review
        conn = _setup_test_db()
        # Insert test item
        conn.execute(
            "INSERT INTO intel_items (title, source) VALUES (?, ?)",
            ("Test item", "test")
        )
        conn.commit()
        item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        _flag_needs_opus_review(item_id, "intel")
        row = conn.execute(
            "SELECT needs_opus_review FROM intel_items WHERE id = ?", (item_id,)
        ).fetchone()
        assert row[0] == 1
        conn.close()


# --- Discord Alert Tests ---

class TestDiscordAlert:
    """Tests for exceptional deal Discord webhook."""

    def test_build_discord_payload(self):
        """Discord webhook payload includes deal details."""
        from core.cluster.intel_scoring import _build_discord_alert_payload
        deal = {
            "id": 42,
            "name": "EVGA RTX 3090 FTW3",
            "price": 750.0,
            "deal_score": 92,
            "verdict": "exceptional",
            "listing_url": "https://ebay.com/itm/123",
        }
        payload = _build_discord_alert_payload(deal)
        assert "embeds" in payload
        assert "FTW3" in json.dumps(payload)
        assert "92" in json.dumps(payload)

    @pytest.mark.asyncio
    async def test_discord_alert_no_webhook_url(self):
        """No Discord URL configured — should silently skip."""
        from core.cluster.intel_scoring import _send_discord_alert
        # Should not raise
        with patch.dict(os.environ, {"DISCORD_DEAL_WEBHOOK_URL": ""}):
            await _send_discord_alert({"name": "test", "deal_score": 90})


# --- Below Offline Fallback ---

class TestBelowFallback:
    """Tests for Below offline handling."""

    @pytest.mark.asyncio
    async def test_below_unreachable_returns_none(self):
        """When Below is offline, scoring should return None (not raise)."""
        from core.cluster.intel_scoring import _call_below_chat
        with patch("core.cluster.intel_scoring.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.side_effect = Exception("Connection refused")
            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.Timeout = MagicMock()
            result = await _call_below_chat("test prompt")
            assert result is None
