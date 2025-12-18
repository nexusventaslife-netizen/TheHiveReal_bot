import json
import logging
import os
import redis.asyncio as redis
from datetime import datetime

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

# Lee la URL de Redis del entorno
ENV_REDIS_URL = os.getenv("REDIS_URL", "rediss://default:AbEBAAIncDIxNTYwNjk5MzkwODc0OGE2YWUyNmJkMmI1N2M4MmNiM3AyNDUzMTM@brave-hawk-45313.upstash.io:6379")

# Cliente Global
r = None

# --- ESTRUCTURA DE USUARIO (HIVE + PANDORA MERGE) ---
# Se han agregado todos los campos necesarios para el motor psicológico
DEFAULT_USER = {
    # --- Identidad ---
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "joined_at": "",
    "last_active": "",
    
    # --- Economía Hive ---
    "nectar": 500.0,      # Balance Líquido
    "usd_balance": 0.00,  # Saldo Real USD
    
    # --- Economía Pandora (Hard Money) ---
    "locked_balance": 0.0, # Saldo bloqueado (Vesting)
    "vesting_until": "",   # Fecha de liberación
    
    # --- Sistema de Referidos (Viralidad + Calidad) ---
    "referrals": [],
    "referred_by": None,
    "ref_quality_score": 0, # Puntos por calidad de referidos
    
    # --- Gamificación & Rol (Psych-Engine) ---
    "role": "Larva",         # Larva -> Obrero -> Explorador -> Guardián -> Nodo -> Reina
    "role_decay": 0,         # Contador de inactividad
    "hidden_progress": 0.0,  # Barra de experiencia oculta
    "behavior_score": 100.0, # Puntuación de comportamiento (Anti-bot)
    "spam_score": 0.0,
    
    # --- Engagement ---
    "streak_days": 0,
    "last_streak_date": "",
    "energy": 500,           # Max Energy base
    "max_energy": 500,
    "lucky_tickets": 0,
    "is_premium": False,
    
    # --- Social (Células/Guilds) ---
    "cell_id": None,         # ID de la Célula a la que pertenece
    
    # --- Anti-Fraude ---
    "task_timestamps": [],
    "fraud_score": 0,
    "ban_status": False,
    "last_update_ts": 0
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
        # Inicializar variables globales de la Hive si no existen
        if not await r.exists("hive:global:level"):
            await r.set("hive:global:level", 1)
        if not await r.exists("hive:global:health"):
            await r.set("hive:global:health", 100)
            
        logger.info("✅ CONEXIÓN REDIS UPSTASH EXITOSA (Pandora Engine Ready)")
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
    """Agrega usuario a Redis de forma segura fusionando datos nuevos"""
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
                "referred_by": referred_by,
                "last_update_ts": datetime.now().timestamp()
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
                            # Bono por referido simple (Solo Néctar, poco para evitar granjas)
                            parent_data["nectar"] = float(parent_data.get("nectar", 500)) + 50.0
                            await r.set(ref_key, json.dumps(parent_data))
            
            logger.info(f"🆕 Nuevo Usuario (Pandora DNA): {user_id}")
            return True
        else:
            # Actualizar last_active y migrar estructura si es vieja
            raw_data = await r.get(key)
            if raw_data:
                data = json.loads(raw_data)
                data["last_active"] = datetime.now().isoformat()
                
                # Migración dinámica: Asegurar que los campos nuevos de Pandora existan
                changed = False
                for k, v in DEFAULT_USER.items():
                    if k not in data:
                        data[k] = v
                        changed = True
                
                if changed:
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

# --- FUNCIONES DE CÉLULAS (GUILDS) ---
async def create_cell(owner_id, cell_name=None):
    global r
    if not r: return None
    cell_id = f"cell:{owner_id}:{int(datetime.now().timestamp())}"
    cell_data = {
        "id": cell_id,
        "owner": owner_id,
        "name": cell_name or f"Hive Cell {owner_id}",
        "members": [owner_id],
        "work_today": 0.0,
        "synergy_level": 1.0
    }
    await r.set(cell_id, json.dumps(cell_data))
    # Actualizar usuario
    u = await get_user(owner_id)
    u['cell_id'] = cell_id
    await r.set(f"user:{owner_id}", json.dumps(u))
    return cell_id

async def get_cell(cell_id):
    global r
    if not r or not cell_id: return None
    data = await r.get(cell_id)
    return json.loads(data) if data else None

async def update_global_hive(work_amount):
    """Actualiza la salud y nivel global de la Hive"""
    global r
    if not r: return
    try:
        # Incrementar trabajo acumulado
        total_work = await r.incrbyfloat("hive:global:work", float(work_amount))
        level = float(await r.get("hive:global:level") or 1)
        
        # Lógica de subida de nivel global
        if total_work > level * 10000:
            await r.incr("hive:global:level")
            await r.set("hive:global:health", 100) # Restaurar salud al subir nivel
            
    except Exception as e:
        logger.error(f"Error hive tick: {e}")

async def save_db(data=None):
    pass
