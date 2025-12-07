import os
import logging
import json
import time
import random
import hashlib
import asyncpg
from typing import Optional, Dict, Any

# Configuración de Logs
logger = logging.getLogger("Hive.DB")

# Variable global para la piscina de conexiones
db_pool: Optional[asyncpg.Pool] = None

# Configuración de Regiones (Para el Geo-Scanner)
REGION_DATA = {
    "TIER_1": {"countries": ["US", "GB", "DE", "CA", "AU"], "cap": 850.0, "flag": "💎"},
    "TIER_2": {"countries": ["ES", "MX", "BR", "IT", "FR"], "cap": 320.0, "flag": "🥇"},
    "TIER_3": {"countries": [], "cap": 105.0, "flag": "🥈"},
}

async def init_db(database_url):
    """Inicializa la conexión a la base de datos de forma robusta."""
    global db_pool
    if not database_url:
        logger.error("❌ NO HAY DATABASE_URL. EL SISTEMA NO GUARDARÁ DATOS.")
        return

    # Creamos un Pool de conexiones (Vital para 200k usuarios)
    try:
        db_pool = await asyncpg.create_pool(database_url, min_size=5, max_size=20)
        
        async with db_pool.acquire() as conn:
            # Tabla de Usuarios (Optimizada con Índices)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    email TEXT,
                    referrer_id BIGINT,
                    rank TEXT DEFAULT 'LARVA',
                    balance_usd DOUBLE PRECISION DEFAULT 0.0,
                    balance_hive DOUBLE PRECISION DEFAULT 0.0,
                    country_code TEXT DEFAULT 'UNK',
                    region_tier TEXT DEFAULT 'TIER_3',
                    is_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """)
            
            # Tabla P2P (Mercado)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS p2p_market (
                    id SERIAL PRIMARY KEY,
                    seller_id BIGINT,
                    amount_hive DOUBLE PRECISION,
                    price_usd DOUBLE PRECISION,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Tabla de Seguridad (Anti-Fraude Fotos)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS security_hashes (
                    hash_id TEXT PRIMARY KEY,
                    user_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
        logger.info("✅ BASE DE DATOS TITÁN CONECTADA Y OPTIMIZADA.")
    except Exception as e:
        logger.critical(f"❌ ERROR CRÍTICO DB: {e}")

async def get_user(tg_id: int):
    """Obtiene datos del usuario super rápido."""
    if not db_pool: return {}
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        return dict(row) if row else {}

async def upsert_user(user, referrer_id=None):
    """Registra o actualiza usuario e incrementa contadores."""
    if not db_pool: return
    
    # Lógica Geo-Scanner
    lang = user.language_code or "en"
    country = lang.split("-")[-1].upper() if "-" in lang else lang.upper()
    tier = "TIER_3"
    for k, v in REGION_DATA.items():
        if country in v["countries"]:
            tier = k
            break
            
    async with db_pool.acquire() as conn:
        # Insertar o no hacer nada si ya existe (muy eficiente)
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, referrer_id, country_code, region_tier)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name
        """, user.id, user.first_name, referrer_id, country, tier)
        
        # Pagar referido si corresponde
        if referrer_id and referrer_id != user.id:
            await conn.execute("UPDATE users SET balance_hive = balance_hive + 200 WHERE telegram_id=$1", referrer_id)

async def modify_balance(tg_id, usd=0.0, hive=0.0):
    """Mueve el dinero de forma segura."""
    if not db_pool: return
    async with db_pool.acquire() as conn:
        if usd: await conn.execute("UPDATE users SET balance_usd = balance_usd + $1 WHERE telegram_id=$2", usd, tg_id)
        if hive: await conn.execute("UPDATE users SET balance_hive = balance_hive + $1 WHERE telegram_id=$2", hive, tg_id)

async def check_duplicate_image(img_bytes, user_id):
    """Sistema de seguridad básico anti-fraude."""
    if not db_pool: return False
    # Usamos MD5 simple para velocidad en MVP. En escala real usaríamos pHash en worker.
    img_hash = hashlib.md5(img_bytes).hexdigest()
    async with db_pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM security_hashes WHERE hash_id=$1", img_hash)
        if exists: return True
        await conn.execute("INSERT INTO security_hashes (hash_id, user_id) VALUES ($1, $2)", img_hash, user_id)
    return False

async def get_p2p_orders():
    """Trae las ofertas del mercado."""
    if not db_pool: return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM p2p_market WHERE active=TRUE ORDER BY created_at DESC LIMIT 5")
        return [dict(r) for r in rows]
