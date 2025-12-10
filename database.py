import os
import logging
import asyncpg

logger = logging.getLogger("Hive.DB")
DATABASE_URL = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    global pool
    if not DATABASE_URL:
        logger.error("❌ NO DATABASE URL")
        return
    try:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    email TEXT,
                    balance_usd NUMERIC DEFAULT 0,
                    referrer_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
        logger.info("✅ DB Conectada.")
    except Exception as e:
        logger.error(f"❌ Error DB: {e}")

async def close_db():
    if pool: await pool.close()

async def add_user(user_id, first_name, username, referrer_id=None):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, first_name, username, referrer_id) 
                VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING
            """, user_id, first_name, username, referrer_id)
    except Exception: pass

async def update_email(user_id, email):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET email = $1 WHERE user_id = $2", email, user_id)
    except Exception: pass

async def delete_user(user_id):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
    except Exception: pass
