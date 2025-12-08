import os
import logging
import asyncpg
import redis.asyncio as redis
from datetime import datetime

# Configuración de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Hive.DB")

# Variables Globales
DB_POOL = None
REDIS_CLIENT = None

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def init_db():
    """Inicializa la conexión a PostgreSQL y Redis."""
    global DB_POOL, REDIS_CLIENT
    
    # 1. Conectar PostgreSQL
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL no encontrada.")
        raise ValueError("DATABASE_URL env var is missing")
    
    try:
        DB_POOL = await asyncpg.create_pool(DATABASE_URL)
        logger.info("✅ PostgreSQL Pool creado exitosamente.")
        
        # Crear tablas si no existen
        async with DB_POOL.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance_usd NUMERIC(10, 4) DEFAULT 0.0,
                    balance_hive NUMERIC(10, 4) DEFAULT 0.0,
                    email TEXT,
                    gate_passed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    referrer_id BIGINT
                );
                
                CREATE TABLE IF NOT EXISTS leads_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    email TEXT UNIQUE,
                    source TEXT DEFAULT 'bot_start',
                    captured_at TIMESTAMP DEFAULT NOW()
                );
            """)
    except Exception as e:
        logger.error(f"❌ Error conectando a Postgres: {e}")
        raise e

    # 2. Conectar Redis
    try:
        REDIS_CLIENT = redis.from_url(REDIS_URL, decode_responses=True)
        await REDIS_CLIENT.ping()
        logger.info("✅ REDIS CONECTADO EN DATABASE.")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo conectar a Redis: {e}")

async def close_db():
    """Cierra las conexiones a la DB y Redis limpiamente."""
    global DB_POOL, REDIS_CLIENT
    
    if DB_POOL:
        await DB_POOL.close()
        logger.info("🔒 PostgreSQL Pool cerrado.")
    
    if REDIS_CLIENT:
        await REDIS_CLIENT.close()
        logger.info("🔒 Redis Client cerrado.")

# --- FUNCIONES DE USUARIO ---

async def get_user(user_id: int):
    async with DB_POOL.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

async def add_user(user_id: int, username: str, first_name: str, referrer_id: int = None):
    async with DB_POOL.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name, referrer_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING
            """, user_id, username, first_name, referrer_id)
        except Exception as e:
            logger.error(f"Error creando usuario {user_id}: {e}")

async def add_lead(user_id: int, email: str):
    """Guarda el email en la tabla de leads y actualiza el usuario."""
    async with DB_POOL.acquire() as conn:
        try:
            # 1. Guardar en leads_harvest
            await conn.execute("""
                INSERT INTO leads_harvest (user_id, email)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET email = EXCLUDED.email
            """, user_id, email)
            
            # 2. Actualizar tabla users
            await conn.execute("""
                UPDATE users SET email = $1 WHERE user_id = $2
            """, email, user_id)
            return True
        except Exception as e:
            logger.error(f"Error guardando lead {email}: {e}")
            return False

async def update_user_gate_status(user_id: int, status: bool):
    """Marca si el usuario pasó el link de publicidad."""
    async with DB_POOL.acquire() as conn:
        await conn.execute("UPDATE users SET gate_passed = $1 WHERE user_id = $2", status, user_id)

async def get_balance(user_id: int):
    """Retorna (balance_usd, balance_hive)."""
    async with DB_POOL.acquire() as conn:
        row = await conn.fetchrow("SELECT balance_usd, balance_hive FROM users WHERE user_id = $1", user_id)
        if row:
            return row['balance_usd'], row['balance_hive']
        return 0.0, 0.0

async def add_hive_points(user_id: int, amount: float):
    async with DB_POOL.acquire() as conn:
        await conn.execute("UPDATE users SET balance_hive = balance_hive + $1 WHERE user_id = $2", amount, user_id)
