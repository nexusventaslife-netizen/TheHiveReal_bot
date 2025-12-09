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
    REGENERANDO ESQUEMA PARA SOPORTAR REFERIDOS.
    """
    global pool
    
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL FALTANTE")
        return

    try:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=5, max_size=20)
        logger.info("✅ DB Pool Conectado.")
        
        async with pool.acquire() as conn:
            # 🧨 ZONA DE LIMPIEZA: Borramos para actualizar la estructura
            logger.warning("⚠️ ACTUALIZANDO ESQUEMA DE BASE DE DATOS...")
            await conn.execute("DROP TABLE IF EXISTS users CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS leads_harvest CASCADE;")
            
            # NUEVA TABLA CON SOPORTE DE REFERIDOS
            await conn.execute("""
                CREATE TABLE users (
                    user_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    email TEXT,
                    balance_usd NUMERIC(10, 4) DEFAULT 0.0,
                    balance_hive BIGINT DEFAULT 0,
                    api_gate_passed BOOLEAN DEFAULT FALSE,
                    referrer_id BIGINT,             -- Quién lo invitó
                    referrals_count INT DEFAULT 0,  -- Cuántos ha invitado
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX idx_users_email ON users(email);
                
                CREATE TABLE leads_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    email TEXT UNIQUE,
                    captured_at TIMESTAMP DEFAULT NOW()
                );
            """)
            logger.info("✅ Tablas regeneradas con sistema de referidos.")
            
    except Exception as e:
        logger.critical(f"❌ ERROR CRÍTICO EN DB: {e}")
        raise e

async def close_db():
    global pool
    if pool:
        await pool.close()

# --- FUNCIONES DE REFERIDOS Y USUARIOS ---

async def add_user(user_id, first_name, username, referrer_id=None):
    """
    Crea usuario y procesa la recompensa por referido si aplica.
    Devuelve TRUE si es un usuario nuevo, FALSE si ya existía.
    """
    if not pool: return False
    
    try:
        async with pool.acquire() as conn:
            # 1. Intentamos insertar el nuevo usuario
            # Usamos RETURNING para saber si se insertó realmente
            result = await conn.fetchval("""
                INSERT INTO users (user_id, first_name, username, referrer_id) 
                VALUES ($1, $2, $3, $4) 
                ON CONFLICT (user_id) DO NOTHING
                RETURNING user_id
            """, user_id, first_name, username, referrer_id)
            
            # Si result es None, el usuario ya existía. No hacemos nada más.
            if not result:
                return False

            # 2. Si es usuario nuevo y tiene referrer_id, recompensamos al invitador
            if referrer_id and referrer_id != user_id:
                logger.info(f"💰 Procesando referido: {referrer_id} invitó a {user_id}")
                await conn.execute("""
                    UPDATE users 
                    SET balance_hive = balance_hive + 50,
                        referrals_count = referrals_count + 1
                    WHERE user_id = $1
                """, referrer_id)
            
            return True

    except Exception as e:
        logger.error(f"Error añadiendo usuario: {e}")
        return False

async def get_user(user_id):
    if not pool: return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None

# --- OTRAS FUNCIONES ---
# (Las mantenemos igual para que el resto del bot funcione)

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
