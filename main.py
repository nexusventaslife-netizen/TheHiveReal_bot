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
# ==============================================================================
# 4. SERVICIOS INTERNOS (LÓGICA DE NEGOCIO)
# ==============================================================================

class UserManager:
    @staticmethod
    async def get_or_create(user: Any, referrer_id: Optional[int] = None) -> Dict[str, Any]:
        """Gestión inteligente de usuarios con detección de región."""
        if not db_pool: return {"telegram_id": user.id, "rank": "LARVA", "balance_usd": 0, "balance_hive": 0, "region_tier": "TIER_3"}
        
        # Geo-Detección
        lang = user.language_code or "en"
        country_code = lang.split("-")[-1].upper() if "-" in lang else lang.upper()
        
        region_tier = "TIER_3"
        for tier_name, data in REGION_DATA.items():
            if country_code in data["countries"]:
                region_tier = tier_name
                break
        
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO users (telegram_id, first_name, username, referrer_id, country_code, region_tier)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (telegram_id) DO UPDATE 
                SET first_name = EXCLUDED.first_name, username = EXCLUDED.username, last_active = NOW()
                RETURNING *
            """, user.id, user.first_name, user.username, referrer_id, country_code, region_tier)
            
            # Smart Contract de Referidos
            if referrer_id and referrer_id != user.id and row['created_at'] == datetime.now():
                await conn.execute("UPDATE users SET balance_hive = balance_hive + $1 WHERE telegram_id = $2", REFERRAL_BONUS_HIVE, referrer_id)
            
            return dict(row)

class SecurityService:
    @staticmethod
    async def validate_proof(img_bytes: bytes, user_id: int) -> bool:
        """
        Análisis Biométrico de Imágenes (Anti-Fraude).
        Retorna True si detecta duplicidad.
        """
        if not db_pool: return False
        try:
            img = Image.open(BytesIO(img_bytes))
            phash = str(imagehash.phash(img))
            async with db_pool.acquire() as conn:
                exists = await conn.fetchval("SELECT 1 FROM security_hashes WHERE hash_id=$1", phash)
                if exists:
                    logger.warning(f"SECURITY: Duplicate Proof User {user_id}")
                    return True
                await conn.execute("INSERT INTO security_hashes (hash_id, user_id) VALUES ($1, $2)", phash, user_id)
            return False
        except Exception:
            return False

class AdNetworkService:
    @staticmethod
    async def serve_interstitial(update: Update):
        """Publicidad Nativa Inteligente (CTR Optimization)."""
        if random.random() < 0.30:
            ads = [
                {"text": "🔥 **CURSO TRADING ELITE**", "url": LINKS["TRADING"]},
                {"text": "🚀 **CUENTA BINANCE VIP**", "url": LINKS["BINANCE"]},
            ]
            ad = random.choice(ads)
            kb = [[InlineKeyboardButton("👉 VER OFERTA", url=ad["url"])]]
            try:
                await update.message.reply_text(f"📢 **PUBLICIDAD**\n\n{ad['text']}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                await asyncio.sleep(1.2)
            except: pass

async def mining_engine_loop():
    """Motor de Minería Masiva (Batch Processing)."""
    while True:
        await asyncio.sleep(60)
        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    # Actualización masiva eficiente
                    await conn.execute("""
                        UPDATE users 
                        SET balance_hive = balance_hive + (0.1 * mining_power)
                        WHERE rank != 'LARVA' AND mining_active = TRUE
                    """)
            except Exception as e:
                logger.error(f"Mining Error: {e}")

# ==============================================================================
# 5. CONTROLADORES DE TELEGRAM (PARTE A: CORE HANDLERS)
# ==============================================================================

(WAIT_EMAIL, WAIT_PROOF_CPA, WAIT_PROOF_VIP, WAIT_PROOF_FEE, WAIT_VIRAL_LINK, WAIT_PROOF_AFFILIATE) = range(6)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() else None
    
    user_data = await UserManager.get_or_create(user, referrer_id)
    
    if not user_data.get("email"):
        tier_info = REGION_DATA.get(user_data.get('region_tier', 'TIER_3'))
        msg = await update.message.reply_text("🛰️ **INICIANDO ESCANEO DE MERCADO...**")
        await asyncio.sleep(1.0)
        await msg.edit_text(
            f"✅ **UBICACIÓN CONFIRMADA:** {user_data.get('country_code')} {tier_info.get('message', '')}\n"
            f"📊 **POTENCIAL DIARIO:** {tier_info['daily_cap']}\n\n"
            "🧬 **ACTIVACIÓN DE NODO:**\nIngresa tu Email Oficial:"
        )
        return WAIT_EMAIL
    
    await show_dashboard(update, context, user_data)
    return ConversationHandler.END

async def email_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    try:
        validate_email(email)
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("UPDATE users SET email=$1, rank='OBRERO' WHERE telegram_id=$2", email, update.effective_user.id)
        await update.message.reply_text("✅ **SISTEMA ONLINE.**")
        await show_dashboard(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Email inválido.")
        return WAIT_EMAIL

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: Dict = None):
    if not user_data: user_data = await UserManager.get_or_create(update.effective_user)
    await AdNetworkService.serve_interstitial(update)
    
    tier = user_data.get('region_tier', 'TIER_3')
    stats = REGION_DATA.get(tier, REGION_DATA['TIER_3'])
    bal = user_data.get('balance_usd', 0)
    
    proj_week = (bal + stats['opt_projection']) * 7
    
    rank_icon = "👑" if "VIP" in user_data['rank'] else "🐝"
    
    msg = (
        f"💠 **HIVE TITAN OS** | ID: `{user_data['telegram_id']}`\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💵 **USD:** `${bal:.2f}`\n"
        f"🍯 **HIVE:** `{user_data['balance_hive']:.2f}`\n"
        f"🧬 **RANGO:** {rank_icon} {user_data['rank']}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📈 **PROYECCIÓN (7 DÍAS):** `${proj_week:.2f}`\n"
        f"💡 _Tip: Sube a VIP para retirar hoy._\n\n"
        "👇 **PANEL DE CONTROL:**"
    )
    kb = [
        ["🎓 ACADEMY / MARKET", "📱 VIRAL STUDIO"],
        ["🍯 RECOLECTAR (CPA)", "⛏️ MINAR / ADS"],
        ["🧬 EVOLUCIONAR", "💹 P2P DEX"],
        ["🏦 RETIROS", "👤 PERFIL"]
    ]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")
