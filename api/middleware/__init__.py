"""
API Middleware Package

Contains middleware components for FastAPI application:
- Rate limiting
- Authentication (future)
- CORS (future)
- Logging (future)
"""

from .rate_limiter import (
    RateLimitMiddleware,
    rate_limit,
    apply_rate_limit_config,
    get_rate_limit_store,
    RATE_LIMIT_CONFIG,
)

__all__ = [
    "RateLimitMiddleware",
    "rate_limit",
    "apply_rate_limit_config",
    "get_rate_limit_store",
    "RATE_LIMIT_CONFIG",
]
