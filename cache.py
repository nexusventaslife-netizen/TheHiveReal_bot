import json
import logging
from typing import Optional, Dict, Any
from redis.asyncio import Redis

# Intentamos usar orjson para velocidad extrema
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

logger = logging.getLogger(__name__)

USER_CACHE_TTL = 300 
P2P_CACHE_TTL = 10
REGION_CACHE_TTL = 3600
SHARD_COUNT = 64

redis_client: Optional[Redis] = None

def key_for_user(telegram_id: int, shard_count: int = SHARD_COUNT) -> str:
    shard = int(telegram_id) % shard_count
    return f"user:{shard}:{telegram_id}"

async def init_cache(client: Redis, *, user_ttl: int = USER_CACHE_TTL, p2p_ttl: int = P2P_CACHE_TTL):
    global redis_client, USER_CACHE_TTL, P2P_CACHE_TTL
    redis_client = client
    USER_CACHE_TTL = user_ttl
    P2P_CACHE_TTL = p2p_ttl
    logger.info(f"✅ CACHÉ INICIALIZADO (Motor: {'ORJSON' if HAS_ORJSON else 'JSON Standard'})")

def _serialize(obj: Dict[str, Any]) -> str:
    if HAS_ORJSON:
        return orjson.dumps(obj).decode('utf-8')
    return json.dumps(obj, default=str, separators=(",", ":"))

def _deserialize(s: Any) -> Optional[Dict[str, Any]]:
    if not s: return None
    try:
        if HAS_ORJSON:
            return orjson.loads(s)
        return json.loads(s)
    except Exception as e:
        logger.error(f"Error deserializando caché: {e}")
        return None

async def cache_get_user(telegram_id: int, fallback_db_callable=None, ttl: int = None) -> Optional[Dict[str, Any]]:
    if not redis_client:
        if fallback_db_callable: return await fallback_db_callable()
        return None

    key = key_for_user(telegram_id)
    try:
        raw = await redis_client.get(key)
        if raw: return _deserialize(raw)
    except Exception as e:
        logger.error(f"⚠️ Redis Read Error: {e}")

    if fallback_db_callable:
        data = await fallback_db_callable()
        if data: 
            try:
                await redis_client.set(key, _serialize(data), ex=ttl or USER_CACHE_TTL)
            except Exception: pass
        return data
    return None

async def cache_set_user(telegram_id: int, data: Dict[str, Any], ttl: int = None):
    if not redis_client: return
    key = key_for_user(telegram_id)
    try:
        await redis_client.set(key, _serialize(data), ex=ttl or USER_CACHE_TTL)
    except Exception as e:
        logger.error(f"⚠️ Redis Write Error: {e}")

async def cache_invalidate_user(telegram_id: int):
    if not redis_client: return
    key = key_for_user(telegram_id)
    try:
        await redis_client.delete(key)
    except Exception: pass
