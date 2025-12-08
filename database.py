import os
import logging
import asyncpg
import redis.asyncio as redis

# Configuración de Logs
logger = logging.getLogger(__name__)

# URL de Conexión
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Variables globales
pool = None
redis_client = None

async def init_db():
    """Inicializa conexiones optimizadas para tráfico alto."""
    global pool, redis_client
    
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL faltante. El bot no puede arrancar.")
        raise ValueError("DATABASE_URL missing")

    # 1. POSTGRESQL: Configuración de Pool para Escalar
    # max_size=20 es seguro para el plan Starter de Render. 
    # Si subes de plan, puedes aumentar esto a 50 o 100.
    try:
        pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("✅ PostgreSQL Pool: Conectado (Max 20 conexiones).")
        
        # Crear tablas (Idempotente: no falla si ya existen)
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
                CREATE TABLE IF NOT EXISTS leads_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    email TEXT UNIQUE,
                    source TEXT DEFAULT 'bot',
                    captured_at TIMESTAMP DEFAULT NOW()
                );
                -- Índices para velocidad en busquedas de millones de filas
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_leads_email ON leads_harvest(email);
            """)
    except Exception as e:
        logger.critical(f"❌ Error fatal en DB: {e}")
        raise e

    # 2. REDIS: Caché rápido
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis: Conectado.")
    except Exception as e:
        logger.warning(f"⚠️ Redis no disponible: {e}")

async def close_db():
    """Cierre limpio para evitar fugas de memoria."""
    global pool, redis_client
    if pool:
        await pool.close()
        logger.info("🔒 DB Pool cerrado.")
    if redis_client:
        await redis_client.close()
        logger.info("🔒 Redis cerrado.")

# --- FUNCIONES CORE (Optimized) ---

async def add_user(user_id, first_name, username):
    if not pool: return
    async with pool.acquire() as conn:
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
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO leads_harvest (user_id, email) 
                VALUES ($1, $2) 
                ON CONFLICT (user_id) DO UPDATE SET email = EXCLUDED.email
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
        await conn.execute("UPDATE users SET balance_hive = balance_hive + $1 WHERE user_id = $2", amount, user_id)
