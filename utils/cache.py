import json
import logging
from functools import wraps
from typing import Optional, Any
from extensions import redis_client
import redis

logger = logging.getLogger("erp_cache")

class TenantRedis:
    def __init__(self, redis_client):
        self.r = redis_client

    def _key(self, key: str) -> str:
        # Public keys keep the prefix without tenant slug
        if key.startswith("tenant:"):
            return key
        try:
            from utils.tenant_context import get_current_tenant
            tenant = get_current_tenant()
            return f"t:{tenant['slug']}:{key}"
        except Exception:
            return f"t:default:{key}"

    def get(self, key: str) -> Optional[Any]:
        return self.r.get(self._key(key))

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        k = self._key(key)
        if ex is not None:
            return self.r.setex(k, ex, value)
        return self.r.set(k, value)

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        return self.r.setex(self._key(key), ttl, value)

    def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return self.r.delete(*[self._key(k) for k in keys])

    def keys(self, pattern: str) -> list:
        if pattern.startswith("tenant:"):
            return self.r.keys(pattern)
        try:
            from utils.tenant_context import get_current_tenant
            tenant = get_current_tenant()
            prefix = f"t:{tenant['slug']}:"
        except Exception:
            prefix = "t:default:"
        full_pattern = f"{prefix}{pattern}"
        keys = self.r.keys(full_pattern)
        if not keys:
            return []
            
        decoded_keys = []
        for k in keys:
            k_str = k.decode('utf-8') if isinstance(k, bytes) else str(k)
            if k_str.startswith(prefix):
                decoded_keys.append(k_str[len(prefix):])
            else:
                decoded_keys.append(k_str)
        return decoded_keys

    def delete_tenant_all(self, tenant_slug: str):
        """Delete all keys belonging to a specific tenant."""
        pattern = f"t:{tenant_slug}:*"
        keys = self.r.keys(pattern)
        if keys:
            self.r.delete(*keys)

# Scoped TenantRedis wrapper instance
tenant_redis = TenantRedis(redis_client)

class Cache:
    @staticmethod
    def get(key: str) -> Optional[Any]:
        try:
            data = tenant_redis.get(key)
            if data:
                return json.loads(data)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            logger.warning(f"Redis unavailable while getting key: {key}. Falling back to DB.")
        except Exception as e:
            logger.error(f"Cache error: {e}")
        return None

    @staticmethod
    def set(key: str, value: Any, ttl: int = 300):
        try:
            tenant_redis.setex(key, ttl, json.dumps(value))
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            pass
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")

    @staticmethod
    def delete(key: str):
        try:
            tenant_redis.delete(key)
        except Exception:
            pass

    @staticmethod
    def invalidate_pattern(pattern: str):
        """Invalidate all keys matching a pattern scoped to current tenant."""
        try:
            keys = tenant_redis.keys(pattern)
            if keys:
                tenant_redis.delete(*keys)
        except Exception:
            pass

    @staticmethod
    def cached(ttl: int = 300, key_prefix: str = ""):
        """Decorator to cache function results in Redis scoped by tenant."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                arg_str = ":".join([str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()])
                cache_key = f"{key_prefix or f.__name__}:{arg_str}"
                
                cached_value = Cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                result = f(*args, **kwargs)
                Cache.set(cache_key, result, ttl)
                return result
            return decorated_function
        return decorator

def cache_result(key_template: str, ttl: int = 300):
    """
    Decorator to cache function results in Redis with dynamic key formatting 
    based on arguments, scoped by tenant.
    """
    import inspect
    def decorator(f):
        sig = inspect.signature(f)
        @wraps(f)
        def decorated_function(*args, **kwargs):
            bust = kwargs.pop('bust', False)
            
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            
            try:
                fmt_args = {k: str(v) for k, v in bound.arguments.items()}
                cache_key = key_template.format(**fmt_args)
            except Exception:
                cache_key = f"fallback:{f.__name__}:{hash(frozenset(bound.arguments.items()))}"
                
            if not bust:
                cached_value = Cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
                    
            result = f(*args, **kwargs)
            Cache.set(cache_key, result, ttl)
            return result
        return decorated_function
    return decorator

# Specific cache helper instance
erp_cache = Cache()
