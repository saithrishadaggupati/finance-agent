import hashlib
import json
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# In-memory fallback cache when Redis isn't running
_memory_cache: dict = {}


class CacheService:
    def __init__(self, host: str = "localhost", port: int = 6379, ttl: int = 3600):
        self.ttl = ttl
        self.redis_client = None

        if REDIS_AVAILABLE:
            try:
                client = redis.Redis(host=host, port=port, db=0, socket_connect_timeout=1)
                client.ping()
                self.redis_client = client
            except Exception:
                pass  # Fall through to in-memory cache

    def _make_key(self, question: str, transactions_hash: str) -> str:
        raw = f"{question.lower().strip()}:{transactions_hash}"
        return "finance:" + hashlib.md5(raw.encode()).hexdigest()

    def _hash_transactions(self, transactions: list) -> str:
        serialized = json.dumps(transactions, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    def get(self, question: str, transactions: list) -> Optional[dict]:
        key = self._make_key(question, self._hash_transactions(transactions))

        if self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        # Fallback to memory cache
        return _memory_cache.get(key)

    def set(self, question: str, transactions: list, response: dict):
        key = self._make_key(question, self._hash_transactions(transactions))
        serialized = json.dumps(response, default=str)

        if self.redis_client:
            try:
                self.redis_client.setex(key, self.ttl, serialized)
                return
            except Exception:
                pass

        # Fallback to memory cache
        _memory_cache[key] = response

    def is_redis_connected(self) -> bool:
        return self.redis_client is not None

    def flush(self):
        if self.redis_client:
            try:
                keys = self.redis_client.keys("finance:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass
        _memory_cache.clear()


_cache_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance
