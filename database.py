import json
import os
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_FILE = "users_db.json"
logger = logging.getLogger(__name__)

# Estructura de usuario por defecto
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

# --- FUNCIONES DE COMPATIBILIDAD CON TU MAIN.PY ---
# Estas son las que faltaban y causaron el crash

async def init_db():
    """Inicializa la base de datos (crea el archivo si no existe)"""
    if not os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "w") as f:
                json.dump({}, f)
            logger.info("✅ Base de datos creada exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error creando DB: {e}")
    else:
        logger.info("✅ Base de datos encontrada.")

async def close_db():
    """Cierra la conexión (en JSON no es necesario, pero el main lo pide)"""
    logger.info("🔒 Conexión a DB cerrada (Simulado).")

# --- FUNCIONES DE LÓGICA DE USUARIOS ---

async def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando DB: {e}")
        return {}

async def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error(f"Error guardando DB: {e}")

async def add_user(user_id, first_name, username, referred_by=None):
    db = await load_db()
    uid = str(user_id)
    
    if uid not in db:
        new_user = DEFAULT_USER.copy()
        new_user.update({
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "referred_by": referred_by
        })
        db[uid] = new_user
        
        # Procesar referido
        if referred_by and str(referred_by) in db:
            if uid not in db[str(referred_by)]["referrals"]:
                db[str(referred_by)]["referrals"].append(uid)
                # Bonus al referidor
                db[str(referred_by)]["tokens"] += 50
        
        await save_db(db)
        return True
    else:
        # Update last active
        db[uid]["last_active"] = datetime.now().isoformat()
        await save_db(db)
        return False

async def update_email(user_id, email):
    db = await load_db()
    uid = str(user_id)
    if uid in db:
        db[uid]["email"] = email
        await save_db(db)

async def get_user(user_id):
    db = await load_db()
    return db.get(str(user_id))

# Función extra para compatibilidad futura
async def add_referral(user_id, referrer_id):
    # Esta función ya está integrada en add_user, pero la dejamos por si acaso
    pass
