import json
import logging
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, List, Any

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS ESTRUCTURAL (V200.0 - ULTRA EXPANDED)
# ==============================================================================

logger = logging.getLogger("HiveDatabase")
logger.setLevel(logging.INFO)

# La URL de Redis debe venir del entorno (Render/Docker)
ENV_REDIS_URL = os.getenv("REDIS_URL")

# Cliente Global
r: Optional[redis.Redis] = None

# --- ARQUETIPO DEL ORGANISMO (USUARIO) ---
# Esta estructura es la evolución final. Contiene métricas financieras y biológicas.
DEFAULT_USER = {
    # 1. IDENTIDAD
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,              # Vital para CPA
    "joined_at": "",
    "language": "es",
    
    # 2. ECONOMÍA DUAL (LIQUIDEZ vs VESTING)
    "nectar": 500.0,            # Saldo Líquido (Moneda interna para upgrades)
    "tokens_locked": 0.0,       # Saldo Bloqueado (Airdrop futuro - Retention Hook)
    "usd_balance": 0.00,        # Saldo Real (Ganado en Tiers 2 y 3)
    "wallet_address": None,     # Para retiros
    
    # 3. ESTADO BIOLÓGICO (FACTOR X - PANDORA)
    "role": "LARVA",            # Jerarquía: Larva -> Obrero -> Explorador -> Guardián -> Nodo -> Génesis
    "role_xp": 0.0,             # Experiencia acumulada (distinta al dinero)
    "energy": 500,              # Energía actual
    "max_energy": 500,          # Capacidad máxima (Sube con el Rol)
    "oxygen": 100.0,            # Eficiencia (0-100%). Baja con inactividad.
    "last_pulse": 0,            # Timestamp de la última interacción (Heartbeat)
    
    # 4. INTELIGENCIA DE ENJAMBRE (SOCIAL)
    "cell_id": None,            # ID de la Célula (Squad) actual
    "referrals": [],            # Lista de IDs de hijos directos
    "referred_by": None,        # ID del padre
    "swarm_power": 1.0,         # Multiplicador basado en la calidad de los hijos
    
    # 5. SEGURIDAD & ANTI-FRAUDE (RLE + ENTROPY)
    "entropy_trace": [],        # Historial de los últimos 20 timestamps de clic (Análisis Matemático)
    "fraud_score": 0,           # 0-100. >80 es Ban automático.
    "ban_status": False,
    "warning_count": 0,
    
    # 6. META-GAME & ENGANCHE
    "streak_days": 0,           # Días consecutivos entrando
    "last_streak_date": "",
    "is_premium": False,        # Membresía Reina (Paga)
    "inventory": []             # Items futuros
}

# --- ARQUETIPO DE LA CÉLULA (GUILD) ---
DEFAULT_CELL = {
    "id": "",
    "owner_id": 0,
    "name": "",
    "description": "Una colmena en crecimiento.",
    "members": [],              # Lista de IDs
    "synergy_level": 1.0,       # Multiplicador grupal (Base 1.0 + 0.05 por miembro)
    "total_xp": 0.0,            # XP acumulada de todos los miembros
    "daily_work": 0.0,          # Métricas diarias para leaderboards
    "created_at": "",
    "is_verified": False
}

# ==============================================================================
# MOTOR DE CONEXIÓN
# ==============================================================================

async def init_db():
    """Inicializa la conexión a Redis con reintentos y configuración de alto rendimiento."""
    global r
    
    if not ENV_REDIS_URL:
        logger.critical("❌ ERROR FATAL: REDIS_URL no encontrada en variables de entorno.")
        return

    logger.info("🔌 Conectando al Núcleo de Memoria (Redis)...")
    try:
        r = redis.from_url(
            ENV_REDIS_URL, 
            decode_responses=True, 
            socket_timeout=10.0,
            socket_connect_timeout=10.0,
            health_check_interval=30
        )
        await r.ping()
        
        # Inicializar Parámetros Globales del Juego si es el primer arranque
        if not await r.exists("global:hive_status"):
            await r.set("global:hive_status", "ONLINE")
            await r.set("global:total_mined", "0")
            await r.set("global:active_users", "0")
            
        logger.info("✅ CONEXIÓN ESTABLECIDA: SISTEMA PANDORA ONLINE")
    except Exception as e:
        logger.error(f"❌ FALLO CRÍTICO EN DB: {e}")
        r = None

async def close_db():
    global r
    if r:
        try:
            await r.aclose()
            logger.info("🔒 Conexión DB cerrada correctamente.")
        except Exception as e:
            logger.error(f"Error cerrando DB: {e}")

# ==============================================================================
# LÓGICA DE USUARIOS (CRUD + MIGRACIÓN)
# ==============================================================================

async def get_user(user_id: int) -> Optional[Dict]:
    """Recupera un usuario. Si la estructura cambió (nuevas features), migra los datos al vuelo."""
    global r
    if not r: return None
    key = f"user:{user_id}"
    
    try:
        data = await r.get(key)
        if data:
            user = json.loads(data)
            
            # MIGRACIÓN AL VUELO: Si agregamos nuevas features al código, 
            # los usuarios viejos no se rompen, se actualizan aquí.
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
    """Crea un nuevo organismo en la colmena."""
    global r
    if not r: return False
    
    key = f"user:{user_id}"
    
    # Usamos una transacción (pipeline) para asegurar consistencia
    async with r.pipeline() as pipe:
        try:
            exists = await r.exists(key)
            if exists: return False # Ya existe

            new_user = DEFAULT_USER.copy()
            new_user.update({
                "id": user_id,
                "first_name": first_name,
                "username": username,
                "joined_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "last_pulse": time.time(),
                "referred_by": referrer_id
            })
            
            # Guardar usuario
            pipe.set(key, json.dumps(new_user))
            
            # Incrementar contador global
            pipe.incr("global:total_users")
            
            # Lógica Viral: Si tiene padre, registrar la conexión
            if referrer_id and referrer_id != user_id:
                ref_key = f"user:{referrer_id}"
                # Nota: Necesitamos leer al padre fuera del pipe o asumir existencia.
                # Para simplificar en async, lo procesamos post-creación o usamos lógica separada.
                pass 

            await pipe.execute()
            
            # Proceso separado para el referido (para no bloquear creación)
            if referrer_id:
                await _process_referral_bonus(referrer_id, user_id)
                
            logger.info(f"✨ NUEVO ORGANISMO CREADO: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creando usuario {user_id}: {e}")
            return False

async def save_user(user_id: int, data: Dict):
    """Guarda el estado del usuario."""
    if r: await r.set(f"user:{user_id}", json.dumps(data))

async def update_email(user_id: int, email: str):
    """Actualiza email para validación CPA."""
    user = await get_user(user_id)
    if user:
        user['email'] = email
        await save_user(user_id, user)

# ==============================================================================
# LÓGICA DE CÉLULAS / ENJAMBRES (SQUAD SYSTEM)
# ==============================================================================

async def create_cell(owner_id: int, name: str) -> Optional[str]:
    """Crea una nueva célula con ID único."""
    global r
    if not r: return None
    
    # Generar ID único basado en tiempo y dueño
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
    await r.sadd("global:all_cells", cell_id) # Índice para búsquedas
    return cell_id

async def get_cell(cell_id: str) -> Optional[Dict]:
    if not r or not cell_id: return None
    data = await r.get(cell_id)
    return json.loads(data) if data else None

async def update_cell(cell_id: str, data: Dict):
    if r: await r.set(cell_id, json.dumps(data))

async def join_cell(user_id: int, cell_id: str) -> bool:
    """Añade usuario a célula y recalcula sinergia."""
    cell = await get_cell(cell_id)
    if cell and user_id not in cell['members']:
        cell['members'].append(user_id)
        # Sinergia: +5% por miembro, máximo x2.5 (30 miembros)
        count = len(cell['members'])
        cell['synergy_level'] = min(2.5, 1.0 + (count * 0.05))
        await update_cell(cell_id, cell)
        return True
    return False

# ==============================================================================
# SISTEMA VIRAL INTERNO
# ==============================================================================

async def _process_referral_bonus(referrer_id: int, child_id: int):
    """Otorga bonos y registra la genealogía."""
    global r
    if not r: return
    
    ref_key = f"user:{referrer_id}"
    data_raw = await r.get(ref_key)
    
    if data_raw:
        parent = json.loads(data_raw)
        
        # Evitar duplicados
        if child_id not in parent.get("referrals", []):
            parent["referrals"].append(child_id)
            
            # Bono inmediato de Néctar (Gasolina para el sistema)
            parent["nectar"] = float(parent.get("nectar", 0)) + 50.0
            
            # Subir Score de Enjambre (Calidad)
            parent["swarm_power"] = float(parent.get("swarm_power", 1.0)) + 0.01
            
            await r.set(ref_key, json.dumps(parent))
