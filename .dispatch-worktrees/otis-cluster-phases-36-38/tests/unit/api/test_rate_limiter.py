"""
Unit tests for Rate Limiter middleware

Tests:
- Token bucket algorithm
- Rate limit enforcement
- Retry-After headers
- Bucket cleanup
- Per-route limits
- Multiple clients
"""

import pytest
import asyncio
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from api.middleware.rate_limiter import (
    RateLimitMiddleware,
    RateLimitStore,
    RateLimitBucket,
    rate_limit,
    apply_rate_limit_config,
    RATE_LIMIT_CONFIG,
)


class TestRateLimitBucket:
    """Test token bucket implementation"""

    def test_bucket_creation(self):
        """Test creating a rate limit bucket"""
        bucket = RateLimitBucket(tokens=10.0, last_update=time.time(), limit=10, window=60)

        assert bucket.tokens == 10.0
        assert bucket.limit == 10
        assert bucket.window == 60

    def test_consume_token_success(self):
        """Test successful token consumption"""
        current = time.time()
        bucket = RateLimitBucket(tokens=5.0, last_update=current, limit=10, window=60)

        success, retry_after = bucket.consume(current)
        assert success is True
        assert retry_after == 0
        assert bucket.tokens == 4.0

    def test_consume_token_failure(self):
        """Test token consumption when bucket is empty"""
        current = time.time()
        bucket = RateLimitBucket(tokens=0.0, last_update=current, limit=10, window=60)

        success, retry_after = bucket.consume(current)
        assert success is False
        assert retry_after > 0

    def test_token_refill(self):
        """Test tokens refill over time"""
        start = time.time()
        bucket = RateLimitBucket(tokens=0.0, last_update=start, limit=10, window=60)

        # Simulate 30 seconds passing (should refill 5 tokens: 10/60 * 30)
        future = start + 30
        success, retry_after = bucket.consume(future)

        # Should have ~5 tokens, so consumption succeeds
        assert success is True
        assert bucket.tokens > 3.0  # Allow some floating point error

    def test_token_cap_at_limit(self):
        """Test tokens don't exceed limit"""
        start = time.time()
        bucket = RateLimitBucket(tokens=5.0, last_update=start, limit=10, window=60)

        # Simulate 120 seconds (should refill 20 tokens, but capped at 10)
        future = start + 120
        bucket.consume(future)

        # After consuming 1, should have 9 (capped at limit 10)
        assert bucket.tokens <= 10.0


class TestRateLimitStore:
    """Test rate limit store"""

    @pytest.mark.asyncio
    async def test_store_creates_bucket(self):
        """Test store creates new buckets"""
        store = RateLimitStore()
        bucket = await store.get_bucket("test-key", limit=10, window=60)

        assert bucket is not None
        assert bucket.limit == 10
        assert bucket.window == 60

    @pytest.mark.asyncio
    async def test_store_reuses_bucket(self):
        """Test store reuses existing buckets"""
        store = RateLimitStore()
        bucket1 = await store.get_bucket("test-key", limit=10, window=60)
        bucket2 = await store.get_bucket("test-key", limit=10, window=60)

        assert bucket1 is bucket2

    @pytest.mark.asyncio
    async def test_consume_success(self):
        """Test consuming from store"""
        store = RateLimitStore()
        success, retry_after = await store.consume("test-key", limit=10, window=60)

        assert success is True
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_consume_multiple(self):
        """Test consuming multiple tokens"""
        store = RateLimitStore()

        # Consume 10 tokens (should all succeed)
        for i in range(10):
            success, _ = await store.consume("test-key", limit=10, window=60)
            assert success is True

        # 11th should fail
        success, retry_after = await store.consume("test-key", limit=10, window=60)
        assert success is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_separate_keys(self):
        """Test different keys have separate limits"""
        store = RateLimitStore()

        # Exhaust key1
        for i in range(5):
            await store.consume("key1", limit=5, window=60)

        # key2 should still work
        success, _ = await store.consume("key2", limit=5, window=60)
        assert success is True

        # key1 should be exhausted
        success, _ = await store.consume("key1", limit=5, window=60)
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test expired buckets are cleaned up"""
        store = RateLimitStore()
        store.cleanup_interval = 0  # Force immediate cleanup

        # Create bucket
        await store.get_bucket("old-key", limit=10, window=1)
        assert "old-key" in store.buckets

        # Wait for expiry
        await asyncio.sleep(2.5)

        # Trigger cleanup by getting another bucket
        await store.get_bucket("new-key", limit=10, window=60)

        # Old key should be cleaned up
        assert "old-key" not in store.buckets
        assert "new-key" in store.buckets


class TestRateLimitMiddleware:
    """Test FastAPI rate limit middleware"""

    def create_test_app(self, limit=5, window=60, exclude_paths=None):
        """Create test FastAPI app with rate limiting"""
        app = FastAPI()

        app.add_middleware(
            RateLimitMiddleware,
            default_limit=limit,
            default_window=window,
            exclude_paths=exclude_paths or [],
        )

        @app.get("/api/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/api/excluded")
        async def excluded_endpoint():
            return {"message": "excluded"}

        @app.get("/api/custom")
        @rate_limit(limit=2, window=60)
        async def custom_limit_endpoint():
            return {"message": "custom"}

        return app

    def test_rate_limit_allows_requests(self):
        """Test rate limiter allows requests under limit"""
        app = self.create_test_app(limit=5, window=60)
        client = TestClient(app)

        # Should allow 5 requests
        for i in range(5):
            response = client.get("/api/test")
            assert response.status_code == 200

    def test_rate_limit_blocks_excess(self):
        """Test rate limiter blocks requests over limit"""
        app = self.create_test_app(limit=3, window=60)
        client = TestClient(app)

        # First 3 succeed
        for i in range(3):
            response = client.get("/api/test")
            assert response.status_code == 200

        # 4th should fail
        response = client.get("/api/test")
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["error"].lower()

    def test_rate_limit_headers(self):
        """Test rate limit headers in response"""
        app = self.create_test_app(limit=10, window=60)
        client = TestClient(app)

        response = client.get("/api/test")
        assert response.status_code == 200

        # Check headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        assert int(response.headers["X-RateLimit-Limit"]) == 10
        assert int(response.headers["X-RateLimit-Remaining"]) == 9

    def test_retry_after_header(self):
        """Test Retry-After header when rate limited"""
        app = self.create_test_app(limit=1, window=60)
        client = TestClient(app)

        # Exhaust limit
        client.get("/api/test")

        # Should get Retry-After header
        response = client.get("/api/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert int(response.headers["Retry-After"]) > 0

    def test_excluded_paths(self):
        """Test excluded paths bypass rate limiting"""
        app = self.create_test_app(limit=1, window=60, exclude_paths=["/api/excluded"])
        client = TestClient(app)

        # Exhaust limit on normal endpoint
        client.get("/api/test")
        response = client.get("/api/test")
        assert response.status_code == 429

        # Excluded endpoint should still work
        for i in range(10):
            response = client.get("/api/excluded")
            assert response.status_code == 200

    def test_different_paths_separate_limits(self):
        """Test different paths have separate rate limits"""
        app = self.create_test_app(limit=2, window=60)
        client = TestClient(app)

        # Exhaust /api/test
        client.get("/api/test")
        client.get("/api/test")
        response = client.get("/api/test")
        assert response.status_code == 429

        # /api/excluded should still work
        response = client.get("/api/excluded")
        assert response.status_code == 200


class TestRateLimitConfig:
    """Test rate limit configuration"""

    def test_config_has_prd_endpoints(self):
        """Test configuration includes PRD endpoints"""
        assert "/api/prd/current" in RATE_LIMIT_CONFIG
        assert "/api/prd/update" in RATE_LIMIT_CONFIG
        assert "/api/prd/parse" in RATE_LIMIT_CONFIG

    def test_config_values(self):
        """Test configuration has valid values"""
        for path, config in RATE_LIMIT_CONFIG.items():
            assert "limit" in config
            assert "window" in config
            assert config["limit"] > 0
            assert config["window"] > 0

    def test_expensive_endpoints_lower_limits(self):
        """Test expensive endpoints have lower limits"""
        # Update should be more limited than read
        update_limit = RATE_LIMIT_CONFIG["/api/prd/update"]["limit"]
        read_limit = RATE_LIMIT_CONFIG["/api/prd/current"]["limit"]

        assert update_limit < read_limit

        # Build execute should be very limited
        build_limit = RATE_LIMIT_CONFIG["/api/build/execute"]["limit"]
        assert build_limit < update_limit


class TestRateLimitDecorator:
    """Test rate limit decorator"""

    def test_decorator_sets_attributes(self):
        """Test decorator sets rate limit attributes"""

        @rate_limit(limit=5, window=30)
        def test_func():
            pass

        assert hasattr(test_func, "_rate_limit")
        assert hasattr(test_func, "_rate_limit_window")
        assert test_func._rate_limit == 5
        assert test_func._rate_limit_window == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
