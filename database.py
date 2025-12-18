import json
import logging
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, List, Any

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (HIVE CORE V201)
# ==============================================================================

logger = logging.getLogger("HiveDatabase")
logger.setLevel(logging.INFO)

ENV_REDIS_URL = os.getenv("REDIS_URL")
r: Optional[redis.Redis] = None

# --- ARQUETIPO DEL ORGANISMO (USUARIO) ---
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    # ECONOMÍA
    "nectar": 0.0,            # Saldo Líquido
    "tokens_locked": 0.0,     # Vesting
    "usd_balance": 0.00,      # CPA Real
    # BIOLOGÍA
    "role": "LARVA",
    "role_xp": 0.0,
    "energy": 300,
    "max_energy": 300,
    "oxygen": 100.0,
    "last_pulse": 0,
    # ANTI-FRAUDE
    "entropy_trace": [],
    "fraud_score": 0,
    "ban_status": False,
    # SOCIAL
    "cell_id": None,
    "referrals": [],
    "referred_by": None,
    "swarm_power": 1.0,
    # META
    "joined_at": "",
    "is_premium": False
}

DEFAULT_CELL = {
    "id": "", "owner_id": 0, "name": "", "members": [], 
    "synergy_level": 1.0, "total_xp": 0.0, "created_at": ""
}

# --- MOTOR DE CONEXIÓN ---

async def init_db():
    global r
    if not ENV_REDIS_URL:
        logger.critical("❌ ERROR: REDIS_URL no encontrada.")
        return
    try:
        r = redis.from_url(ENV_REDIS_URL, decode_responses=True)
        await r.ping()
        logger.info("✅ REDIS CONECTADO (SISTEMA DE MEMORIA ACTIVO)")
    except Exception as e:
        logger.error(f"❌ FALLO REDIS: {e}")
        r = None

async def close_db():
    if r: await r.aclose()

# --- GESTIÓN DE USUARIOS ---

async def get_user(user_id: int) -> Optional[Dict]:
    if not r: return None
    key = f"user:{user_id}"
    data = await r.get(key)
    if data:
        user = json.loads(data)
        # Migración al vuelo
        for k, v in DEFAULT_USER.items():
            if k not in user: user[k] = v
        return user
    return None

async def create_user(user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
    if not r: return False
    key = f"user:{user_id}"
    if await r.exists(key): return False

    new_user = DEFAULT_USER.copy()
    new_user.update({
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "joined_at": datetime.now().isoformat(),
        "last_pulse": time.time(),
        "referred_by": referrer_id
    })
    await r.set(key, json.dumps(new_user))
    
    # Procesar Referido
    if referrer_id:
        await _process_referral_bonus(referrer_id, user_id)
    return True

async def save_user(user_id: int, data: Dict):
    if r: await r.set(f"user:{user_id}", json.dumps(data))

async def delete_user(user_id: int):
    """BORRADO TOTAL: Usado para el comando /reset"""
    if r: 
        await r.delete(f"user:{user_id}")
        logger.info(f"🗑️ USUARIO {user_id} ELIMINADO (RESET)")

async def update_email(user_id: int, email: str):
    user = await get_user(user_id)
    if user:
        user['email'] = email
        await save_user(user_id, user)

# --- GESTIÓN DE CÉLULAS ---

async def create_cell(owner_id: int, name: str) -> Optional[str]:
    if not r: return None
    cell_id = f"cell:{owner_id}:{int(time.time())}"
    cell_data = DEFAULT_CELL.copy()
    cell_data.update({
        "id": cell_id, "owner_id": owner_id, "name": name, 
        "members": [owner_id], "created_at": datetime.now().isoformat()
    })
    await r.set(cell_id, json.dumps(cell_data))
    return cell_id

async def get_cell(cell_id: str) -> Optional[Dict]:
    if not r or not cell_id: return None
    data = await r.get(cell_id)
    return json.loads(data) if data else None

async def update_cell(cell_id: str, data: Dict):
    if r: await r.set(cell_id, json.dumps(data))

# --- INTERNOS ---

async def _process_referral_bonus(referrer_id: int, child_id: int):
    if not r: return
    ref_key = f"user:{referrer_id}"
    data = await r.get(ref_key)
    if data:
        parent = json.loads(data)
        if child_id not in parent.get("referrals", []):
            parent["referrals"].append(child_id)
            parent["nectar"] += 50.0 # Bono por reclutar
            await r.set(ref_key, json.dumps(parent))
