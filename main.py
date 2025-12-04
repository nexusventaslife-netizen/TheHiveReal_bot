"""
THEONEHIVE 8.0 - OFFERWALLS & API READY
Novedades:
1. Endpoint '/postback' para recibir notificaciones de AdGem/OfferToro/etc.
2. Automatización de recompensas (Spread automático).
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
# CONFIGURACIÓN & SECRETOS
# ---------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
DATABASE_URL = os.environ.get("DATABASE_URL")
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret123") # <--- CLAVE DE SEGURIDAD PARA TUS APIS

APP_NAME = "TheOneHive 🌍"
ASK_EMAIL, ASK_COUNTRY = range(2)

GEO_ECONOMY = {
    "TIER_A": {"countries": ["US", "AU", "GB", "CA"], "daily_target": 25.0, "symbol": "$"},
    "TIER_B": {"countries": ["ES", "DE", "FR", "IT"], "daily_target": 20.0, "symbol": "€"},
    "TIER_C": {"countries": ["MX", "AR", "CO", "BR"], "daily_target": 15.0, "symbol": "$"},
    "TIER_D": {"countries": ["GLOBAL", "VE", "NG"], "daily_target": 6.0, "symbol": "$"}
}

app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None
db_pool: Optional[asyncpg.Pool] = None

# ---------------------------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------------------------
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        # Tablas ya creadas en v7.0, solo aseguramos conexión
        # Si necesitas borrar todo de nuevo para pruebas, descomenta:
        # await conn.execute("DROP TABLE IF EXISTS users CASCADE;")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                email TEXT,
                country_code TEXT,
                tier TEXT,
                balance DOUBLE PRECISION DEFAULT 0.0,
                xp INTEGER DEFAULT 0,
                performance_multiplier DOUBLE PRECISION DEFAULT 1.0,
                created_at TEXT
            )
        """)
    logger.info("✅ DB Conectada.")

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
# 🔥 NUEVO: SISTEMA DE POSTBACK (AUTOMATIZACIÓN DE PAGOS EXTERNOS)
# ---------------------------------------------------------------------
@app.get("/postback")
async def postback_handler(
    user_id: int,      # ID del usuario (Telegram ID)
    amount: float,     # Cuanto paga la red (ej: 5.00)
    secret: str,       # Clave de seguridad
    trans_id: str      # ID de transacción única
):
    """
    Este link se le da a OfferToro/AdGem.
    Ellos lo llaman automáticamente cuando alguien completa una tarea.
    URL ejemplo: https://tu-bot.onrender.com/postback?user_id=123&amount=5.0&secret=secret123&trans_id=abc
    """
    
    # 1. Seguridad: Verificar que quien llama es la empresa real
    if secret != POSTBACK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")

    # 2. Lógica de Comisión (SPREAD)
    # Nos pagan 'amount', nosotros damos el 40% al usuario
    user_share = amount * 0.40  
    company_share = amount * 0.60 # Esto es TU ganancia automática

    # 3. Acreditar al usuario en DB
    async with db_pool.acquire() as conn:
        # Actualizar saldo
        await conn.execute(
            "UPDATE users SET balance = balance + $1, xp = xp + 100 WHERE telegram_id = $2",
            user_share, user_id
        )
        # Registrar transacción (Opcional: crear tabla transacciones)
    
    # 4. Notificar al usuario en Telegram
    try:
        bot = await init_bot_app()
        msg = (
            f"💰 **¡TAREA COMPLETADA!**\n\n"
            f"Has recibido: **${user_share:.2f}**\n"
            f"Comisión de Red: ${amount:.2f} (Procesado)\n"
            f"XP Ganada: +100 XP\n\n"
            "¡Sigue así para alcanzar tu meta diaria!"
        )
        await bot.bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"No se pudo notificar al usuario {user_id}: {e}")

    return {"status": "ok", "payout_processed": user_share}

# ---------------------------------------------------------------------
# BOT HANDLERS (Igual que v7.0)
# ---------------------------------------------------------------------
async def start_command(update, context):
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_pro(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 **TheOneHive Global**\nConfiguración inicial.\n📧 **1. Tu Email:**")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 **2. Tu País (código 2 letras):**")
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

async def cancel(update, context): await update.message.reply_text("❌"); return ConversationHandler.END

async def dashboard_pro(update, context):
    user = await get_user(update.effective_user.id)
    if not user: return
    _, eco = get_tier_info(user['country_code'])
    daily = eco['daily_target'] * user['performance_multiplier']
    
    msg = (
        f"📊 **DASHBOARD** | {user['country_code']}\n"
        f"💰 Saldo: {eco['symbol']}{user['balance']:.2f}\n"
        f"🎯 Meta Diaria: {eco['symbol']}{daily:.2f}\n\n"
        "👇 Selecciona:"
    )
    kb = [["⚡️ Muro de Ofertas (Auto)", "💸 Retirar"], ["🌍 Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

# Aquí cambiamos 'Optimized Tasks' por 'Offerwalls'
async def offerwall_menu(update, context):
    # Aquí pondrías tus links de OfferToro/AdGem reales
    # Ejemplo: Link con el ID del usuario para rastrearlo
    user_id = update.effective_user.id
    
    # Link simulado de un Offerwall
    offer_link = f"https://www.offertoro.com/api/?uid={user_id}&pub_id=TU_ID"
    
    msg = "⚡️ **MUROS DE OFERTAS AUTOMÁTICOS**\n\nSelecciona un proveedor para ver cientos de tareas:"
    kb = [
        [InlineKeyboardButton("🟢 OfferToro (Apps & Juegos)", url=offer_link)],
        [InlineKeyboardButton("🔵 AdGem (Videos)", url=offer_link)],
        [InlineKeyboardButton("🟡 CPALead (Encuestas)", url=offer_link)]
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def handle_text(update, context):
    text = update.message.text
    if "Ofertas" in text: await offerwall_menu(update, context)
    elif "Retirar" in text: await update.message.reply_text("💸 Retiros en USDT/Binance (Procesamiento 24h).")
    elif "Perfil" in text: await dashboard_pro(update, context)

async def error_handler(update, context): logger.error(msg="Error:", exc_info=context.error)

async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel)])
    telegram_app.add_handler(conv)
    telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

@app.get("/")
async def root(): return {"status": "Online"}
@app.get("/health")
async def health(): return {"status": "ok"}

@app.on_event("startup")
async def startup(): await init_db(); bot=await init_bot_app(); await bot.start(); 
@app.on_event("shutdown")
async def shutdown(): 
    if telegram_app: await telegram_app.stop(); await telegram_app.shutdown()
    if db_pool: await db_pool.close()
@app.post("/telegram/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN: return JSONResponse(status_code=403, content={})
    data = await request.json(); bot=await init_bot_app(); await bot.process_update(Update.de_json(data, bot.bot)); return {"ok":True}
