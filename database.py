import json
import logging
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, List, Any

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (HIVE MEMORY)
# ==============================================================================

logger = logging.getLogger("HiveDatabase")
logger.setLevel(logging.INFO)

# La URL de Redis debe venir del entorno
ENV_REDIS_URL = os.getenv("REDIS_URL")

# Cliente Global
r: Optional[redis.Redis] = None

# --- ARQUETIPO DEL ORGANISMO (USUARIO) ---
DEFAULT_USER = {
    # 1. IDENTIDAD
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,              # Vital para CPA
    "joined_at": "",
    "language": "es",
    
    # 2. ECONOMÍA DUAL
    "nectar": 500.0,            # Saldo Líquido (Moneda interna)
    "tokens_locked": 0.0,       # Saldo Bloqueado (Vesting)
    "usd_balance": 0.00,        # Saldo Real (Ganado en Tiers)
    
    # 3. ESTADO BIOLÓGICO (FACTOR PANDORA)
    "role": "LARVA",            # Larva -> Obrero -> Explorador -> Guardián -> Nodo -> Génesis
    "role_xp": 0.0,             # Experiencia
    "energy": 500,              # Energía actual
    "max_energy": 500,          # Capacidad máxima
    "oxygen": 100.0,            # Eficiencia (0-100%)
    "last_pulse": 0,            # Timestamp última interacción
    "last_update_ts": 0,        # Timestamp última regeneración
    
    # 4. INTELIGENCIA DE ENJAMBRE
    "cell_id": None,            # ID de la Célula
    "referrals": [],            # Hijos directos
    "referred_by": None,        # Padre
    "swarm_power": 1.0,         # Multiplicador calidad
    
    # 5. SEGURIDAD (ENTROPY)
    "entropy_trace": [],        # Historial de timestamps
    "fraud_score": 0,           # 0-100
    "ban_status": False,
    
    # 6. META-GAME
    "streak_days": 0,
    "is_premium": False
}

# --- ARQUETIPO DE LA CÉLULA ---
DEFAULT_CELL = {
    "id": "",
    "owner_id": 0,
    "name": "",
    "members": [],
    "synergy_level": 1.0,       # Multiplicador grupal
    "total_xp": 0.0,
    "created_at": ""
}

# ==============================================================================
# CONEXIÓN Y GESTIÓN
# ==============================================================================

async def init_db():
    global r
    if not ENV_REDIS_URL:
        logger.critical("❌ ERROR FATAL: REDIS_URL no encontrada.")
        return

    logger.info("🔌 Conectando al Núcleo de Memoria (Redis)...")
    try:
        r = redis.from_url(
            ENV_REDIS_URL, 
            decode_responses=True, 
            socket_timeout=10.0,
            socket_connect_timeout=10.0
        )
        await r.ping()
        logger.info("✅ CONEXIÓN ESTABLECIDA: SISTEMA PANDORA ONLINE")
    except Exception as e:
        logger.error(f"❌ FALLO CRÍTICO EN DB: {e}")
        r = None

async def close_db():
    global r
    if r:
        try:
            await r.aclose()
        except Exception as e:
            logger.error(f"Error cerrando DB: {e}")

# ==============================================================================
# LÓGICA DE USUARIOS
# ==============================================================================

async def get_user(user_id: int) -> Optional[Dict]:
    global r
    if not r: return None
    key = f"user:{user_id}"
    try:
        data = await r.get(key)
        if data:
            user = json.loads(data)
            # MIGRACIÓN AL VUELO: Asegurar campos
            needs_save = False
            for k, v in DEFAULT_USER.items():
                if k not in user:
                    user[k] = v
                    needs_save = True
            if needs_save:
                await r.set(key, json.dumps(user))
            return user
        return None
    except Exception as e:
        logger.error(f"Error recuperando usuario {user_id}: {e}")
        return None

async def create_user(user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
    global r
    if not r: return False
    key = f"user:{user_id}"
    
    exists = await r.exists(key)
    if exists: return False

    new_user = DEFAULT_USER.copy()
    new_user.update({
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "joined_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "last_pulse": time.time(),
        "last_update_ts": time.time(),
        "referred_by": referrer_id
    })
    
    await r.set(key, json.dumps(new_user))
    
    # Procesar Viralidad
    if referrer_id and referrer_id != user_id:
        await _process_referral_bonus(referrer_id, user_id)
        
    return True

async def save_user(user_id: int, data: Dict):
    if r: await r.set(f"user:{user_id}", json.dumps(data))

async def update_email(user_id: int, email: str):
    user = await get_user(user_id)
    if user:
        user['email'] = email
        await save_user(user_id, user)

# ==============================================================================
# LÓGICA DE CÉLULAS
# ==============================================================================

async def create_cell(owner_id: int, name: str) -> Optional[str]:
    global r
    if not r: return None
    cell_id = f"cell:{owner_id}:{int(time.time())}"
    
    cell_data = DEFAULT_CELL.copy()
    cell_data.update({
        "id": cell_id,
        "owner_id": owner_id,
        "name": name,
        "members": [owner_id],
        "created_at": datetime.now().isoformat()
    })
    
    await r.set(cell_id, json.dumps(cell_data))
    return cell_id

async def get_cell(cell_id: str) -> Optional[Dict]:
    if not r or not cell_id: return None
    data = await r.get(cell_id)
    return json.loads(data) if data else None

async def update_cell(cell_id: str, data: Dict):
    if r: await r.set(cell_id, json.dumps(data))

async def join_cell(user_id: int, cell_id: str) -> bool:
    cell = await get_cell(cell_id)
    if cell and user_id not in cell['members']:
        cell['members'].append(user_id)
        # Sinergia: +5% por miembro, tope x2.5
        count = len(cell['members'])
        cell['synergy_level'] = min(2.5, 1.0 + (count * 0.05))
        await update_cell(cell_id, cell)
        return True
    return False

# ==============================================================================
# VIRALIDAD
# ==============================================================================

async def _process_referral_bonus(referrer_id: int, child_id: int):
    global r
    if not r: return
    ref_key = f"user:{referrer_id}"
    data_raw = await r.get(ref_key)
    if data_raw:
        parent = json.loads(data_raw)
        if child_id not in parent.get("referrals", []):
            parent["referrals"].append(child_id)
            parent["nectar"] = float(parent.get("nectar", 0)) + 50.0
            await r.set(ref_key, json.dumps(parent))
