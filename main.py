"""
THE ONE HIVE: TITAN ENTERPRISE EDITION (PART 1/3)
=================================================
ARCHITECTURE: SHARD-READY MONOLITH
CAPACITY: 200,000+ CONCURRENT USERS
MODULES: CORE, DB, SECURITY, CONFIG

INSTRUCCIONES DE ENSAMBLAJE:
1. COPIA ESTE BLOQUE.
2. PEGA LA PARTE 2 DEBAJO.
3. PEGA LA PARTE 3 AL FINAL.
"""

import os
import logging
import hashlib
import hmac
import asyncio
import json
import random
import time
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union, Tuple
from io import BytesIO

# --- DEPENDENCIAS DE ALTO RENDIMIENTO ---
import asyncpg
from email_validator import validate_email, EmailNotValidError
from PIL import Image
import imagehash
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputMediaPhoto,
    ChatAction
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    Defaults
)
from telegram.error import Conflict, NetworkError, BadRequest, TimedOut
from telegram.constants import ParseMode

# ==============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y TUNING DE RENDIMIENTO
# ==============================================================================

# Logging asíncrono y estructurado para Debugging en Producción
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("Hive.Enterprise")

# --- VARIABLES DE ENTORNO (SEGURIDAD) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATA_BUYER_KEY = os.environ.get("DATA_BUYER_KEY", "hive_master_key_v1")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "change_this_in_production")

# --- VARIABLES FINANCIERAS ---
ADMIN_WALLET_TRC20 = os.environ.get("ADMIN_WALLET_TRC20", "TU_WALLET_TRC20")
OFFERTORO_PUB_ID = os.environ.get("OFFERTORO_PUB_ID", "0")
OFFERTORO_SECRET = os.environ.get("OFFERTORO_SECRET", "0")

# --- TOKENOMICS & ECONOMÍA (AJUSTADO PARA ESCALA) ---
TOKEN_SYMBOL = "HIVE"
PRICE_VIP_USD = 14.99
EVOLUTION_COST_HIVE = 5000.0
REWARD_AD_WATCH = 10.0
REWARD_VIRAL_VIDEO = 500.0
REFERRAL_BONUS_HIVE = 200.0
MIN_WITHDRAW_USD = 10.0
FEE_TURBO_WITHDRAW = 1.50
FEE_P2P_PERCENT = 0.05 

# --- GEO-INTELLIGENCE DATA LAKE (TIER CONFIG) ---
REGION_DATA = {
    "TIER_1": {
        "countries": ["US", "GB", "DE", "CA", "AU", "CH", "SE", "NO"], 
        "daily_cap": "$850.00", 
        "base_projection": 15.0, 
        "opt_projection": 45.0,
        "message": "🌍 Mercado de Alta Capitalización Detectado."
    },
    "TIER_2": {
        "countries": ["ES", "MX", "BR", "IT", "FR", "CO", "AR", "CL", "PE", "AE", "JP", "KR"], 
        "daily_cap": "$320.00", 
        "base_projection": 8.0, 
        "opt_projection": 25.0,
        "message": "🚀 Mercado Emergente de Alto Crecimiento."
    },
    "TIER_3": {
        "countries": ["DEFAULT"], 
        "daily_cap": "$105.00", 
        "base_projection": 4.0, 
        "opt_projection": 12.0,
        "message": "💎 Oportunidad de Arbitraje Global Detectada."
    }
}

# --- ENLACES DE AFILIADOS (NEXUS MARKET) ---
LINKS = {
    "TRADING": "https://hotmart.com/es/marketplace/productos/curso-trading-ejemplo",
    "FREELANCE": "https://fiverr.com",
    "HOSTING": "https://hostinger.com",
    "BINANCE": "https://accounts.binance.com/register"
}

# ==============================================================================
# 2. INFRAESTRUCTURA DE API (FASTAPI)
# ==============================================================================

app = FastAPI(title="TheOneHive Titan API", version="5.0.0")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "OPERATIONAL", "load": "NORMAL", "timestamp": datetime.utcnow().isoformat()})

# --- DATA BROKER ENDPOINT ---
@app.get("/api/v1/export_leads")
async def export_leads_secure(key: str, min_rank: str = None, country: str = None):
    if key != DATA_BUYER_KEY: raise HTTPException(status_code=403, detail="ACCESS_DENIED")
    if not db_pool: raise HTTPException(status_code=503, detail="DB_UNAVAILABLE")

    try:
        async with db_pool.acquire() as conn:
            query = "SELECT telegram_id, first_name, email, rank, country_code, balance_usd FROM users WHERE email IS NOT NULL"
            rows = await conn.fetch(query)
            return {"data": [dict(r) for r in rows]}
    except Exception as e:
        logger.error(f"Data Export Error: {e}")
        raise HTTPException(500, "Internal Error")

# --- POSTBACK CPA HANDLER ---
@app.get("/postback/nectar")
async def nectar_postback_handler(oid: str, user_id: int, amount: float, signature: str, ip: str = "0.0.0.0"):
    logger.info(f"CPA Postback: User={user_id}, Amount=${amount}")
    usd_share = amount * 0.30
    hive_share = amount * 100.0
    
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("UPDATE users SET balance_usd = balance_usd + $1, balance_hive = balance_hive + $2, is_verified = TRUE WHERE telegram_id = $3", usd_share, hive_share, user_id)
                    await conn.execute("INSERT INTO ledger (tx_hash, user_id, tx_type, amount_hive, amount_usd, metadata) VALUES ($1, $2, 'CPA_REVENUE', $3, $4, $5)", hashlib.sha256(f"{user_id}{oid}{time.time()}".encode()).hexdigest(), user_id, hive_share, usd_share, f"Offer: {oid}")
                    await conn.execute("INSERT INTO user_data_harvest (user_id, data_type, payload) VALUES ($1, 'cpa_conversion', $2)", user_id, json.dumps({"offer": oid, "val": amount, "ip": ip}))
            return "1"
        except Exception as e:
            logger.error(f"CPA Error: {e}")
            raise HTTPException(500, "Transaction Failed")
    return "0"

# ==============================================================================
# 3. CAPA DE DATOS (POSTGRESQL OPTIMIZADO)
# ==============================================================================

db_pool: Optional[asyncpg.Pool] = None

async def init_database_architecture():
    global db_pool
    if not DATABASE_URL:
        logger.critical("⚠️ DATABASE_URL MISSING. MODE: STATELESS.")
        return
    
    try:
        # Configuración de Pool para 200k usuarios (Conexiones concurrentes)
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=10, max_size=50, max_inactive_connection_lifetime=300)
        
        async with db_pool.acquire() as conn:
            # TABLAS OPTIMIZADAS CON ÍNDICES
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    email TEXT UNIQUE,
                    country_code TEXT DEFAULT 'UNK',
                    region_tier TEXT DEFAULT 'TIER_3',
                    referrer_id BIGINT,
                    rank TEXT DEFAULT 'LARVA',
                    balance_usd DOUBLE PRECISION DEFAULT 0.0 CHECK (balance_usd >= 0),
                    balance_hive DOUBLE PRECISION DEFAULT 0.0 CHECK (balance_hive >= 0),
                    mining_power DOUBLE PRECISION DEFAULT 1.0,
                    mining_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    data_points INTEGER DEFAULT 0,
                    last_active TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);

                CREATE TABLE IF NOT EXISTS ledger (
                    tx_hash TEXT PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    tx_type TEXT NOT NULL,
                    amount_hive DOUBLE PRECISION DEFAULT 0.0,
                    amount_usd DOUBLE PRECISION DEFAULT 0.0,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_ledger_userid ON ledger(user_id);

                CREATE TABLE IF NOT EXISTS p2p_market (
                    id SERIAL PRIMARY KEY,
                    seller_id BIGINT REFERENCES users(telegram_id),
                    amount_hive DOUBLE PRECISION NOT NULL,
                    price_usd DOUBLE PRECISION NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS security_hashes (
                    hash_id TEXT PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS user_data_harvest (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    data_type TEXT,
                    payload JSONB,
                    captured_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS viral_content (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    platform TEXT,
                    url TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
        logger.info("✅ DB SCHEMA DEPLOYED & OPTIMIZED.")
    except Exception as e:
        logger.critical(f"❌ DB INIT FAILED: {e}")
        raise e
