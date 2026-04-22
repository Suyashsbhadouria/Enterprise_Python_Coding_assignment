import os

import redis
from functools import wraps
import json
import hashlib

from Logger.logging_config import configure_logging, get_log_file_path

# Initialize Redis client
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.StrictRedis(
    host=redis_host,
    port=redis_port,
    db=0,
    decode_responses=True
)
logger = configure_logging(__name__)

LOG_FILE_PATH = get_log_file_path()


def make_cache_key(prefix, func_name, args, kwargs):
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return f"{prefix}:{func_name}:{hashlib.md5(raw.encode()).hexdigest()}"

def redis_cache(key_prefix, ttl):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = make_cache_key(key_prefix, func.__name__, args, kwargs)

            try:
                cached_result = redis_client.get(cache_key)

                if cached_result:
                    logger.info(f"✅ Cache HIT: {cache_key}")
                    return json.loads(cached_result)

                logger.info(f"❌ Cache MISS: {cache_key}")

                result = func(*args, **kwargs)
                redis_client.setex(cache_key, ttl, json.dumps(result))

                return result

            except Exception as e:
                logger.error(f"Redis error: {e}")
                return func(*args, **kwargs)

        return wrapper
    return decorator