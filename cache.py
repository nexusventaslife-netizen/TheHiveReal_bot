import json
import logging
from typing import Optional, Dict, Any
from redis.asyncio import Redis

# Intentamos usar orjson para velocidad
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

logger = logging.getLogger(__name__)

USER_CACHE_TTL = 300 
SHARD_COUNT = 64

redis_client: Optional[Redis] = None

def key_for_user(telegram_id: int, shard_count: int = SHARD_COUNT) -> str:
    # Usamos la misma key que database.py para consistencia en este caso simple
    return f"user:{telegram_id}" 

async def init_cache(client: Redis):
    global redis_client
    redis_client = client
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

# Helpers directos para lecturas rápidas si hiciera falta
async def quick_get_user(user_id):
    if not redis_client: return None
    return await redis_client.get(f"user:{user_id}")
