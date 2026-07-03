"""
Caching service for routing responses.
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheService:
    """Service to handle caching of route API responses."""

    def __init__(self, timeout_seconds: int = 3600) -> None:
        self.timeout = timeout_seconds

    def _generate_key(self, start: str, destination: str) -> str:
        """Generate a deterministic cache key based on locations."""
        # Normalize strings: lowercased, stripped
        normalized = f"{start.strip().lower()}|{destination.strip().lower()}"
        key_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"route:{key_hash}"

    def get_route(self, start: str, destination: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached route response if it exists."""
        key = self._generate_key(start, destination)
        try:
            cached_data = cache.get(key)
            if cached_data:
                logger.info("Cache hit for route: %s -> %s", start, destination)
                # Parse back from string if we stored as JSON string
                if isinstance(cached_data, str):
                    return json.loads(cached_data)
                return cached_data
        except Exception as e:
            logger.warning("Failed to retrieve from cache: %s", str(e))
        return None

    def set_route(self, start: str, destination: str, response_data: Dict[str, Any]) -> None:
        """Cache a route response."""
        key = self._generate_key(start, destination)
        try:
            # Store as JSON string to ensure clean serialization
            cache.set(key, json.dumps(response_data), timeout=self.timeout)
            logger.info("Cached route: %s -> %s", start, destination)
        except Exception as e:
            logger.warning("Failed to write to cache: %s", str(e))
