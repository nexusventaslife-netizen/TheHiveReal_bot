import json
import os
import logging
from datetime import datetime
import asyncio

# Configuración de Logs
logger = logging.getLogger(__name__)

# Nombre del archivo de base de datos
DB_FILE = "users_db.json"

# Variable en memoria para velocidad
_db_cache = {}

# Estructura de usuario por defecto (LA QUE TENÍAS ANTES)
DEFAULT_USER = {
    "id": 0,
    "first_name": "",
    "username": "",
    "email": None,
    "tokens": 100,
    "joined_at": "",
    "referrals": [],
    "referred_by": None,
    "wallet": {"btc": 0.0, "usd": 0.0},
    "last_active": ""
}

# ==========================================
# FUNCIONES OBLIGATORIAS PARA EL MAIN.PY
# (Sin esto, el servidor crashea)
# ==========================================

async def init_db():
    """Inicializa la DB al arrancar el servidor"""
    global _db_cache
    if not os.path.exists(DB_FILE):
        _db_cache = {}
        await save_db(_db_cache)
        logger.info("🆕 Base de datos creada desde cero.")
    else:
        _db_cache = await load_db()
        logger.info(f"✅ Base de datos cargada. Usuarios: {len(_db_cache)}")

async def close_db():
    """Cierra la DB al apagar el servidor"""
    global _db_cache
    await save_db(_db_cache)
    logger.info("🔒 Base de datos guardada y cerrada.")

# ==========================================
# FUNCIONES DE LÓGICA DE USUARIOS
# (Las que usa tu Bot Logic)
# ==========================================

async def load_db():
    """Lee el archivo JSON del disco"""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            content = f.read()
            if not content: return {}
            return json.loads(content)
    except Exception as e:
        logger.error(f"❌ Error cargando DB: {e}")
        return {}

async def save_db(data=None):
    """Escribe los datos en el disco"""
    global _db_cache
    if data is None: data = _db_cache
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Error guardando DB: {e}")

async def add_user(user_id, first_name, username, referred_by=None):
    """Registra usuario y maneja referidos"""
    global _db_cache
    uid = str(user_id)
    
    # Si la caché está vacía, intentamos cargar
    if not _db_cache:
        _db_cache = await load_db()
    
    if uid not in _db_cache:
        new_user = DEFAULT_USER.copy()
        new_user.update({
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "referred_by": referred_by
        })
        _db_cache[uid] = new_user
        
        # Lógica de Referidos
        if referred_by:
            rid = str(referred_by)
            if rid in _db_cache and rid != uid:
                if "referrals" not in _db_cache[rid]:
                    _db_cache[rid]["referrals"] = []
                
                if uid not in _db_cache[rid]["referrals"]:
                    _db_cache[rid]["referrals"].append(uid)
                    # Bono de 50 tokens al referidor
                    current_tokens = _db_cache[rid].get("tokens", 0)
                    _db_cache[rid]["tokens"] = current_tokens + 50
        
        await save_db(_db_cache)
        return True
    else:
        # Solo actualizamos última conexión
        _db_cache[uid]["last_active"] = datetime.now().isoformat()
        await save_db(_db_cache)
        return False

async def update_email(user_id, email):
    """Guarda el email"""
    global _db_cache
    uid = str(user_id)
    if uid in _db_cache:
        _db_cache[uid]["email"] = email
        await save_db(_db_cache)

async def get_user(user_id):
    """Devuelve datos del usuario"""
    global _db_cache
    if not _db_cache:
        _db_cache = await load_db()
    return _db_cache.get(str(user_id))

# Función extra de compatibilidad por si alguna versión vieja la llama
async def add_referral(user_id, referrer_id):
    # Esta lógica ya está dentro de add_user, pero la dejamos para que no rompa nada
    pass
