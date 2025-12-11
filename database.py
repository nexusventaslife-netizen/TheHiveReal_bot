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

# Estructura Base
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "tokens": 100,
    "joined_at": "",
    "referrals": [],
    "referred_by": None,
    "last_active": ""
}

# --- FUNCIONES DE SISTEMA (OBLIGATORIAS PARA MAIN.PY) ---

async def init_db():
    """Conecta a Redis al iniciar"""
    global r
    try:
        # decode_responses=True hace que los datos vengan como texto, no bytes
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
    
    # Verificar si existe
    exists = await r.exists(key)
    
    if not exists:
        # Crear usuario nuevo
        new_user = DEFAULT_USER.copy()
        new_user.update({
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "referred_by": referred_by
        })
        
        # Guardar como JSON string en Redis
        await r.set(key, json.dumps(new_user))
        
        # Procesar Referido
        if referred_by:
            rid = str(referred_by)
            ref_key = f"user:{rid}"
            
            # Verificar si el padre existe
            if await r.exists(ref_key):
                # Traer datos del padre
                parent_data = json.loads(await r.get(ref_key))
                
                # Evitar duplicados y autoreferidos
                if rid != uid and uid not in parent_data.get("referrals", []):
                    parent_data.setdefault("referrals", []).append(uid)
                    parent_data["tokens"] = parent_data.get("tokens", 100) + 50
                    
                    # Guardar actualización del padre
                    await r.set(ref_key, json.dumps(parent_data))
        
        return True # Nuevo usuario creado
    else:
        # Usuario ya existe, actualizar last_active
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

# Función auxiliar de compatibilidad
async def save_db(data=None):
    pass # Redis guarda al instante, no necesitamos save manual
async def load_db():
    pass # Redis no carga archivos
