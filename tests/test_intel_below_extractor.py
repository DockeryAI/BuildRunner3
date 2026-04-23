"""
tests/test_intel_below_extractor.py

Unit and snapshot regression tests for core.cluster.scripts.intel_below_extractor.
All Below API calls are mocked — no real network access.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.cluster.scripts.intel_below_extractor import (
    INTEL_ITEM_SCHEMA,
    CATEGORIZE_SCHEMA,
    extract_intel_items,
    categorize_intel_items,
    _below_chat,
)

SNAPSHOT_FILE = Path(__file__).parent / "fixtures" / "intel_snapshot.jsonl"


# ---------------------------------------------------------------------------
# _below_chat
# ---------------------------------------------------------------------------


class TestBelowChat:
    def test_returns_none_when_flag_off(self):
        import core.cluster.scripts.intel_below_extractor as mod
        orig = mod._BELOW_INTEL_ENABLED
        mod._BELOW_INTEL_ENABLED = False
        try:
            result = _below_chat(INTEL_ITEM_SCHEMA, [{"role": "user", "content": "test"}])
            assert result is None
        finally:
            mod._BELOW_INTEL_ENABLED = orig

    def test_returns_none_on_connection_error(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("offline")):
            result = _below_chat(INTEL_ITEM_SCHEMA, [{"role": "user", "content": "test"}])
        assert result is None

    def test_returns_none_on_timeout(self):
        import socket
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
            result = _below_chat(INTEL_ITEM_SCHEMA, [{"role": "user", "content": "test"}])
        assert result is None

    def test_parses_valid_response(self):
        """Valid JSON response from Below should be returned as a dict."""
        mock_content = json.dumps({"items": []})
        mock_response_data = json.dumps({
            "message": {"content": mock_content}
        }).encode()

        class _MockResp:
            def read(self): return mock_response_data
            def __enter__(self): return self
            def __exit__(self, *a): pass

        with patch("urllib.request.urlopen", return_value=_MockResp()):
            result = _below_chat(INTEL_ITEM_SCHEMA, [{"role": "user", "content": "x"}])
        assert result == {"items": []}


# ---------------------------------------------------------------------------
# extract_intel_items
# ---------------------------------------------------------------------------


class TestExtractIntelItems:
    def _mock_below(self, items: list[dict]):
        """Return a context manager that patches _below_chat to return items."""
        import core.cluster.scripts.intel_below_extractor as mod
        return patch.object(mod, "_below_chat", return_value={"items": items})

    def test_returns_empty_on_offline(self):
        import core.cluster.scripts.intel_below_extractor as mod
        with patch.object(mod, "_below_chat", return_value=None):
            result = extract_intel_items("some text")
        assert result == []

    def test_returns_relevant_items_only(self):
        items = [
            {"title": "Real finding", "source": "anthropic.com", "url": "https://example.com",
             "summary": "New Claude model", "source_type": "official", "category": "model-release",
             "priority": "high", "relevant": True},
            {"title": "Spam", "source": "spam.com", "url": "https://spam.com",
             "summary": "buy now", "source_type": "blog", "category": "general-news",
             "priority": "low", "relevant": False},
        ]
        with self._mock_below(items):
            result = extract_intel_items("some text")
        assert len(result) == 1
        assert result[0]["title"] == "Real finding"

    def test_returns_all_when_all_relevant(self):
        items = [
            {"title": f"Item {i}", "source": "example.com", "url": f"https://example.com/{i}",
             "summary": "Summary", "source_type": "official", "category": "api-change",
             "priority": "medium", "relevant": True}
            for i in range(5)
        ]
        with self._mock_below(items):
            result = extract_intel_items("text")
        assert len(result) == 5

    def test_truncates_text_to_8000_chars(self):
        """Very large input must be truncated before sending to Below."""
        large_text = "x" * 20000
        captured = []

        import core.cluster.scripts.intel_below_extractor as mod
        def _fake_chat(schema, messages, **kw):
            captured.append(messages)
            return {"items": []}

        with patch.object(mod, "_below_chat", side_effect=_fake_chat):
            extract_intel_items(large_text)

        # The user message content must not exceed 8000 chars of the raw text
        user_msg = next(m for m in captured[0] if m["role"] == "user")
        assert len(user_msg["content"]) < 9000  # some overhead allowed for prompt wrapper

    def test_rollback_flag_returns_empty(self):
        import core.cluster.scripts.intel_below_extractor as mod
        orig = mod._BELOW_INTEL_ENABLED
        mod._BELOW_INTEL_ENABLED = False
        try:
            result = extract_intel_items("some text about Claude models")
        finally:
            mod._BELOW_INTEL_ENABLED = orig
        assert result == []


# ---------------------------------------------------------------------------
# categorize_intel_items
# ---------------------------------------------------------------------------


class TestCategorizeIntelItems:
    def _mock_below(self, classified: list[dict]):
        import core.cluster.scripts.intel_below_extractor as mod
        return patch.object(mod, "_below_chat", return_value={"classified": classified})

    def test_returns_empty_for_empty_input(self):
        result = categorize_intel_items([])
        assert result == []

    def test_returns_empty_on_offline(self):
        import core.cluster.scripts.intel_below_extractor as mod
        with patch.object(mod, "_below_chat", return_value=None):
            result = categorize_intel_items([{"id": 1, "title": "foo", "summary": "bar"}])
        assert result == []

    def test_classifies_items(self):
        classified = [
            {"id": 1, "category": "model-release", "priority": "high", "source_type": "official"},
            {"id": 2, "category": "security", "priority": "critical", "source_type": "official"},
        ]
        with self._mock_below(classified):
            result = categorize_intel_items([
                {"id": 1, "title": "New model", "summary": "Claude 4 released"},
                {"id": 2, "title": "CVE", "summary": "RCE in npm package"},
            ])
        assert len(result) == 2
        assert result[0]["category"] == "model-release"
        assert result[1]["priority"] == "critical"

    def test_caps_at_50_items(self):
        """Must not send more than 50 items to Below."""
        items = [{"id": i, "title": f"Item {i}", "summary": "x"} for i in range(100)]
        captured_messages = []

        import core.cluster.scripts.intel_below_extractor as mod
        def _fake_chat(schema, messages, **kw):
            captured_messages.extend(messages)
            return {"classified": []}

        with patch.object(mod, "_below_chat", side_effect=_fake_chat):
            categorize_intel_items(items)

        # The user message should not list more than 50 items
        user_msg = next(m for m in captured_messages if m["role"] == "user")
        # Count "id=" occurrences
        id_count = user_msg["content"].count("id=")
        assert id_count <= 50


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_intel_item_schema_has_required_fields(self):
        item_schema = INTEL_ITEM_SCHEMA["properties"]["items"]["items"]
        required = item_schema["required"]
        for field in ("title", "source", "url", "summary", "category", "priority", "relevant"):
            assert field in required, f"{field} missing from intel item schema"

    def test_categorize_schema_has_required_fields(self):
        item_schema = CATEGORIZE_SCHEMA["properties"]["classified"]["items"]
        required = item_schema["required"]
        for field in ("id", "category", "priority", "source_type"):
            assert field in required

    def test_valid_categories_in_schema(self):
        category_enum = INTEL_ITEM_SCHEMA["properties"]["items"]["items"]["properties"]["category"]["enum"]
        assert "model-release" in category_enum
        assert "security" in category_enum
        assert "api-change" in category_enum

    def test_valid_priorities_in_schema(self):
        priority_enum = INTEL_ITEM_SCHEMA["properties"]["items"]["items"]["properties"]["priority"]["enum"]
        assert "critical" in priority_enum
        assert "high" in priority_enum
        assert "low" in priority_enum


# ---------------------------------------------------------------------------
# Snapshot regression
# ---------------------------------------------------------------------------


class TestSnapshotRegression:
    """
    Validate schema shape of extracted items against fixture snapshots.
    Below is mocked to return plausible data — this tests the extraction
    schema contract, not Below's accuracy.
    """

    def _load_snapshots(self):
        if not SNAPSHOT_FILE.exists():
            return []
        return [json.loads(l) for l in SNAPSHOT_FILE.read_text().splitlines() if l.strip()]

    def test_snapshot_items_have_required_fields(self):
        """Extracted items must always include all required schema fields."""
        snapshots = self._load_snapshots()
        if not snapshots:
            pytest.skip("No snapshot fixtures found")

        for snap in snapshots:
            if snap.get("expected_items_min", 0) == 0:
                continue  # Skip irrelevant text snapshots

            # Mock Below to return a plausible item for this snapshot
            mock_item = {
                "title": "Mock title",
                "source": "example.com",
                "url": "https://example.com/article",
                "summary": snap["raw_text"][:200],
                "source_type": "official",
                "category": snap.get("expected_category") or "ecosystem-news",
                "priority": (snap.get("expected_priority_in") or ["medium"])[0],
                "relevant": True,
            }

            import core.cluster.scripts.intel_below_extractor as mod
            with patch.object(mod, "_below_chat", return_value={"items": [mock_item]}):
                result = extract_intel_items(snap["raw_text"], context=snap.get("context", "tech news"))

            assert len(result) >= snap["expected_items_min"], (
                f"Snapshot {snap['id']}: expected ≥{snap['expected_items_min']} items, got {len(result)}"
            )
            for item in result:
                for field in ("title", "source", "url", "summary", "category", "priority"):
                    assert field in item, f"Snapshot {snap['id']}: missing field {field!r} in {item}"

    def test_irrelevant_text_returns_empty(self):
        """Text with no tech relevance should return no relevant items."""
        irrelevant_snaps = [s for s in self._load_snapshots() if s.get("expected_items_min") == 0]
        if not irrelevant_snaps:
            pytest.skip("No irrelevant text snapshots")

        for snap in irrelevant_snaps:
            import core.cluster.scripts.intel_below_extractor as mod
            # Mock Below to return items with relevant=False
            with patch.object(mod, "_below_chat", return_value={"items": [
                {"title": "sports", "source": "x", "url": "https://x.com", "summary": "sports",
                 "source_type": "blog", "category": "general-news", "priority": "low", "relevant": False}
            ]}):
                result = extract_intel_items(snap["raw_text"])
            assert len(result) == 0, f"Snapshot {snap['id']}: expected 0 items but got {len(result)}"
