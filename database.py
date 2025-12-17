import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional

# Si usas Python 3.7+, usa redis-py en modo async
try:
    import redis.asyncio as redis 
    # Opcional: si estás en un entorno antiguo o usas aioredis (deprecated)
    # import aioredis as redis 
except ImportError:
    logging.error("❌ Módulo 'redis' (o 'aioredis') no encontrado. Instala: pip install redis")
    redis = None

logger = logging.getLogger("Database")
r: Optional[redis.Redis] = None

# Constantes de Inicialización
DEFAULT_USER_DATA = {
    "usd_balance": 0.00,
    "nectar": 50, # HIVE Tokens
    "tokens_locked": 0,
    "email": None,
    "is_active": False,
    "referrals": [],
    "referrer_id": None,
    # El resto de campos RLE/Anti-fraude se inicializan en bot_logic.start
}

async def init_db():
    """Inicializa la conexión a Redis."""
    global r
    REDIS_URL = os.getenv("REDIS_URL")
    
    if not REDIS_URL:
        logger.warning("⚠️ Variable de entorno REDIS_URL no encontrada. Usando Redis simulado/Dummy. ¡Los datos no se guardarán!")
        # Implementación de un Dummy Redis (Solo para desarrollo local sin Redis)
        class DummyRedis:
            def __init__(self):
                self.data = {}
            async def get(self, key):
                return self.data.get(key)
            async def set(self, key, value):
                self.data[key] = value
            async def exists(self, key):
                return key in self.data
            async def close(self): pass
        r = DummyRedis()
        return

    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        logger.info("✅ Conexión a Redis exitosa.")
    except Exception as e:
        logger.error(f"❌ Error al conectar a Redis: {e}. Usando Dummy Redis.")
        # Fallback si la conexión real falla
        class DummyRedis:
            def __init__(self): self.data = {}
            async def get(self, key): return self.data.get(key)
            async def set(self, key, value): self.data[key] = value
            async def exists(self, key): return key in self.data
            async def close(self): pass
        r = DummyRedis()


async def get_user(user_id: int) -> Dict[str, Any]:
    """Recupera los datos del usuario de Redis, o devuelve un diccionario vacío."""
    if not r: return {}
    
    key = f"user:{user_id}"
    data = await r.get(key)
    
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Error al decodificar JSON para el usuario {user_id}")
            return {} 
    return {}


async def add_user(user_id: int, first_name: str, username: Optional[str], referrer_id: Optional[str] = None):
    """Crea un nuevo usuario si no existe e incrementa el contador de referidos."""
    if not r: return
    
    key = f"user:{user_id}"
    if not await r.exists(key):
        new_data = DEFAULT_USER_DATA.copy()
        new_data.update({
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "referrer_id": int(referrer_id) if referrer_id else None
        })
        
        await r.set(key, json.dumps(new_data))
        logger.info(f"➕ Nuevo usuario: {user_id}")
        
        # Lógica de Referidos
        if referrer_id and referrer_id.isdigit():
            ref_data = await get_user(int(referrer_id))
            if ref_data:
                ref_data['referrals'].append(user_id)
                await r.set(f"user:{referrer_id}", json.dumps(ref_data))
                logger.info(f"🔗 {user_id} agregado a referidos de {referrer_id}")

async def update_email(user_id: int, email: str):
    """Actualiza el correo electrónico del usuario."""
    if not r: return
    user_data = await get_user(user_id)
    if user_data:
        user_data['email'] = email
        await r.set(f"user:{user_id}", json.dumps(user_data))
        logger.info(f"📧 Email actualizado para {user_id}")

# La función save_user_data se mantiene en bot_logic.py para usar 'r' globalmente.
