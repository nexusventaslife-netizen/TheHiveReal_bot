import os
import logging
import asyncpg

# Logs
logger = logging.getLogger("Hive.DB")

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    """
    Inicializa Pool de Postgres.
    Configuración para Alta Concurrencia (Render Standard).
    """
    global pool
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL FALTANTE")
        return

    try:
        # Creamos pool con límites para no saturar Postgres
        pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=5,  # Mantiene 5 conexiones vivas siempre
            max_size=20, # Sube hasta 20 si hay mucho tráfico
            max_inactive_connection_lifetime=300
        )
        logger.info("✅ DB Pool Conectado (Max: 20 conexiones)")
        
        # Schema Init (Crear tablas si no existen)
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
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                -- Índice para búsquedas rápidas por email
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                
                CREATE TABLE IF NOT EXISTS leads_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    email TEXT UNIQUE,
                    captured_at TIMESTAMP DEFAULT NOW()
                );
            """)
    except Exception as e:
        logger.critical(f"❌ DB ERROR: {e}")
        raise e

async def close_db():
    global pool
    if pool:
        await pool.close()
        logger.info("🔒 DB Pool Cerrado")

# --- QUERIES OPTIMIZADOS ---

async def add_user(user_id, first_name, username):
    if not pool: return
    async with pool.acquire() as conn:
        # 'ON CONFLICT DO NOTHING' es muy rápido
        await conn.execute("""
            INSERT INTO users (user_id, first_name, username) 
            VALUES ($1, $2, $3) 
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, first_name, username)

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
                ON CONFLICT (email) DO NOTHING
            """, user_id, email)
        return True
    except Exception:
        return False

async def update_user_gate_status(user_id, status=True):
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET api_gate_passed = $1 WHERE user_id = $2", status, user_id)

async def get_user_balance(user_id):
    if not pool: return {'balance_usd': 0.0, 'balance_hive': 0}
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT balance_usd, balance_hive FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else {'balance_usd': 0.0, 'balance_hive': 0}

async def add_hive_points(user_id, amount):
    if not pool: return
    async with pool.acquire() as conn:
        # Update atómico (seguro para concurrencia)
        await conn.execute("UPDATE users SET balance_hive = balance_hive + $1 WHERE user_id = $2", amount, user_id)
