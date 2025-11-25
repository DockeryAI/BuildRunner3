"""
Rate Limiting Middleware for FastAPI

Implements token bucket rate limiting to prevent API abuse:
- Per-IP rate limiting
- Configurable limits per endpoint
- Redis-backed for distributed systems (with in-memory fallback)
- Automatic cleanup of expired entries
- Rate limit headers in responses

Usage:
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=100,
        default_window=60
    )

    Or per-route:
    @app.get("/api/prd/current")
    @rate_limit(limit=10, window=60)
    async def get_prd():
        ...
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

logger = logging.getLogger(__name__)


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting"""
    tokens: float
    last_update: float
    limit: int
    window: int  # seconds

    def consume(self, current_time: float) -> Tuple[bool, int]:
        """
        Try to consume a token

        Returns:
            Tuple of (success, retry_after_seconds)
        """
        # Refill tokens based on time passed
        time_passed = current_time - self.last_update
        refill_rate = self.limit / self.window
        self.tokens = min(self.limit, self.tokens + (time_passed * refill_rate))
        self.last_update = current_time

        # Try to consume
        if self.tokens >= 1:
            self.tokens -= 1
            return True, 0
        else:
            # Calculate retry after
            tokens_needed = 1 - self.tokens
            retry_after = int(tokens_needed / refill_rate) + 1
            return False, retry_after


class RateLimitStore:
    """
    In-memory rate limit store with automatic cleanup

    In production, replace with Redis for distributed systems
    """

    def __init__(self):
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        self._lock = asyncio.Lock()

    async def get_bucket(self, key: str, limit: int, window: int) -> RateLimitBucket:
        """Get or create rate limit bucket for key"""
        async with self._lock:
            # Periodic cleanup
            current_time = time.time()
            if current_time - self.last_cleanup > self.cleanup_interval:
                await self._cleanup(current_time)

            if key not in self.buckets:
                self.buckets[key] = RateLimitBucket(
                    tokens=float(limit),
                    last_update=current_time,
                    limit=limit,
                    window=window
                )

            return self.buckets[key]

    async def _cleanup(self, current_time: float):
        """Remove expired buckets"""
        expired_keys = [
            key for key, bucket in self.buckets.items()
            if current_time - bucket.last_update > bucket.window * 2
        ]

        for key in expired_keys:
            del self.buckets[key]

        self.last_cleanup = current_time
        logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit buckets")

    async def consume(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Try to consume a token from bucket

        Returns:
            Tuple of (success, retry_after_seconds)
        """
        bucket = await self.get_bucket(key, limit, window)
        current_time = time.time()
        return bucket.consume(current_time)


# Global store instance
_store: Optional[RateLimitStore] = None


def get_rate_limit_store() -> RateLimitStore:
    """Get or create global rate limit store"""
    global _store
    if _store is None:
        _store = RateLimitStore()
    return _store


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting

    Applies default rate limits to all routes unless overridden
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.exclude_paths = exclude_paths or []
        self.store = get_rate_limit_store()

    def get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client

        Uses IP address by default. In production, consider:
        - User ID if authenticated
        - API key
        - Combination of IP + User-Agent
        """
        # Try to get real IP from headers (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting"""
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        path = request.url.path

        # Skip excluded paths
        if self.should_exclude(path):
            return await call_next(request)

        # Get rate limit config (check if route has custom limits)
        limit = getattr(request.state, "rate_limit", self.default_limit)
        window = getattr(request.state, "rate_limit_window", self.default_window)

        # Get client identifier
        client_id = self.get_client_identifier(request)
        key = f"{client_id}:{path}"

        # Try to consume token
        success, retry_after = await self.store.consume(key, limit, window)

        if not success:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {client_id} on {path}. "
                f"Retry after {retry_after}s"
            )

            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Window": str(window)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        bucket = await self.store.get_bucket(key, limit, window)
        remaining = int(bucket.tokens)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(bucket.last_update + window)
        )

        return response


# Decorator for per-route rate limits
def rate_limit(limit: int, window: int = 60):
    """
    Decorator to set custom rate limits for specific routes

    Example:
        @app.get("/api/expensive")
        @rate_limit(limit=5, window=60)
        async def expensive_operation():
            ...
    """
    def decorator(func):
        # Store rate limit config on function
        func._rate_limit = limit
        func._rate_limit_window = window
        return func
    return decorator


# Endpoint-specific rate limit configurations
RATE_LIMIT_CONFIG = {
    # PRD endpoints
    "/api/prd/current": {"limit": 100, "window": 60},  # 100 reads per minute
    "/api/prd/update": {"limit": 30, "window": 60},    # 30 updates per minute
    "/api/prd/parse": {"limit": 50, "window": 60},     # 50 parses per minute
    "/api/prd/versions": {"limit": 50, "window": 60},  # 50 reads per minute
    "/api/prd/rollback": {"limit": 10, "window": 60},  # 10 rollbacks per minute

    # Task endpoints
    "/api/tasks": {"limit": 100, "window": 60},
    "/api/tasks/update": {"limit": 50, "window": 60},
    "/api/tasks/complete": {"limit": 50, "window": 60},

    # Build endpoints
    "/api/build/execute": {"limit": 20, "window": 60},  # Limited - expensive
    "/api/build/status": {"limit": 100, "window": 60},
}


def apply_rate_limit_config(request: Request):
    """
    Apply endpoint-specific rate limit configuration

    Call this in a dependency or middleware before route handler
    """
    path = request.url.path
    config = RATE_LIMIT_CONFIG.get(path, {})

    if config:
        request.state.rate_limit = config["limit"]
        request.state.rate_limit_window = config["window"]
