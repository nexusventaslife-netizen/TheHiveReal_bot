import os
import logging
import asyncpg

# Configuración de Logs
logger = logging.getLogger("Hive.DB")

# URL de Conexión (La toma de las variables de entorno de Render)
DATABASE_URL = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    """Inicializa la conexión a la base de datos y crea las tablas."""
    global pool
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL FALTANTE. Revisa tus variables en Render.")
        return

    try:
        # Creamos el pool de conexiones
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=5, max_size=20)
        logger.info("✅ DB Pool Conectado.")
        
        async with pool.acquire() as conn:
            # Crea la tabla de usuarios si no existe
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
            logger.info("✅ Tablas verificadas.")
    except Exception as e:
        logger.critical(f"❌ ERROR CRÍTICO EN DB: {e}")

async def close_db():
    """Cierra la conexión al apagar el bot."""
    global pool
    if pool:
        await pool.close()
        logger.info("💤 DB Pool Cerrado.")

async def add_user(user_id, first_name, username, referrer_id=None):
    """Agrega un nuevo usuario."""
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            # Insertamos usuario. Si ya existe, no hacemos nada (DO NOTHING)
            result = await conn.execute("""
                INSERT INTO users (user_id, first_name, username, referrer_id) 
                VALUES ($1, $2, $3, $4) 
                ON CONFLICT (user_id) DO NOTHING
            """, user_id, first_name, username, referrer_id)
            
            # Verificamos si realmente se insertó (el tag será 'INSERT 0 1')
            if result == 'INSERT 0 1':
                # Si tenía referido, le damos puntos al que lo invitó
                if referrer_id and referrer_id != user_id:
                    await conn.execute("UPDATE users SET balance_hive = balance_hive + 50 WHERE user_id = $1", referrer_id)
                return True
            return False
    except Exception as e:
        logger.error(f"Error añadiendo usuario: {e}")
        return False

async def update_email(user_id, email):
    """Guarda el email del usuario."""
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET email = $1 WHERE user_id = $2", email, user_id)
            return True
    except Exception as e:
        logger.error(f"Error guardando email: {e}")
        return False

async def get_user(user_id):
    """Obtiene los datos de un usuario."""
    if not pool: return None
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    except Exception:
        return None

async def delete_user(user_id):
    """Borra un usuario (Para el comando /reset)."""
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
            logger.info(f"🗑️ Usuario {user_id} eliminado de la DB.")
    except Exception as e:
        logger.error(f"Error borrando usuario: {e}")
