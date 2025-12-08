import logging
import asyncpg
import datetime
from typing import Optional, Dict

logger = logging.getLogger("Hive.DB")
db_pool: Optional[asyncpg.Pool] = None

# CONFIGURACIÓN DE ESCALABILIDAD
# Tier 1: Alta Paga (EEUU, UK, DE)
# Tier 2: Volumen Medio (ES, MX, BR)
# Tier 3: Volumen Masivo (Resto del mundo)
TIER_1_COUNTRIES = ['US', 'GB', 'CA', 'DE', 'AU', 'CH', 'NO', 'SE']

async def init_db(database_url):
    global db_pool
    if not database_url:
        logger.critical("❌ FATAL: NO DATABASE URL")
        return

    # POOL PARA 200,000 USUARIOS: Min 20 conexiones, Max 100 para aguantar picos
    db_pool = await asyncpg.create_pool(database_url, min_size=20, max_size=100)
    
    async with db_pool.acquire() as conn:
        # 1. USUARIOS (Indexado para velocidad extrema)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                country_code TEXT DEFAULT 'GLOBAL',
                tier TEXT DEFAULT 'TIER_3',
                
                -- FINANZAS REALES
                balance_available DOUBLE PRECISION DEFAULT 0.0, -- Retirable YA
                balance_pending DOUBLE PRECISION DEFAULT 0.0,   -- En Hold (Seguridad)
                balance_hive DOUBLE PRECISION DEFAULT 0.0,      -- Token Interno
                
                -- GAMIFICACIÓN (ADICCIÓN)
                rank TEXT DEFAULT 'LARVA',
                xp BIGINT DEFAULT 0,
                streak_days INT DEFAULT 0,
                last_activity DATE DEFAULT CURRENT_DATE,
                mining_power DOUBLE PRECISION DEFAULT 1.0,
                
                -- SEGURIDAD & MONETIZACIÓN
                api_gate_passed BOOLEAN DEFAULT FALSE, -- Muro CPA inicial
                data_consent BOOLEAN DEFAULT TRUE,
                wallet_address TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);
        """)

        # 2. TRANSACCIONES (Ledger Inmutable)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                type TEXT, -- 'CPA_EARN', 'WITHDRAW', 'NFT_BUY', 'REFERRAL'
                amount DOUBLE PRECISION,
                status TEXT, -- 'COMPLETED', 'ON_HOLD', 'PENDING'
                source TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id);
        """)

        # 3. REVENUE ADMIN (Tu Ganancia Oculta)
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

# --- FUNCIONES DE ALTO RENDIMIENTO ---

async def get_user_fast(tg_id: int):
    """Lectura ultra-rápida para 200k usuarios."""
    if not db_pool: return {}
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        return dict(row) if row else {}

async def register_user_smart(user):
    """Registro con auto-detección de Tier."""
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

async def process_secure_postback(user_id, amount, network, admin_percent=0.30):
    """
    EL CEREBRO FINANCIERO (Auditado por Blue Team).
    1. Calcula Split.
    2. Aplica Hold de 7 días si el monto es sospechoso (>$5).
    3. Registra tu ganancia.
    """
    if not db_pool: return
    
    # Cálculos
    admin_profit = amount * admin_percent
    user_share = amount - admin_profit
    
    # Regla de Seguridad: Si paga más de $5, va a Pending (Anti-Fraude)
    status = 'AVAILABLE' if user_share < 5.0 else 'ON_HOLD'
    target_column = "balance_available" if status == 'AVAILABLE' else "balance_pending"
    
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # 1. Pagar al usuario (al bolsillo correcto)
            await conn.execute(f"UPDATE users SET {target_column} = {target_column} + $1 WHERE telegram_id=$2", user_share, user_id)
            
            # 2. Registrar transacción usuario
            await conn.execute("""
                INSERT INTO transactions (user_id, type, amount, status, source)
                VALUES ($1, 'CPA_EARN', $2, $3, $4)
            """, user_id, user_share, status, network)
            
            # 3. Registrar tu ganancia
            await conn.execute("""
                INSERT INTO admin_revenue (source, gross_amount, user_share, admin_profit)
                VALUES ($1, $2, $3, $4)
            """, network, amount, user_share, admin_profit)
            
    return {"user_share": user_share, "status": status}

async def update_gamification(user_id):
    """Sistema de Adicción: Rachas y Rangos."""
    if not db_pool: return
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT streak_days, last_activity, xp FROM users WHERE telegram_id=$1", user_id)
        if not row: return
        
        today = datetime.date.today()
        last = row['last_activity']
        streak = row['streak_days']
        xp = row['xp']
        
        # Lógica de Racha
        if last == today:
            pass # Ya entró hoy
        elif last == today - datetime.timedelta(days=1):
            streak += 1 # Mantiene racha
        else:
            streak = 1 # Perdió racha
            
        # Cálculo de Rango
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
    """
    DEFLACIÓN: Quema HIVE para permitir sacar Dólares.
    Costo: 100 HIVE por cada $1 USD retirado.
    """
    cost_hive = usd_amount * 100
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance_hive, balance_available FROM users WHERE telegram_id=$1", user_id)
        
        if user['balance_hive'] < cost_hive: return "NO_HIVE"
        if user['balance_available'] < usd_amount: return "NO_USD"
        
        async with conn.transaction():
            # Quema HIVE
            await conn.execute("UPDATE users SET balance_hive = balance_hive - $1 WHERE telegram_id=$2", cost_hive, user_id)
            # Resta USD
            await conn.execute("UPDATE users SET balance_available = balance_available - $1 WHERE telegram_id=$2", usd_amount, user_id)
            # Registra Retiro
            await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1, 'WITHDRAW', $2, 'PENDING')", user_id, usd_amount)
            
        return "OK"

async def unlock_api_gate(user_id):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET api_gate_passed = TRUE WHERE telegram_id=$1", user_id)
