"""
tests/cluster/test_below_embed.py

Unit tests for core.cluster.below.embed — happy path, Below-offline fallback,
malformed response. All HTTP calls are mocked; no real network access.
"""

from __future__ import annotations

import pytest
import httpx

from unittest.mock import patch, MagicMock

from core.cluster.below.embed import (
    EMBED_DIM,
    EMBED_MODEL,
    BelowOfflineError,
    EmbedDimensionError,
    MalformedEmbedResponse,
    check_below_embed_available,
    embed_batch,
    reset_circuit_breaker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_embed_response(texts: list[str]) -> dict:
    """Build a mock Ollama /api/embed response with synthetic 768-d vectors."""
    embeddings = [[float(i) * 0.001] * EMBED_DIM for i in range(len(texts))]
    return {"model": EMBED_MODEL, "embeddings": embeddings, "total_duration": 12345678}


def _mock_httpx_post(response_data: dict, status_code: int = 200):
    """Return a context-manager-compatible mock for httpx.post."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = response_data
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_resp,
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cb():
    """Reset circuit breaker before every test to prevent state leakage."""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestEmbedBatchHappyPath:
    def test_single_text_returns_768d_vector(self):
        texts = ["hello world"]
        resp_data = _make_embed_response(texts)

        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(resp_data)):
            result = embed_batch(texts)

        assert len(result) == 1
        assert len(result[0]) == EMBED_DIM
        assert all(isinstance(v, float) for v in result[0])

    def test_batch_preserves_order(self):
        texts = ["alpha", "beta", "gamma"]
        resp_data = _make_embed_response(texts)

        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(resp_data)):
            result = embed_batch(texts)

        assert len(result) == 3
        # Each vector should be distinct (synthetic data: index * 0.001)
        assert result[0][0] == pytest.approx(0.0)
        assert result[1][0] == pytest.approx(0.001)
        assert result[2][0] == pytest.approx(0.002)

    def test_returns_list_of_floats(self):
        texts = ["test embedding consistency"]
        resp_data = _make_embed_response(texts)

        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(resp_data)):
            result = embed_batch(texts)

        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert all(isinstance(v, float) for v in result[0])

    def test_integer_values_coerced_to_float(self):
        """Ollama may return integer 0 in sparse vectors; embed_batch must coerce."""
        texts = ["sparse"]
        data = {"model": EMBED_MODEL, "embeddings": [[0] * EMBED_DIM]}

        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(data)):
            result = embed_batch(texts)

        assert all(isinstance(v, float) for v in result[0])

    def test_empty_texts_raises_value_error(self):
        with pytest.raises(ValueError, match="at least one text"):
            embed_batch([])


# ---------------------------------------------------------------------------
# Below-offline / network failure fallback
# ---------------------------------------------------------------------------


class TestBelowOfflineFallback:
    def test_connect_error_raises_below_offline(self):
        with patch(
            "core.cluster.below.embed.httpx.post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(BelowOfflineError):
                embed_batch(["test"], retries=0)

    def test_timeout_raises_below_offline(self):
        with patch(
            "core.cluster.below.embed.httpx.post",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(BelowOfflineError):
                embed_batch(["test"], retries=0)

    def test_http_500_raises_below_offline(self):
        mock_resp = _mock_httpx_post({}, status_code=500)
        with patch("core.cluster.below.embed.httpx.post", return_value=mock_resp):
            with pytest.raises(BelowOfflineError):
                embed_batch(["test"], retries=0)

    def test_retries_are_attempted(self):
        call_count = 0

        def flaky_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("transient")
            return _mock_httpx_post(_make_embed_response(["text"]))

        with patch("core.cluster.below.embed.httpx.post", side_effect=flaky_post):
            with patch("core.cluster.below.embed.time.sleep"):  # skip delay
                result = embed_batch(["text"], retries=2)

        assert call_count == 3
        assert len(result) == 1

    def test_circuit_breaker_trips_after_threshold_failures(self):
        from core.cluster.below.embed import _CIRCUIT_THRESHOLD

        with patch(
            "core.cluster.below.embed.httpx.post",
            side_effect=httpx.ConnectError("down"),
        ):
            for _ in range(_CIRCUIT_THRESHOLD):
                try:
                    embed_batch(["x"], retries=0)
                except BelowOfflineError:
                    pass

        # Circuit should now be open — should raise without making a network call
        with patch("core.cluster.below.embed.httpx.post") as mock_post:
            with pytest.raises(BelowOfflineError, match="circuit breaker"):
                embed_batch(["y"], retries=0)
            mock_post.assert_not_called()

    def test_check_below_embed_available_returns_false_on_error(self):
        with patch(
            "core.cluster.below.embed.httpx.post",
            side_effect=httpx.ConnectError("down"),
        ):
            result = check_below_embed_available(timeout=1.0)
        assert result is False

    def test_check_below_embed_available_returns_true_on_success(self):
        resp_data = _make_embed_response(["ping"])
        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(resp_data)):
            result = check_below_embed_available()
        assert result is True


# ---------------------------------------------------------------------------
# Malformed response handling
# ---------------------------------------------------------------------------


class TestMalformedResponse:
    def test_missing_embeddings_key(self):
        bad_data = {"model": EMBED_MODEL, "something_else": []}
        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(bad_data)):
            with pytest.raises(MalformedEmbedResponse, match="missing 'embeddings'"):
                embed_batch(["test"], retries=0)

    def test_wrong_count_of_embeddings(self):
        # Send 2 texts but return only 1 embedding
        texts = ["a", "b"]
        bad_data = {"model": EMBED_MODEL, "embeddings": [[0.1] * EMBED_DIM]}
        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(bad_data)):
            with pytest.raises(MalformedEmbedResponse, match="Expected 2 embeddings"):
                embed_batch(texts, retries=0)

    def test_wrong_embedding_dimension(self):
        texts = ["test"]
        bad_data = {"model": EMBED_MODEL, "embeddings": [[0.1] * 512]}  # wrong dim
        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(bad_data)):
            with pytest.raises(EmbedDimensionError, match="dimension 512"):
                embed_batch(texts, retries=0)

    def test_non_dict_response(self):
        with patch("core.cluster.below.embed.httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = ["not", "a", "dict"]
            mock_post.return_value = mock_resp

            with pytest.raises(MalformedEmbedResponse, match="Expected dict"):
                embed_batch(["test"], retries=0)

    def test_embedding_not_list_of_numbers(self):
        texts = ["test"]
        bad_data = {"model": EMBED_MODEL, "embeddings": [["a"] * EMBED_DIM]}
        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(bad_data)):
            with pytest.raises(MalformedEmbedResponse, match="not a list of numbers"):
                embed_batch(texts, retries=0)

    def test_malformed_does_not_retry(self):
        """Structural errors should not be retried — they won't fix themselves."""
        call_count = 0

        def bad_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"model": EMBED_MODEL}  # missing 'embeddings'
            return mock_resp

        with patch("core.cluster.below.embed.httpx.post", side_effect=bad_post):
            with pytest.raises(MalformedEmbedResponse):
                embed_batch(["test"], retries=5)

        assert call_count == 1, "Malformed response should not trigger retries"


# ---------------------------------------------------------------------------
# Circuit breaker reset
# ---------------------------------------------------------------------------


class TestCircuitBreakerReset:
    def test_reset_allows_calls_after_trip(self):
        from core.cluster.below.embed import _CIRCUIT_THRESHOLD

        # Trip the breaker
        with patch(
            "core.cluster.below.embed.httpx.post",
            side_effect=httpx.ConnectError("down"),
        ):
            for _ in range(_CIRCUIT_THRESHOLD):
                try:
                    embed_batch(["x"], retries=0)
                except BelowOfflineError:
                    pass

        # Force reset
        reset_circuit_breaker()

        # Now a good response should work
        resp_data = _make_embed_response(["hello"])
        with patch("core.cluster.below.embed.httpx.post", return_value=_mock_httpx_post(resp_data)):
            result = embed_batch(["hello"])

        assert len(result) == 1
