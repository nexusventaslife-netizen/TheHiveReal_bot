import logging
import asyncpg
import datetime
import json
import os
import redis.asyncio as redis
from typing import Optional, Dict

logger = logging.getLogger("Hive.DB")
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

TIER_1_COUNTRIES = ['US', 'GB', 'CA', 'DE', 'AU', 'CH', 'NO', 'SE']

async def init_db(database_url):
    global db_pool, redis_client
    
    if not database_url:
        logger.critical("❌ FATAL: NO DATABASE URL")
        return
    db_pool = await asyncpg.create_pool(database_url, min_size=5, max_size=100)
    
    # CONEXIÓN REDIS
    redis_url = os.environ.get("REDIS_URL")
    try:
        if redis_url:
            redis_client = redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            logger.info("✅ REDIS CONECTADO EN DATABASE.")
    except Exception as e:
        logger.error(f"⚠️ ERROR REDIS: {e}")

    async with db_pool.acquire() as conn:
        # 1. CREAR TABLAS BASE
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                country_code TEXT DEFAULT 'GLOBAL',
                tier TEXT DEFAULT 'TIER_3',
                balance_available DOUBLE PRECISION DEFAULT 0.0,
                balance_pending DOUBLE PRECISION DEFAULT 0.0,
                balance_hive DOUBLE PRECISION DEFAULT 0.0,
                balance_usd DOUBLE PRECISION DEFAULT 0.0,
                rank TEXT DEFAULT 'LARVA',
                xp BIGINT DEFAULT 0,
                streak_days INT DEFAULT 0,
                last_activity DATE DEFAULT CURRENT_DATE,
                mining_power DOUBLE PRECISION DEFAULT 1.0,
                wallet_address TEXT,
                email TEXT,
                api_gate_passed BOOLEAN DEFAULT FALSE,
                data_consent BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                mining_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # 2. TABLAS TRANSACCIONALES
        await conn.execute("""
             CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY, user_id BIGINT, type TEXT, amount DOUBLE PRECISION, 
                status TEXT, source TEXT, created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS admin_revenue (
                id SERIAL PRIMARY KEY, source TEXT, gross_amount DOUBLE PRECISION, 
                user_share DOUBLE PRECISION, admin_profit DOUBLE PRECISION, created_at TIMESTAMP DEFAULT NOW()
            );
            -- CORRECCIÓN IMPORTANTE AQUÍ: Definimos email como UNIQUE si se crea de nuevo
            CREATE TABLE IF NOT EXISTS leads_harvest (
                id SERIAL PRIMARY KEY, 
                telegram_id BIGINT, 
                email TEXT UNIQUE, 
                country TEXT, 
                market_value DOUBLE PRECISION DEFAULT 0.0, 
                exported BOOLEAN DEFAULT FALSE, 
                captured_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ---------------------------------------------------------
        # 🚨 PARCHE DE EMERGENCIA: Agregar restricción UNIQUE si falta
        # ---------------------------------------------------------
        try:
            # Intentamos agregar la restricción única al email en leads_harvest
            # Si ya existe, fallará silenciosamente o no hará nada
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'leads_harvest_email_key'
                    ) THEN
                        ALTER TABLE leads_harvest ADD CONSTRAINT leads_harvest_email_key UNIQUE (email);
                    END IF;
                END
                $$;
            """)
        except Exception as e:
            logger.warning(f"Nota sobre migración de constraints: {e}")
        # ---------------------------------------------------------

        # 3. TABLAS PARA TASKS.PY
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger (
                id SERIAL PRIMARY KEY,
                tx_hash TEXT UNIQUE,
                user_id BIGINT,
                tx_type TEXT,
                amount_hive DOUBLE PRECISION,
                amount_usd DOUBLE PRECISION,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS user_data_harvest (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                data_type TEXT,
                payload JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS viral_content (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                platform TEXT,
                url TEXT,
                clicks INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

# --- FUNCIONES ---

async def get_user_fast(tg_id: int):
    # Intentar Redis primero
    if redis_client:
        try:
            cached = await redis_client.get(f"user:{tg_id}")
            if cached: return json.loads(cached)
        except: pass

    # Intentar DB
    if not db_pool: return {}
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        if row:
            data = dict(row)
            if redis_client:
                await redis_client.setex(f"user:{tg_id}", 60, json.dumps(data, default=str))
            return data
        return {}

async def register_user_smart(user):
    if not db_pool: return
    lang = user.language_code or "en"
    country = lang.split("-")[-1].upper() if "-" in lang else "GLOBAL"
    tier = "TIER_1" if country in TIER_1_COUNTRIES else "TIER_3"
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, country_code, tier)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_id) DO NOTHING
        """, user.id, user.first_name, country, tier)
    return tier

async def save_user_email(telegram_id: int, email: str, market_value: float = 0.0):
    if not db_pool: return False
    
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Guardar en perfil de usuario
                await conn.execute("UPDATE users SET email=$1, data_consent=TRUE WHERE telegram_id=$2", email, telegram_id)
                
                # Guardar en leads_harvest con manejo seguro de conflictos
                # Ahora que hemos asegurado la constraint UNIQUE, esto funcionará
                await conn.execute("""
                    INSERT INTO leads_harvest (telegram_id, email, country, market_value)
                    VALUES ($1, $2, 'UNK', $3) 
                    ON CONFLICT (email) DO NOTHING
                """, telegram_id, email, market_value)
        
        if redis_client: await redis_client.delete(f"user:{telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving email: {e}")
        # En caso de error crítico, devolvemos False para que el bot pueda avisar
        return False

async def process_secure_postback(user_id, amount, network, admin_percent=0.30):
    if not db_pool: return
    admin_profit = amount * admin_percent
    user_share = amount - admin_profit
    status = 'AVAILABLE' if user_share < 5.0 else 'ON_HOLD'
    
    col = "balance_available" if status == 'AVAILABLE' else "balance_pending"
    
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f"""
                UPDATE users 
                SET {col} = {col} + $1, balance_usd = balance_usd + $1 
                WHERE telegram_id=$2
            """, user_share, user_id)
            
            await conn.execute("INSERT INTO transactions (user_id, type, amount, status, source) VALUES ($1, 'CPA_EARN', $2, $3, $4)", user_id, user_share, status, network)
            await conn.execute("INSERT INTO admin_revenue (source, gross_amount, user_share, admin_profit) VALUES ($1, $2, $3, $4)", network, amount, user_share, admin_profit)
    if redis_client: await redis_client.delete(f"user:{user_id}")
    return {"user_share": user_share, "status": status}

async def update_gamification(user_id):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT streak_days, last_activity, xp FROM users WHERE telegram_id=$1", user_id)
        if not row: return {"streak": 0, "rank": "LARVA"}
        
        today = datetime.date.today()
        last = row['last_activity']
        streak = row['streak_days'] or 0
        xp = row['xp'] or 0
        
        if last == today: pass
        elif last == today - datetime.timedelta(days=1): streak += 1
        else: streak = 1
        
        new_rank = "LARVA"
        if xp > 1000: new_rank = "ABEJA"
        if xp > 10000: new_rank = "TITAN"
        
        await conn.execute("UPDATE users SET streak_days=$1, last_activity=$2, rank=$3 WHERE telegram_id=$4", streak, today, new_rank, user_id)
        if redis_client: await redis_client.delete(f"user:{user_id}")
        return {"streak": streak, "rank": new_rank}

async def burn_hive_for_withdrawal(user_id, usd_amount):
    cost_hive = usd_amount * 100
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance_hive, balance_available FROM users WHERE telegram_id=$1", user_id)
        if not user or user['balance_hive'] < cost_hive or user['balance_available'] < usd_amount:
            return "NO_FUNDS"
        async with conn.transaction():
            await conn.execute("UPDATE users SET balance_hive = balance_hive - $1, balance_available = balance_available - $2, balance_usd = balance_usd - $2 WHERE telegram_id=$3", cost_hive, usd_amount, user_id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1, 'WITHDRAW', $2, 'PENDING')", user_id, usd_amount)
    if redis_client: await redis_client.delete(f"user:{user_id}")
    return "OK"

async def unlock_api_gate(user_id):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET api_gate_passed = TRUE WHERE telegram_id=$1", user_id)
    if redis_client: await redis_client.delete(f"user:{user_id}")
