import os
import logging
import asyncpg

# Configuración de Logs
logger = logging.getLogger("Hive.DB")

# URL de Conexión
DATABASE_URL = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    """
    Inicializa la Base de Datos.
    Si cambias el schema, considera usar migraciones en lugar de DROP TABLE en producción.
    """
    global pool
    
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL FALTANTE")
        return

    try:
        # Configuración del Pool
        pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=5,
            max_size=20
        )
        logger.info("✅ DB Pool Conectado.")
        
        async with pool.acquire() as conn:
            # Crea tablas si no existen (IF NOT EXISTS es más seguro que DROP para no perder datos por error)
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
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                
                CREATE TABLE IF NOT EXISTS leads_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    email TEXT UNIQUE,
                    captured_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
    except Exception as e:
        logger.critical(f"❌ ERROR CRÍTICO EN DB: {e}")
        raise e

async def close_db():
    global pool
    if pool:
        await pool.close()
        logger.info("🔒 DB Pool Cerrado")

# --- CRUD OPERATIONS ---

async def add_user(user_id, first_name, username, referrer_id=None):
    """Crea usuario nuevo. Retorna True si se creó, False si ya existía."""
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            # Intentar insertar
            result = await conn.execute("""
                INSERT INTO users (user_id, first_name, username, referrer_id) 
                VALUES ($1, $2, $3, $4) 
                ON CONFLICT (user_id) DO NOTHING
            """, user_id, first_name, username, referrer_id)
            
            # Si "INSERT 0 1", se creó. Si "INSERT 0 0", ya existía.
            return result == "INSERT 0 1"
    except Exception as e:
        logger.error(f"Error add_user: {e}")
        return False

async def get_user(user_id):
    if not pool: return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None

async def update_user_email(user_id, email):
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET email = $1 WHERE user_id = $2", email, user_id)

async def add_lead(user_id, email):
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO leads_harvest (user_id, email) 
                VALUES ($1, $2) 
                ON CONFLICT (user_id) DO UPDATE SET email = EXCLUDED.email
            """, user_id, email)
        return True
    except Exception:
        return False

async def reward_referrer(referrer_id, points=50):
    """Recompensa al usuario que invitó."""
    if not pool or not referrer_id: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE users 
                SET balance_hive = balance_hive + $1 
                WHERE user_id = $2
            """, points, referrer_id)
    except Exception as e:
        logger.error(f"Error reward_referrer: {e}")

async def get_user_referrals_count(user_id):
    """Cuenta cuántos referidos tiene un usuario."""
    if not pool: return 0
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT COUNT(*) FROM users WHERE referrer_id = $1", user_id)
        return val

async def delete_user(user_id):
    """DEV ONLY: Borra usuario para pruebas."""
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
