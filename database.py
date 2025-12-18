import json
import logging
import os
import redis.asyncio as redis
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (REDIS UPSTASH)
# =============================================================================
logger = logging.getLogger("HiveDatabase")

# Lee la URL de Redis del entorno
ENV_REDIS_URL = os.getenv("REDIS_URL", "rediss://default:AbEBAAIncDIxNTYwNjk5MzkwODc0OGE2YWUyNmJkMmI1N2M4MmNiM3AyNDUzMTM@brave-hawk-45313.upstash.io:6379")

# Cliente Global
r = None

# =============================================================================
# ESTRUCTURA MAESTRA DE USUARIO (V300.0 - FUSIÓN TOTAL)
# =============================================================================
# Aquí está TODO: Lo viejo (USD, Tareas) y lo nuevo (Roles, Células, Engine)
DEFAULT_USER = {
    # --- Identidad & Acceso ---
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "joined_at": "",
    "last_active": "",
    "last_update_ts": 0,
    
    # --- Economía Vieja (Legacy) ---
    "usd_balance": 0.00,        # Saldo en Dólares (Tasks)
    "pending_usd": 0.00,        # Saldo pendiente de aprobación
    
    # --- Economía Nueva (Pandora Hive) ---
    "nectar": 500.0,            # HIVE Líquido (Moneda interna)
    "locked_balance": 0.0,      # HIVE Bloqueado (Vesting/Hard Money)
    "vesting_until": "",        # Fecha de liberación
    
    # --- Gamificación & Roles (Jerarquía) ---
    "role": "Larva",            # Larva -> Obrero -> Explorador -> Guardián -> Nodo -> Reina
    "role_decay": 0,            # Contador de inactividad (Castigo)
    "hidden_progress": 0.0,     # XP Oculta (Factor X)
    "behavior_score": 100.0,    # Puntuación de comportamiento (0-100)
    
    # --- Energía & Minería ---
    "energy": 500,              # Energía actual
    "max_energy": 500,          # Capacidad máxima
    "mining_level": 1,          # Nivel del pico/tap
    
    # --- Social (Células/Guilds) ---
    "cell_id": None,            # ID de la Célula a la que pertenece
    "cell_role": "Member",      # Member / Leader
    
    # --- Sistema de Referidos (Viralidad) ---
    "referrals": [],            # Lista de IDs referidos
    "referred_by": None,        # Quién lo invitó
    "ref_quality_score": 0,     # Calidad de los referidos (Si trabajan o no)
    
    # --- Anti-Fraude & Seguridad ---
    "task_timestamps": [],      # Timestamps de tareas para detectar scripts
    "fraud_score": 0,           # Nivel de riesgo
    "ban_status": False,        # Si está baneado
    
    # --- Historial ---
    "streak_days": 0,           # Racha de días consecutivos
    "completed_tasks": 0,       # Total de tareas hechas
    "is_premium": False         # Membresía Reina pagada
}

# =============================================================================
# FUNCIONES DEL SISTEMA
# =============================================================================

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
        
        # Inicializar Estado Global de la Hive si no existe
        if not await r.exists("hive:global:level"):
            await r.set("hive:global:level", 1)
        if not await r.exists("hive:global:health"):
            await r.set("hive:global:health", 100)
        if not await r.exists("hive:global:work_total"):
            await r.set("hive:global:work_total", 0.0)
            
        logger.info("✅ BASE DE DATOS CONECTADA (Estructura Completa)")
    except Exception as e:
        logger.error(f"❌ FALLÓ CONEXIÓN REDIS: {e}")
        r = None

async def close_db():
    """Cierra la conexión al apagar"""
    global r
    if r:
        try:
            await r.aclose()
            logger.info("🔒 CONEXIÓN CERRADA")
        except Exception as e:
            logger.error(f"Error cerrando Redis: {e}")

# =============================================================================
# GESTIÓN DE USUARIOS
# =============================================================================

async def add_user(user_id, first_name, username, referred_by=None):
    """Crea o actualiza un usuario asegurando que tenga TODOS los campos nuevos"""
    global r
    if not r: return False
    
    uid = str(user_id)
    key = f"user:{uid}"
    
    try:
        exists = await r.exists(key)
        
        if not exists:
            # USUARIO NUEVO
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
            
            # Procesar Referido (Solo si es nuevo)
            if referred_by and str(referred_by) != uid:
                rid = str(referred_by)
                ref_key = f"user:{rid}"
                if await r.exists(ref_key):
                    raw_parent = await r.get(ref_key)
                    if raw_parent:
                        parent_data = json.loads(raw_parent)
                        if uid not in parent_data.get("referrals", []):
                            parent_data.setdefault("referrals", []).append(uid)
                            # Bono pequeño por invitación
                            parent_data["nectar"] = float(parent_data.get("nectar", 0)) + 50.0
                            await r.set(ref_key, json.dumps(parent_data))
            
            logger.info(f"🆕 Nuevo Usuario Registrado: {user_id}")
            return True
        else:
            # USUARIO EXISTENTE (MIGRACIÓN SILENCIOSA)
            # Esto asegura que si agregaste campos nuevos, los usuarios viejos los tengan
            raw_data = await r.get(key)
            if raw_data:
                data = json.loads(raw_data)
                data["last_active"] = datetime.now().isoformat()
                
                changed = False
                for k, v in DEFAULT_USER.items():
                    if k not in data:
                        data[k] = v
                        changed = True
                
                if changed:
                    await r.set(key, json.dumps(data))
                    logger.info(f"♻️ Usuario {user_id} migrado a nueva estructura.")
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
    global r
    if not r: return
    try:
        await r.set(f"user:{user_id}", json.dumps(data))
    except Exception as e:
        logger.error(f"Error guardando usuario {user_id}: {e}")

async def update_email(user_id, email):
    u = await get_user(user_id)
    if u:
        u["email"] = email
        await save_user(user_id, u)

# =============================================================================
# GESTIÓN DE CÉLULAS (NUEVO)
# =============================================================================

async def create_cell(owner_id, cell_name):
    global r
    if not r: return None
    cell_id = f"cell:{owner_id}:{int(datetime.now().timestamp())}"
    cell_data = {
        "id": cell_id,
        "owner": owner_id,
        "name": cell_name,
        "members": [owner_id],
        "work_today": 0.0,
        "synergy_level": 1.0,
        "created_at": datetime.now().isoformat()
    }
    await r.set(cell_id, json.dumps(cell_data))
    
    # Actualizar al dueño
    u = await get_user(owner_id)
    u['cell_id'] = cell_id
    u['cell_role'] = 'Leader'
    await save_user(owner_id, u)
    
    return cell_id

async def get_cell(cell_id):
    global r
    if not r or not cell_id: return None
    data = await r.get(cell_id)
    return json.loads(data) if data else None

# =============================================================================
# GESTIÓN DE HIVE GLOBAL
# =============================================================================

async def update_hive_global(work_amount):
    global r
    if not r: return
    try:
        total = await r.incrbyfloat("hive:global:work_total", float(work_amount))
        lvl = float(await r.get("hive:global:level") or 1)
        
        # Lógica de Nivel Global
        if total > lvl * 10000:
            await r.incr("hive:global:level")
            await r.set("hive:global:health", 100)
    except: pass

async def get_hive_global_stats():
    global r
    if not r: return {"level": 1, "health": 100, "work_total": 0}
    return {
        "level": await r.get("hive:global:level") or 1,
        "health": await r.get("hive:global:health") or 100,
        "work_total": await r.get("hive:global:work_total") or 0
    }
