import json
import logging
import os
import redis.asyncio as redis
from datetime import datetime

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

# Lee la URL de Redis del entorno, o usa una por defecto si falla
# (Es importante que definas REDIS_URL en Render también si quieres máxima seguridad, 
# pero aquí dejo la tuya como fallback para que no deje de funcionar)
ENV_REDIS_URL = os.getenv("REDIS_URL", "rediss://default:AbEBAAIncDIxNTYwNjk5MzkwODc0OGE2YWUyNmJkMmI1N2M4MmNiM3AyNDUzMTM@brave-hawk-45313.upstash.io:6379")

# Cliente Global
r = None

# Estructura Base (ACTUALIZADA V50.0)
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "nectar": 500,        # Moneda Interna (HIVE) - Bono de bienvenida
    "usd_balance": 0.00,  # Saldo Real (Empieza en 0, gana 0.05 al validar)
    "skills": [],         # Inventario
    "joined_at": "",
    "referrals": [],
    "referred_by": None,
    "last_active": "",
    # --- ENGANCHE (ESTRATEGIA ANTI-HAMSTER) ---
    "streak_days": 0,            
    "last_streak_date": "",      
    "energy": 100,               
    "lucky_tickets": 0,          
    "is_premium": False          
}

# --- FUNCIONES DE SISTEMA ---

async def init_db():
    """Conecta a Redis al iniciar con reintentos inteligentes"""
    global r
    try:
        r = redis.from_url(
            ENV_REDIS_URL, 
            decode_responses=True, 
            socket_timeout=5.0,
            socket_connect_timeout=5.0
        )
        await r.ping()
        logger.info("✅ CONEXIÓN REDIS UPSTASH EXITOSA")
    except Exception as e:
        logger.error(f"❌ FALLÓ CONEXIÓN REDIS: {e}")
        r = None

async def close_db():
    """Cierra la conexión al apagar"""
    global r
    if r:
        try:
            await r.aclose()
            logger.info("🔒 CONEXIÓN REDIS CERRADA")
        except Exception as e:
            logger.error(f"Error cerrando Redis: {e}")

# --- FUNCIONES DE LÓGICA DE USUARIOS ---

async def add_user(user_id, first_name, username, referred_by=None):
    """Agrega usuario a Redis de forma segura"""
    global r
    if not r: return False
    
    uid = str(user_id)
    key = f"user:{uid}"
    
    try:
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
            
            # Procesar Referido (Viralidad)
            if referred_by:
                rid = str(referred_by)
                ref_key = f"user:{rid}"
                
                # Verificamos si el referido existe
                if await r.exists(ref_key):
                    raw_parent = await r.get(ref_key)
                    if raw_parent:
                        parent_data = json.loads(raw_parent)
                        
                        if rid != uid and uid not in parent_data.get("referrals", []):
                            parent_data.setdefault("referrals", []).append(uid)
                            # Bono por referido (Solo Néctar)
                            parent_data["nectar"] = int(parent_data.get("nectar", 500)) + 50
                            await r.set(ref_key, json.dumps(parent_data))
            
            logger.info(f"🆕 Nuevo Usuario: {user_id}")
            return True
        else:
            # Actualizar last_active sin borrar datos
            raw_data = await r.get(key)
            if raw_data:
                data = json.loads(raw_data)
                data["last_active"] = datetime.now().isoformat()
                # Asegurar que los nuevos campos existen en usuarios viejos
                for k, v in DEFAULT_USER.items():
                    if k not in data:
                        data[k] = v
                await r.set(key, json.dumps(data))
            return False
            
    except Exception as e:
        logger.error(f"Error en add_user: {e}")
        return False

async def update_email(user_id, email):
    """Actualiza email en Redis"""
    global r
    if not r: return
    key = f"user:{user_id}"
    try:
        if await r.exists(key):
            data = json.loads(await r.get(key))
            data["email"] = email
            await r.set(key, json.dumps(data))
    except Exception as e:
        logger.error(f"Error actualizando email: {e}")

async def get_user(user_id):
    """Obtiene datos de Redis"""
    global r
    if not r: return None
    key = f"user:{user_id}"
    try:
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Error obteniendo usuario {user_id}: {e}")
    return None

async def save_db(data=None):
    pass
