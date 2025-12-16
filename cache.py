# cache.py
import json
from typing import Optional, Dict, Any
from redis.asyncio import Redis

USER_CACHE_TTL = 60
P2P_CACHE_TTL = 10
REGION_CACHE_TTL = 3600
SHARD_COUNT = 64

redis_client: Optional[Redis] = None

def key_for_user(telegram_id: int, shard_count: int = SHARD_COUNT) -> str:
    shard = int(telegram_id) % shard_count
    return f"user:{shard}:{telegram_id}"

def key_for_p2p() -> str:
    return "p2p:offers"

async def init_cache(client: Redis, *, user_ttl: int = USER_CACHE_TTL, p2p_ttl: int = P2P_CACHE_TTL):
    global redis_client, USER_CACHE_TTL, P2P_CACHE_TTL
    redis_client = client
    USER_CACHE_TTL = user_ttl
    P2P_CACHE_TTL = p2p_ttl

def _serialize(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, default=str, separators=(",", ":"))

def _deserialize(s: str) -> Optional[Dict[str, Any]]:
    if not s: return None
    try: return json.loads(s)
    except Exception: return None

async def cache_get_user(telegram_id: int, fallback_db_callable=None, ttl: int = None) -> Optional[Dict[str, Any]]:
    if not redis_client:
        if fallback_db_callable: return await fallback_db_callable()
        return None

    key = key_for_user(telegram_id)
    raw = await redis_client.get(key)
    if raw: return _deserialize(raw)

    if fallback_db_callable:
        data = await fallback_db_callable()
        if data: await redis_client.set(key, _serialize(data), ex=ttl or USER_CACHE_TTL)
        return data
    return None

async def cache_set_user(telegram_id: int, data: Dict[str, Any], ttl: int = None):
    if not redis_client: return
    key = key_for_user(telegram_id)
    await redis_client.set(key, _serialize(data), ex=ttl or USER_CACHE_TTL)

async def cache_invalidate_user(telegram_id: int):
    if not redis_client: return
    key = key_for_user(telegram_id)
    await redis_client.delete(key)
