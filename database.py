import json
import logging
import os
import redis.asyncio as redis
from datetime import datetime

# --- CONFIGURACIÓN ---
logger = logging.getLogger(__name__)

# Lee la URL de Redis del entorno.
ENV_REDIS_URL = os.getenv("REDIS_URL")

# Cliente Global
r = None

# Estructura Base (ACTUALIZADA V157.0 + SWARM RESONANCE)
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "nectar": 500.0,      # Moneda Interna (HIVE)
    "usd_balance": 0.00,  # Saldo Real
    "skills": [],         # Inventario
    "joined_at": "",
    "referrals": [],      # Lista de IDs
    "referred_by": None,
    "last_active": "",
    # --- ENGANCHE ---
    "streak_days": 0,            
    "last_streak_date": "",      
    "energy": 100,               
    "max_energy": 500,    # [NUEVO] Permitir upgrades de capacidad
    "lucky_tickets": 0,          
    "is_premium": False,
    # --- RLE DEFENSE & SWARM ALGO ---
    "fraud_score": 0,           
    "task_timestamps": [],      
    "ip_address_hash": None,    
    "ban_status": False,        
    "tokens_locked": 0.0,
    # --- [NUEVO] METRICAS DISRUPTIVAS ---
    "click_intervals": [],      # Para analizar ritmo humano
    "resonance_level": 1.0      # Multiplicador basado en calidad de equipo
}

# --- FUNCIONES DE SISTEMA ---

async def init_db():
    """Conecta a Redis al iniciar validando que la URL exista"""
    global r
    
    if not ENV_REDIS_URL:
        logger.critical("❌ ERROR FATAL: La variable de entorno 'REDIS_URL' no está configurada.")
        r = None
        return

    try:
        r = redis.from_url(
            ENV_REDIS_URL, 
            decode_responses=True, 
            socket_timeout=5.0,
            socket_connect_timeout=5.0
        )
        await r.ping()
        # [NUEVO] Inicializar variables globales si no existen
        if not await r.exists("global:pulse_multiplier"):
            await r.set("global:pulse_multiplier", "1.0")
        
        logger.info("✅ CONEXIÓN REDIS EXITOSA (V157.0)")
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
    if not r: 
        logger.warning("⚠️ Intento de escritura sin conexión a Redis")
        return False
    
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
                            parent_data["nectar"] = float(parent_data.get("nectar", 500)) + 50.0
                            await r.set(ref_key, json.dumps(parent_data))
            
            logger.info(f"🆕 Nuevo Usuario: {user_id}")
            return True
        else:
            # Actualizar last_active sin borrar datos existentes
            raw_data = await r.get(key)
            if raw_data:
                data = json.loads(raw_data)
                data["last_active"] = datetime.now().isoformat()
                
                # MIGRACIÓN SEGURA: Asegurar campos nuevos
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

# [NUEVO] Funciones Globales para Algoritmo Disruptivo
async def get_global_pulse():
    global r
    if not r: return 1.0
    try:
        val = await r.get("global:pulse_multiplier")
        return float(val) if val else 1.0
    except: return 1.0
