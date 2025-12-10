import os
import logging
import asyncpg

# Configuración de Logs
logger = logging.getLogger("Hive.DB")

DATABASE_URL = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    """Inicia la conexión y crea las tablas."""
    global pool
    if not DATABASE_URL:
        logger.error("❌ ERROR: No hay DATABASE_URL en las variables de entorno.")
        return

    try:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=5, max_size=20)
        logger.info("✅ Base de Datos Conectada.")
        
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    email TEXT,
                    balance_usd NUMERIC(10, 4) DEFAULT 0.0,
                    balance_hive BIGINT DEFAULT 0,
                    api_gate_passed BOOLEAN DEFAULT FALSE,
                    referrer_id BIGINT,
                    referrals_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
    except Exception as e:
        logger.critical(f"❌ ERROR CRÍTICO DB: {e}")

async def close_db():
    global pool
    if pool:
        await pool.close()
        logger.info("💤 Base de Datos Cerrada.")

async def add_user(user_id, first_name, username, referrer_id=None):
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, first_name, username, referrer_id) 
                VALUES ($1, $2, $3, $4) 
                ON CONFLICT (user_id) DO NOTHING
            """, user_id, first_name, username, referrer_id)
            return True
    except Exception as e:
        logger.error(f"Error add_user: {e}")
        return False

async def update_email(user_id, email):
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET email = $1 WHERE user_id = $2", email, user_id)
            return True
    except Exception as e:
        logger.error(f"Error update_email: {e}")
        return False

async def delete_user(user_id):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
    except Exception:
        pass
