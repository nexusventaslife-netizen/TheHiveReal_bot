import logging
import asyncpg
import datetime
from typing import Optional, Dict

logger = logging.getLogger("Hive.DB")
db_pool: Optional[asyncpg.Pool] = None

TIER_1_COUNTRIES = ['US', 'GB', 'CA', 'DE', 'AU', 'CH', 'NO', 'SE']

async def init_db(database_url):
    global db_pool
    if not database_url:
        logger.critical("❌ FATAL: NO DATABASE URL")
        return

    db_pool = await asyncpg.create_pool(database_url, min_size=20, max_size=100)
    
    async with db_pool.acquire() as conn:
        # 1. Crear tabla si es una instalación nueva
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                country_code TEXT DEFAULT 'GLOBAL',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # 2. AUTO-MIGRACIÓN: Agregar columnas nuevas a tablas viejas
        # Esto soluciona el error "UndefinedColumnError"
        await conn.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'TIER_3';
            ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_available DOUBLE PRECISION DEFAULT 0.0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_pending DOUBLE PRECISION DEFAULT 0.0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_hive DOUBLE PRECISION DEFAULT 0.0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS rank TEXT DEFAULT 'LARVA';
            ALTER TABLE users ADD COLUMN IF NOT EXISTS xp BIGINT DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_days INT DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity DATE DEFAULT CURRENT_DATE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS mining_power DOUBLE PRECISION DEFAULT 1.0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS api_gate_passed BOOLEAN DEFAULT FALSE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS data_consent BOOLEAN DEFAULT TRUE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_address TEXT;
        """)

        # Crear índices para velocidad
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);")

        # Tablas auxiliares
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                type TEXT,
                amount DOUBLE PRECISION,
                status TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id);
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_revenue (
                id SERIAL PRIMARY KEY,
                source TEXT,
                gross_amount DOUBLE PRECISION,
                user_share DOUBLE PRECISION,
                admin_profit DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS leads_harvest (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                email TEXT,
                country TEXT,
                market_value DOUBLE PRECISION DEFAULT 0.0,
                exported BOOLEAN DEFAULT FALSE,
                captured_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_leads_email ON leads_harvest(email);
        """)
        
        logger.info("✅ BASE DE DATOS MIGRADA Y LISTA.")

# --- FUNCIONES DE ALTO RENDIMIENTO ---

async def get_user_fast(tg_id: int):
    if not db_pool: return {}
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        return dict(row) if row else {}

async def register_user_smart(user):
    if not db_pool: return
    
    lang = user.language_code or "en"
    country = lang.split("-")[-1].upper() if "-" in lang else "GLOBAL"
    tier = "TIER_1" if country in TIER_1_COUNTRIES else "TIER_3"
    
    async with db_pool.acquire() as conn:
        # Intentamos insertar, si ya existe no hace nada
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, country_code, tier)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_id) DO NOTHING
        """, user.id, user.first_name, country, tier)
        return tier

async def save_user_email(telegram_id: int, email: str, market_value: float = 0.0):
    if not db_pool: return False
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("""
                UPDATE users SET email=$1, data_consent=TRUE WHERE telegram_id=$2
            """, email, telegram_id)
            await conn.execute("""
                INSERT INTO leads_harvest (telegram_id, email, country, market_value)
                VALUES ($1, $2, (SELECT country_code FROM users WHERE telegram_id=$1), $3)
                ON CONFLICT (email) DO NOTHING
            """, telegram_id, email, market_value)
    return True

async def process_secure_postback(user_id, amount, network, admin_percent=0.30):
    if not db_pool: return
    
    admin_profit = amount * admin_percent
    user_share = amount - admin_profit
    status = 'AVAILABLE' if user_share < 5.0 else 'ON_HOLD'
    target_column = "balance_available" if status == 'AVAILABLE' else "balance_pending"
    
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f"UPDATE users SET {target_column} = {target_column} + $1 WHERE telegram_id=$2", user_share, user_id)
            await conn.execute("""
                INSERT INTO transactions (user_id, type, amount, status, source)
                VALUES ($1, 'CPA_EARN', $2, $3, $4)
            """, user_id, user_share, status, network)
            await conn.execute("""
                INSERT INTO admin_revenue (source, gross_amount, user_share, admin_profit)
                VALUES ($1, $2, $3, $4)
            """, network, amount, user_share, admin_profit)
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
        
        if last == today:
            pass
        elif last == today - datetime.timedelta(days=1):
            streak += 1
        else:
            streak = 1
        
        new_rank = "LARVA"
        if xp > 1000: new_rank = "ABEJA"
        if xp > 10000: new_rank = "SOLDADO"
        if xp > 50000: new_rank = "TITAN"
        
        await conn.execute("""
            UPDATE users SET streak_days=$1, last_activity=$2, rank=$3
            WHERE telegram_id=$4
        """, streak, today, new_rank, user_id)
        
        return {"streak": streak, "rank": new_rank}

async def burn_hive_for_withdrawal(user_id, usd_amount):
    cost_hive = usd_amount * 100
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance_hive, balance_available FROM users WHERE telegram_id=$1", user_id)
        if not user: return "NO_USER"
        if user['balance_hive'] < cost_hive: return "NO_HIVE"
        if user['balance_available'] < usd_amount: return "NO_USD"
        
        async with conn.transaction():
            await conn.execute("UPDATE users SET balance_hive = balance_hive - $1 WHERE telegram_id=$2", cost_hive, user_id)
            await conn.execute("UPDATE users SET balance_available = balance_available - $1 WHERE telegram_id=$2", usd_amount, user_id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1, 'WITHDRAW', $2, 'PENDING')", user_id, usd_amount)
    return "OK"

async def unlock_api_gate(user_id):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET api_gate_passed = TRUE WHERE telegram_id=$1", user_id)
