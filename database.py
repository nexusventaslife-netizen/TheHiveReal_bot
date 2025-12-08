import os
import logging
import asyncpg
from datetime import datetime

# Configuración de Logs
logger = logging.getLogger(__name__)

# URL de Conexión (Desde Render)
DATABASE_URL = os.getenv("DATABASE_URL")

# Variable global para el pool de conexiones
pool = None

async def init_db():
    """Inicializa el pool de conexiones a PostgreSQL."""
    global pool
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL no está definida.")
        return

    try:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL)
        logger.info("✅ Conexión a Base de Datos (AsyncPG) establecida.")
        
        # Crear tablas si no existen (Inicialización básica)
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
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS leads_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    email TEXT UNIQUE,
                    captured_at TIMESTAMP DEFAULT NOW()
                );
            """)
    except Exception as e:
        logger.error(f"❌ Error conectando a DB: {e}")
        raise e

async def close_db():
    """Cierra el pool de conexiones limpiamente."""
    global pool
    if pool:
        await pool.close()
        logger.info("🛑 Conexión a Base de Datos cerrada.")

# --- FUNCIONES DE USUARIO ---

async def add_user(user_id, first_name, username):
    """Crea un usuario si no existe."""
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, first_name, username) 
            VALUES ($1, $2, $3) 
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, first_name, username)

async def get_user(user_id):
    """Obtiene datos del usuario."""
    if not pool: return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None

async def update_user_email(user_id, email):
    """Actualiza el email del usuario."""
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET email = $1 WHERE user_id = $2", email, user_id)

async def add_lead(user_id, email):
    """Guarda el email en la tabla de leads (Harvest)."""
    if not pool: return
    async with pool.acquire() as conn:
        # Usamos ON CONFLICT para evitar errores si el email ya existe
        await conn.execute("""
            INSERT INTO leads_harvest (user_id, email) 
            VALUES ($1, $2) 
            ON CONFLICT (email) DO NOTHING
        """, user_id, email)

async def update_user_gate_status(user_id, status=True):
    """Marca que el usuario pasó el filtro de publicidad."""
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET api_gate_passed = $1 WHERE user_id = $2", status, user_id)

async def get_user_balance(user_id):
    """Retorna los saldos del usuario."""
    if not pool: return {'balance_usd': 0.0, 'balance_hive': 0}
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT balance_usd, balance_hive FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else {'balance_usd': 0.0, 'balance_hive': 0}
