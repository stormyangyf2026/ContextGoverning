"""Rate limiting using slowapi library.

Configuration is loaded from Settings (env vars / .env file).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings

settings = get_settings()

# Global limiter instance — configured during app startup
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default, settings.rate_limit_hourly],
)
