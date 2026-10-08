import hashlib
import json
import logging
import time
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class CacheLayer:
    """
    Enterprise Caching Layer for the Copilot.
    Uses Redis as the primary backend with automatic fallback to an
    in-memory TTL cache when Redis is unavailable or unconfigured.
    """

    def __init__(self):
        self.enabled = settings.redis_enabled
        self.ttl = settings.cache_ttl_seconds
        self._redis_client = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0

        if self.enabled:
            self._init_redis()

    def _init_redis(self):
        try:
            import redis
            redis_url = settings.redis_url
            # Render's managed Redis uses rediss:// (TLS) with a self-signed cert.
            # Append ssl_cert_reqs=none to the URL — works across all redis-py versions
            # without relying on kwarg support that varies by version.
            if redis_url.startswith("rediss://") and "ssl_cert_reqs" not in redis_url:
                sep = "&" if "?" in redis_url else "?"
                redis_url = f"{redis_url}{sep}ssl_cert_reqs=none"
            client = redis.Redis.from_url(
                redis_url,
                socket_connect_timeout=2.0,
                decode_responses=True,
            )
            client.ping()
            self._redis_client = client
            logger.info(f"Connected to Redis cache at {settings.redis_url}")
        except Exception as exc:
            logger.warning(
                f"Redis connection failed ({exc}). Operating with high-performance in-memory fallback cache."
            )
            self._redis_client = None

    @staticmethod
    def _compute_key(query: str, namespace: str = "copilot") -> str:
        normalized = query.strip().lower()
        query_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"{namespace}:{query_hash}"

    def get(self, query: str, namespace: str = "copilot") -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        key = self._compute_key(query, namespace)

        # 1. Try Redis
        if self._redis_client is not None:
            try:
                cached_data = self._redis_client.get(key)
                if cached_data:
                    self._hits += 1
                    logger.debug(f"Redis cache HIT for key: {key}")
                    return json.loads(cached_data)
            except Exception as exc:
                logger.warning(f"Error reading from Redis ({exc}); checking in-memory cache.")

        # 2. Try In-Memory Cache
        entry = self._memory_cache.get(key)
        if entry:
            if time.time() < entry["expires_at"]:
                self._hits += 1
                logger.debug(f"In-memory cache HIT for key: {key}")
                return entry["data"]
            else:
                del self._memory_cache[key]

        self._misses += 1
        return None

    def set(self, query: str, data: Dict[str, Any], namespace: str = "copilot", ttl: Optional[int] = None) -> None:
        if not self.enabled:
            return

        key = self._compute_key(query, namespace)
        effective_ttl = ttl if ttl is not None else self.ttl
        serialized = json.dumps(data)

        # 1. Write to Redis
        if self._redis_client is not None:
            try:
                self._redis_client.setex(key, effective_ttl, serialized)
                logger.debug(f"Stored entry in Redis cache for key: {key} (ttl={effective_ttl}s)")
            except Exception as exc:
                logger.warning(f"Error writing to Redis ({exc}); saving to in-memory cache.")

        # 2. Write to In-Memory Cache
        self._memory_cache[key] = {
            "data": data,
            "expires_at": time.time() + effective_ttl,
        }

    def clear(self) -> None:
        if self._redis_client is not None:
            try:
                keys = self._redis_client.keys("copilot:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as exc:
                logger.error(f"Error flushing Redis keys: {exc}")
        self._memory_cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        hit_ratio = (self._hits / total) if total > 0 else 0.0
        return {
            "backend": "redis" if self._redis_client else "in_memory",
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 4),
            "memory_cache_size": len(self._memory_cache),
        }


cache_service = CacheLayer()
