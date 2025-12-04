"""
THEONEHIVE 9.5 - STABLE PRODUCTION
Correcciones:
1. Formato HTML para evitar errores con guiones bajos (_) en TIERs.
2. Integración completa de Offerwalls, Postback y Retiros.
3. Base de Datos persistente en PostgreSQL.
"""

import logging
import os
import asyncio
from datetime import datetime
from typing import Optional

# Librerías
import asyncpg 
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# ---------------------------------------------------------------------
# ⚙️ CONFIGURACIÓN
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret_default") 
ADMIN_ID = os.environ.get("ADMIN_ID") 
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

APP_NAME = "TheOneHive 🌍"

# Estados de Conversación
ASK_EMAIL, ASK_COUNTRY, ASK_WALLET = range(3)

# Configuración Económica
GEO_ECONOMY = {
    "TIER_A": {"countries": ["US", "AU", "GB", "CA"], "symbol": "$"},
    "TIER_B": {"countries": ["ES", "DE", "FR", "IT"], "symbol": "€"},
    "TIER_C": {"countries": ["MX", "AR", "CO", "BR"], "symbol": "$"},
    "TIER_D": {"countries": ["GLOBAL", "VE", "NG"], "symbol": "$"}
}

app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None
db_pool: Optional[asyncpg.Pool] = None

# ---------------------------------------------------------------------
# 🗄️ BASE DE DATOS MAESTRA
# ---------------------------------------------------------------------
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        # 1. Tabla Usuarios
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                email TEXT,
                country_code TEXT,
                tier TEXT,
                balance DOUBLE PRECISION DEFAULT 0.0,
                wallet_address TEXT,
                performance_multiplier DOUBLE PRECISION DEFAULT 1.0,
                created_at TEXT
            )
        """)
        # 2. Tabla Transacciones
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                type TEXT,
                amount DOUBLE PRECISION,
                source TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
    logger.info("✅ DB Conectada y Esquema Verificado.")

async def get_user(tg_id: int):
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", tg_id)
        return dict(row) if row else None

def get_tier_info(country_code):
    code = str(country_code).upper()
    for tier, data in GEO_ECONOMY.items():
        if code in data["countries"]: return tier, data
    return "TIER_D", GEO_ECONOMY["TIER_D"]

# ---------------------------------------------------------------------
# 💰 POSTBACK (AUTOMATIZACIÓN DE PAGOS)
# ---------------------------------------------------------------------
@app.get("/postback")
async def postback_handler(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")

    # SPREAD: 40% Usuario / 60% Empresa
    user_share = amount * 0.40
    
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", user_share, user_id)
        await conn.execute("""
            INSERT INTO transactions (user_id, type, amount, source, status, created_at)
            VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)
        """, user_id, user_share, datetime.utcnow().isoformat())

    try:
        bot = await init_bot_app()
        await bot.bot.send_message(chat_id=user_id, text=f"🤑 <b>¡TAREA PAGADA!</b>\nHas ganado: +${user_share:.2f}", parse_mode="HTML")
    except: pass
    
    return {"status": "success", "payout": user_share}

# ---------------------------------------------------------------------
# 🤖 BOT HANDLERS
# ---------------------------------------------------------------------
async def start_command(update, context):
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_pro(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 <b>TheOneHive Global</b>\nConfiguración inicial.\n📧 <b>1. Tu Email:</b>", parse_mode="HTML")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 <b>2. Tu País (código 2 letras):</b>\nEj: MX, US, ES, VE", parse_mode="HTML")
    return ASK_COUNTRY

async def receive_country(update, context):
    code = update.message.text.upper().strip()
    email = context.user_data['email']
    user = update.effective_user
    tier, _ = get_tier_info(code)
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, email, country_code, tier, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (telegram_id) DO UPDATE SET email=$3, country_code=$4, tier=$5
        """, user.id, user.first_name, email, code, tier, datetime.utcnow().isoformat())
    
    await dashboard_pro(update, context)
    return ConversationHandler.END

# --- DASHBOARD SEGURO (HTML) ---
async def dashboard_pro(update, context):
    user = await get_user(update.effective_user.id)
    if not user: return
    _, eco = get_tier_info(user['country_code'])
    
    # Usamos HTML para que 'TIER_A' no rompa el mensaje
    msg = (
        f"📊 <b>DASHBOARD</b> | {user['country_code']}\n"
        f"💰 Saldo: {eco['symbol']}{user['balance']:.2f}\n"
        f"🚀 Nivel: {user['tier']}\n\n"
        "👇 <b>¿Qué quieres hacer hoy?</b>"
    )
    kb = [["⚡️ Muro de Ofertas", "💸 Retirar Saldo"], ["👤 Mi Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

# --- OFERTAS ---
async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    # Pon tus links reales aquí
    link_toro = f"https://www.offertoro.com/api/?uid={user_id}&pub_id=TU_ID"
    link_adgem = f"https://api.adgem.com/v1/wall?playerid={user_id}&appid=TU_ID"
    
    msg = "⚡️ <b>ZONA DE GANANCIAS AUTOMÁTICAS</b>\nElige un proveedor:"
    kb = [
        [InlineKeyboardButton("🟢 OfferToro (Juegos & Apps)", url=link_toro)],
        [InlineKeyboardButton("🔵 AdGem (Videos & Encuestas)", url=link_adgem)]
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# --- RETIROS ---
async def start_withdraw(update, context):
    user = await get_user(update.effective_user.id)
    if user['balance'] < 5.0:
        await update.message.reply_text(f"⚠️ <b>Saldo Insuficiente</b>\nMínimo: $5.00\nTienes: ${user['balance']:.2f}", parse_mode="HTML")
        return ConversationHandler.END
    
    await update.message.reply_text("💸 <b>SOLICITUD DE RETIRO</b>\n\nIngresa tu dirección USDT (TRC20) o Email Binance:", parse_mode="HTML")
    return ASK*

