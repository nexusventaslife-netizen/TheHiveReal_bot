import json
import os
from datetime import datetime

# Archivo donde se guardan los datos (JSON local)
DB_FILE = "hive_database.json"

# Estructura inicial si el archivo no existe
DEFAULT_DB = {
    "users": {},
    "stats": {"total_users": 0, "total_paid": 0.0}
}

def load_db():
    """Carga la base de datos"""
    if not os.path.exists(DB_FILE):
        return DEFAULT_DB
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_DB

def save_db(data):
    """Guarda los cambios"""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

async def add_user(user_id, first_name, username):
    """Registra un usuario nuevo si no existe"""
    db = load_db()
    uid = str(user_id)
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": user_id,
            "name": first_name,
            "username": username,
            "email": None,
            "country": "GL",
            "joined_at": datetime.now().isoformat(),
            "balance_hive": 100, # Bono inicial
            "balance_usd": 0.0,
            "referrals": [],     # Lista de gente invitada
            "referred_by": None  # Quién lo invitó
        }
        db["stats"]["total_users"] += 1
        save_db(db)
        return True # Nuevo usuario
    return False # Usuario ya existía

async def update_email(user_id, email):
    """Guarda el email del usuario"""
    db = load_db()
    uid = str(user_id)
    if uid in db["users"]:
        db["users"][uid]["email"] = email
        save_db(db)

async def get_user(user_id):
    """Devuelve los datos de un usuario"""
    db = load_db()
    return db["users"].get(str(user_id))

async def add_referral(new_user_id, referrer_id):
    """Conecta a un usuario nuevo con su jefe de colmena"""
    db = load_db()
    new_uid = str(new_user_id)
    ref_uid = str(referrer_id)
    
    # Validaciones básicas
    if new_uid in db["users"] and ref_uid in db["users"]:
        # Evitar auto-referido
        if new_uid == ref_uid: return 
        
        # Asignar padre
        if db["users"][new_uid]["referred_by"] is None:
            db["users"][new_uid]["referred_by"] = ref_uid
            
            # Asignar hijo al padre
            if new_uid not in db["users"][ref_uid]["referrals"]:
                db["users"][ref_uid]["referrals"].append(new_uid)
                # Dar bono al padre (ej: 50 HIVE puntos)
                db["users"][ref_uid]["balance_hive"] += 50
                
            save_db(db)
