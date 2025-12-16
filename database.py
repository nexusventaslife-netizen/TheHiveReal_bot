import json
import logging
import redis.asyncio as redis
from datetime import datetime

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

# TU URL DE UPSTASH (Pegada directa para que no falle)
REDIS_URL = "rediss://default:AbEBAAIncDIxNTYwNjk5MzkwODc0OGE2YWUyNmJkMmI1N2M4MmNiM3AyNDUzMTM@brave-hawk-45313.upstash.io:6379"

# Cliente Global
r = None

# Estructura Base (ACTUALIZADA V47.5 - ENGANCHE MASIVO)
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "nectar": 500,        # Moneda Interna (HIVE)
    "usd_balance": 0.05,  # Saldo Real
    "skills": [],         # Inventario
    "joined_at": "",
    "referrals": [],
    "referred_by": None,
    "last_active": "",
    # --- NUEVOS CAMPOS PARA ENGANCHE (ESTRATEGIA ANTI-HAMSTER) ---
    "streak_days": 0,           # Días seguidos entrando (Racha)
    "last_streak_date": "",     # Fecha del último login para calcular racha
    "energy": 100,              # Energía para minar (Limita bots, obliga a gastar HIVE)
    "lucky_tickets": 0          # Boletos ganados en minería crítica
}

# --- FUNCIONES DE SISTEMA ---

async def init_db():
    """Conecta a Redis al iniciar"""
    global r
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        logger.info("✅ CONEXIÓN REDIS UPSTASH EXITOSA")
    except Exception as e:
        logger.error(f"❌ FALLÓ CONEXIÓN REDIS: {e}")

async def close_db():
    """Cierra la conexión al apagar"""
    global r
    if r:
        await r.aclose()
        logger.info("🔒 CONEXIÓN REDIS CERRADA")

# --- FUNCIONES DE LÓGICA DE USUARIOS ---

async def add_user(user_id, first_name, username, referred_by=None):
    """Agrega usuario a Redis"""
    global r
    uid = str(user_id)
    key = f"user:{uid}"
    
    exists = await r.exists(key)
    
    if not exists:
        new_user = DEFAULT_USER.copy()
        new_user.update({
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "referred_by": referred_by
        })
        
        await r.set(key, json.dumps(new_user))
        
        # Procesar Referido
        if referred_by:
            rid = str(referred_by)
            ref_key = f"user:{rid}"
            
            if await r.exists(ref_key):
                parent_data = json.loads(await r.get(ref_key))
                
                if rid != uid and uid not in parent_data.get("referrals", []):
                    parent_data.setdefault("referrals", []).append(uid)
                    parent_data["nectar"] = parent_data.get("nectar", 500) + 50
                    await r.set(ref_key, json.dumps(parent_data))
        
        return True
    else:
        # Actualizar last_active
        data = json.loads(await r.get(key))
        data["last_active"] = datetime.now().isoformat()
        await r.set(key, json.dumps(data))
        return False

async def update_email(user_id, email):
    """Actualiza email en Redis"""
    global r
    key = f"user:{user_id}"
    if await r.exists(key):
        data = json.loads(await r.get(key))
        data["email"] = email
        await r.set(key, json.dumps(data))

async def get_user(user_id):
    """Obtiene datos de Redis"""
    global r
    key = f"user:{user_id}"
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None

async def save_db(data=None):
    pass
