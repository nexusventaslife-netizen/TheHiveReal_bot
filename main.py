"""
THEONEHIVE 9.0 - MASTER SYSTEM
Integración Total: Offerwalls + Postback + Retiros + DB Financiera + Tiers
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
ADMIN_ID = os.environ.get("ADMIN_ID") # Tu ID para recibir alertas
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

APP_NAME = "TheOneHive 🌍"

# Estados de Conversación
ASK_EMAIL, ASK_COUNTRY, ASK_WALLET = range(3)

# Configuración Económica (Dignidad Global)
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
        # 2. Tabla Transacciones (Historial Financiero)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                type TEXT, -- 'EARN' (Ganancia) o 'WITHDRAW' (Retiro)
                amount DOUBLE PRECISION,
                source TEXT, -- 'OfferToro', 'Binance', etc.
                status TEXT, -- 'COMPLETED', 'PENDING'
                created_at TEXT
            )
        """)
    logger.info("✅ Sistema Financiero DB 9.0 Activo.")

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
# 💰 AUTOMATIZACIÓN DE PAGOS (POSTBACK)
# ---------------------------------------------------------------------
@app.get("/postback")
async def postback_handler(user_id: int, amount: float, secret: str, trans_id: str):
    """Recibe dinero de Offerwalls (OfferToro/AdGem)"""
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")

    # SPREAD: 40% Usuario / 60% Empresa
    user_share = amount * 0.40
    
    async with db_pool.acquire() as conn:
        # Sumar saldo al usuario
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", user_share, user_id)
        # Registrar transacción
        await conn.execute("""
            INSERT INTO transactions (user_id, type, amount, source, status, created_at)
            VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)
        """, user_id, user_share, datetime.utcnow().isoformat())

    # Notificar al Usuario
    try:
        bot = await init_bot_app()
        await bot.bot.send_message(chat_id=user_id, text=f"🤑 **¡TAREA PAGADA!**\nHas ganado: +${user_share:.2f}\n(Comisión red procesada).")
    except: pass
    
    return {"status": "success", "payout": user_share}

# ---------------------------------------------------------------------
# 🤖 BOT: FLUJO DE USUARIO
# ---------------------------------------------------------------------
async def start_command(update, context):
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_pro(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 **TheOneHive Global**\nConfiguración inicial.\n📧 **1. Tu Email:**")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 **2. Tu País (código 2 letras):**\nEj: MX, US, ES, VE")
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

# --- DASHBOARD ---
async def dashboard_pro(update, context):
    user = await get_user(update.effective_user.id)
    if not user: return
    _, eco = get_tier_info(user['country_code'])
    
    msg = (
        f"📊 **DASHBOARD** | {user['country_code']}\n"
        f"💰 Saldo: {eco['symbol']}{user['balance']:.2f}\n"
        f"🚀 Nivel: {user['tier']}\n\n"
        "👇 **¿Qué quieres hacer hoy?**"
    )
    kb = [["⚡️ Muro de Ofertas", "💸 Retirar Saldo"], ["👤 Mi Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

# --- MURO DE OFERTAS (LINK DINÁMICO) ---
async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    # AQUÍ PONES TU URL REAL DE OFFERTORO/ADGEM
    # El parámetro {user_id} es vital para saber a quién pagarle
    link_toro = f"https://www.offertoro.com/api/?uid={user_id}&pub_id=PON_TU_ID_AQUI"
    link_adgem = f"https://api.adgem.com/v1/wall?playerid={user_id}&appid=PON_TU_ID_AQUI"
    
    msg = "⚡️ **ZONA DE GANANCIAS AUTOMÁTICAS**\nElige un proveedor:"
    kb = [
        [InlineKeyboardButton("🟢 OfferToro (Juegos & Apps)", url=link_toro)],
        [InlineKeyboardButton("🔵 AdGem (Videos & Encuestas)", url=link_adgem)]
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

# --- SISTEMA DE RETIROS ---
async def start_withdraw(update, context):
    user = await get_user(update.effective_user.id)
    if user['balance'] < 5.0:
        await update.message.reply_text(f"⚠️ **Saldo Insuficiente**\nMínimo para retirar: $5.00\nTienes: ${user['balance']:.2f}")
        return ConversationHandler.END
    
    await update.message.reply_text("💸 **SOLICITUD DE RETIRO**\n\nIngresa tu dirección de **USDT (TRC20)** o Email de **Binance**:")
    return ASK_WALLET

async def process_withdraw(update, context):
    wallet = update.message.text
    user = update.effective_user
    user_data = await get_user(user.id)
    amount = user_data['balance']
    
    async with db_pool.acquire() as conn:
        # 1. Restar saldo (para que no retire doble)
        await conn.execute("UPDATE users SET balance = 0 WHERE telegram_id = $1", user.id)
        # 2. Registrar Transacción Pendiente
        await conn.execute("""
            INSERT INTO transactions (user_id, type, amount, source, status, created_at)
            VALUES ($1, 'WITHDRAW', $2, $3, 'PENDING', $4)
        """, user.id, amount, wallet, datetime.utcnow().isoformat())

    # Notificar al Admin (TÚ) si está configurado
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID, 
                text=f"🔔 **NUEVO RETIRO**\nUsuario: {user.first_name} (ID: {user.id})\nMonto: ${amount:.2f}\nWallet: `{wallet}`"
            )
        except: pass

    await update.message.reply_text("✅ **Solicitud Recibida**\nTu pago está en proceso (24h).")
    return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("❌"); return ConversationHandler.END

# --- HANDLERS TEXTO ---
async def handle_text(update, context):
    text = update.message.text
    if "Ofertas" in text: await offerwall_menu(update, context)
    elif "Retirar" in text: await start_withdraw(update, context) # Ahora inicia flujo real
    elif "Perfil" in text: await dashboard_pro(update, context)

async def error_handler(update, context): logger.error(msg="Error:", exc_info=context.error)

# ---------------------------------------------------------------------
# 🚀 STARTUP
# ---------------------------------------------------------------------
async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversaciones
    conv_start = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    conv_withdraw = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)],
        states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    telegram_app.add_handler(conv_start)
    telegram_app.add_handler(conv_withdraw)
    telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

@app.get("/")
async def root(): return {"status": "TheOneHive System Online 🟢"}
@app.get("/health")
async def health(): return {"status": "ok"}

@app.on_event("startup")
async def startup(): await init_db(); bot=await init_bot_app(); await bot.start() 
@app.on_event("shutdown")
async def shutdown(): 
    if telegram_app: await telegram_app.stop(); await telegram_app.shutdown()
    if db_pool: await db_pool.close()

@app.post("/telegram/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN: return JSONResponse(status_code=403, content={})
    data = await request.json(); bot=await init_bot_app(); await bot.process_update(Update.de_json(data, bot.bot)); return {"ok":True}
