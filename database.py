import json
import logging
import os
import redis.asyncio as redis
from datetime import datetime

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

# Lee la URL de Redis del entorno
ENV_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Cliente Global
r = None

# Estructura Base PANDORA + HIVE (V200.0)
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    # --- ECONOMÍA ---
    "nectar": 0.0,        # HIVE Líquido
    "locked_nectar": 0.0, # HIVE Bloqueado (Vesting)
    "usd_balance": 0.00,  
    # --- PANDORA ENGINE (Factor X) ---
    "role": "Larva",      # Larva -> Obrero -> Explorador -> Guardián -> Nodo -> Reina
    "energy": 300,        # Max 300 base
    "streak": 0,          # Racha de días
    "consistency": 0.0,   # Puntuación de consistencia (0.0 - 1.0)
    "behavior_score": 0,  # Score interno del Engine
    "hidden_progress": 0, # XP oculta para subir de nivel
    "reputation": 0.0,    # Reputación social
    "spam_score": 0.0,    # Detección de bots
    # --- SOCIAL ---
    "cell_id": None,      # ID de la Célula (Guild)
    "referrals": [],      # Lista de IDs referidos
    "referred_by": None,
    "referral_quality_score": 0, # Puntos por traer gente que TRABAJA
    # --- META ---
    "joined_at": "",
    "last_active": "",
    "last_action_ts": 0   # Timestamp para rate limit
}

# --- FUNCIONES DE SISTEMA ---

async def init_db():
    global r
    try:
        r = redis.from_url(
            ENV_REDIS_URL, 
            decode_responses=True, 
            socket_timeout=5.0,
            socket_connect_timeout=5.0
        )
        await r.ping()
        
        # Inicializar variables globales del HIVE si no existen
        if not await r.exists("hive:global"):
            await r.hset("hive:global", mapping={
                "level": 1,
                "health": 100,
                "work_today": 0.0
            })
            
        logger.info("✅ CONEXIÓN REDIS (PANDORA ENGINE) EXITOSA")
    except Exception as e:
        logger.error(f"❌ FALLÓ CONEXIÓN REDIS: {e}")
        r = None

async def close_db():
    global r
    if r:
        try:
            await r.aclose()
            logger.info("🔒 CONEXIÓN REDIS CERRADA")
        except Exception as e:
            logger.error(f"Error cerrando Redis: {e}")

# --- FUNCIONES DE LÓGICA DE USUARIOS ---

async def add_user(user_id, first_name, username, referred_by=None):
    global r
    if not r: return False
    
    uid = str(user_id)
    key = f"user:{uid}"
    
    try:
        exists = await r.exists(key)
        
        if not exists:
            new_user = DEFAULT_USER.copy()
            now_iso = datetime.now().isoformat()
            new_user.update({
                "id": user_id,
                "first_name": first_name,
                "username": username,
                "joined_at": now_iso,
                "last_active": now_iso,
                "referred_by": referred_by,
                "last_action_ts": datetime.now().timestamp()
            })
            
            await r.set(key, json.dumps(new_user))
            
            # Procesar Referido (Viralidad + Calidad)
            if referred_by and str(referred_by) != uid:
                ref_key = f"user:{referred_by}"
                if await r.exists(ref_key):
                    raw_parent = await r.get(ref_key)
                    if raw_parent:
                        parent_data = json.loads(raw_parent)
                        if uid not in parent_data.get("referrals", []):
                            parent_data.setdefault("referrals", []).append(uid)
                            # NO damos bono inmediato. Se da cuando el referido trabaja (Quality).
                            await r.set(ref_key, json.dumps(parent_data))
            
            logger.info(f"🆕 Nueva Larva: {user_id}")
            return True
        else:
            # Actualizar last_active
            raw_data = await r.get(key)
            if raw_data:
                data = json.loads(raw_data)
                data["last_active"] = datetime.now().isoformat()
                # Migración segura de campos nuevos
                updated = False
                for k, v in DEFAULT_USER.items():
                    if k not in data:
                        data[k] = v
                        updated = True
                if updated:
                    await r.set(key, json.dumps(data))
            return False
            
    except Exception as e:
        logger.error(f"Error en add_user: {e}")
        return False

async def get_user(user_id):
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

async def save_user(user_id, data):
    """Guarda el estado completo del usuario"""
    global r
    if not r: return
    key = f"user:{user_id}"
    try:
        await r.set(key, json.dumps(data))
    except Exception as e:
        logger.error(f"Error guardando usuario {user_id}: {e}")

async def update_email(user_id, email):
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

# --- FUNCIONES DE CÉLULAS Y HIVE ---

async def create_cell_db(owner_id, cell_name):
    global r
    if not r: return None
    cell_id = f"cell:{owner_id}:{int(datetime.now().timestamp())}"
    
    cell_data = {
        "id": cell_id,
        "name": cell_name,
        "owner": owner_id,
        "members": [owner_id],
        "synergy": 0.0,
        "work_today": 0.0
    }
    
    # Guardar metadata de la célula
    await r.set(cell_id, json.dumps(cell_data))
    # Indexar miembro
    await r.sadd(f"cell_members:{cell_id}", owner_id)
    return cell_id

async def get_hive_global():
    global r
    if not r: return {"level": 1, "health": 100, "work_today": 0}
    try:
        return await r.hgetall("hive:global")
    except:
        return {"level": 1, "health": 100, "work_today": 0}

async def update_hive_global(work_amount):
    global r
    if not r: return
    try:
        # Incrementar trabajo hoy
        await r.hincrbyfloat("hive:global", "work_today", work_amount)
        # Lógica simple de nivel
        stats = await r.hgetall("hive:global")
        work = float(stats.get("work_today", 0))
        level = int(stats.get("level", 1))
        
        if work > level * 1000:
            await r.hincrby("hive:global", "level", 1)
            await r.hset("hive:global", "work_today", 0) # Reset ciclo
            await r.hincrby("hive:global", "health", 5) # Curar Hive
    except Exception as e:
        logger.error(f"Error update hive: {e}")
