"""
THEONEHIVE 11.0 - SELF-HEALING ARCHITECTURE
Característica Clave:
Si el bot falla, se reinicia automáticamente para asegurar servicio continuo.
"""

import logging
import os
import sys
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
# ⚙️ CONFIGURACIÓN ROBUSTA
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret_default") 
ADMIN_ID = os.environ.get("ADMIN_ID") 

APP_NAME = "TheOneHive Global"
ASK_EMAIL, ASK_COUNTRY, ASK_WALLET = range(3)

# Economía
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
# 🛡️ SISTEMA DE AUTO-CURACIÓN (SELF-HEALING)
# ---------------------------------------------------------------------
async def check_system_health():
    """Verifica si el cerebro del bot funciona. Si no, fuerza reinicio."""
    try:
        # 1. Probar DB
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
        else:
            raise Exception("DB Pool vacio")
        
        # 2. Probar Telegram
        if telegram_app:
            me = await telegram_app.bot.get_me()
            if not me: raise Exception("Telegram API no responde")
            
        return True
    except Exception as e:
        logger.critical(f"⚠️ FALLO CRÍTICO DE SALUD: {e}")
        logger.critical("🔄 INICIANDO SECUENCIA DE AUTO-REINICIO...")
        # Esto mata el proceso. Render detectará la muerte y creará uno nuevo en 3 segundos.
        os._exit(1) 
        return False

# ---------------------------------------------------------------------
# 🗄️ BASE DE DATOS
# ---------------------------------------------------------------------
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        async with db_pool.acquire() as conn:
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
        logger.info("✅ DB Conectada.")
    except Exception as e:
        logger.error(f"Error DB: {e}")

async def get_user(tg_id: int):
    if not db_pool: return None
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", tg_id)
            return dict(row) if row else None
    except: return None

def get_tier_info(country_code):
    code = str(country_code).upper()
    for tier, data in GEO_ECONOMY.items():
        if code in data["countries"]: return tier, data
    return "TIER_D", GEO_ECONOMY["TIER_D"]

# ---------------------------------------------------------------------
# 💰 LÓGICA DE NEGOCIO (POSTBACK & BOT)
# ---------------------------------------------------------------------
@app.get("/postback")
async def postback_handler(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")
    user_share = amount * 0.40
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", user_share, user_id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)", user_id, user_share, datetime.utcnow().isoformat())
    try:
        bot = await init_bot_app()
        await bot.bot.send_message(chat_id=user_id, text=f"🤑 <b>¡PAGO RECIBIDO!</b>\n+${user_share:.2f}", parse_mode="HTML")
    except: pass
    return {"status": "success"}

async def start_command(update, context):
    context.user_data.clear() # Limpieza preventiva
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_pro(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 <b>TheOneHive Global</b>\n\n📧 <b>Tu Email:</b>", parse_mode="HTML")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 <b>Tu País (2 letras, ej: MX):</b>", parse_mode="HTML")
    return ASK_COUNTRY

async def receive_country(update, context):
    code = update.message.text.upper().strip()
    email = context.user_data.get('email', 'no-mail')
    user = update.effective_user
    tier, _ = get_tier_info(code)
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (telegram_id, first_name, email, country_code, tier, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (telegram_id) DO UPDATE SET email=$3, country_code=$4, tier=$5
            """, user.id, user.first_name, email, code, tier, datetime.utcnow().isoformat())
    await dashboard_pro(update, context)
    return ConversationHandler.END

async def dashboard_pro(update, context):
    user = await get_user(update.effective_user.id)
    if not user: await update.message.reply_text("⚠️ Error de perfil. Usa /start"); return
    _, eco = get_tier_info(user['country_code'])
    msg = (f"📊 <b>DASHBOARD</b> | {user['country_code']}\n💰 Saldo: {eco['symbol']}{user['balance']:.2f}\n🚀 Nivel: {user['tier']}\n\n👇 <b>¿Qué hacemos hoy?</b>")
    kb = [["⚡️ Ofertas", "💸 Retirar"], ["👤 Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    link = f"https://www.offertoro.com/api/?uid={user_id}&pub_id=DEMO"
    kb = [[InlineKeyboardButton("🟢 OfferToro (Apps)", url=link)]]
    await update.message.reply_text("⚡️ <b>ZONA DE GANANCIAS</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def start_withdraw(update, context):
    user = await get_user(update.effective_user.id)
    if not user or user['balance'] < 5.0: await update.message.reply_text(f"⚠️ Mínimo $5.00", parse_mode="HTML"); return ConversationHandler.END
    await update.message.reply_text("💸 <b>Tu Wallet USDT:</b>", parse_mode="HTML")
    return ASK_WALLET

async def process_withdraw(update, context):
    wallet = update.message.text
    user = update.effective_user
    amount = (await get_user(user.id))['balance']
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance = 0 WHERE telegram_id = $1", user.id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'WITHDRAW', $2, $3, 'PENDING', $4)", user.id, amount, wallet, datetime.utcnow().isoformat())
    await update.message.reply_text("✅ Solicitud enviada.", parse_mode="HTML")
    if ADMIN_ID: 
        try: await context.bot.send_message(ADMIN_ID, f"🔔 RETIRO: ${amount} de {user.first_name}") 
        except: pass
    return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("❌ Cancelado."); return ConversationHandler.END

async def handle_text(update, context):
    text = update.message.text
    if "Ofertas" in text: await offerwall_menu(update, context)
    elif "Retirar" in text: await start_withdraw(update, context)
    elif "Perfil" in text: await dashboard_pro(update, context)

# ⚠️ ERROR HANDLER QUE RECUPERA EL FLUJO
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Excepción:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("⚠️ <b>Error interno.</b>\nReiniciando sistema... escribe /start en 5 segundos.", parse_mode="HTML")
            # Forzamos limpieza de estado para ese usuario
            context.user_data.clear()
    except: pass

# ---------------------------------------------------------------------
# 🚀 ARRANQUE
# ---------------------------------------------------------------------
async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Comandos con auto-reinicio
    conv_start = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    conv_withdraw = ConversationHandler(entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)], states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    
    telegram_app.add_handler(conv_start)
    telegram_app.add_handler(conv_withdraw)
    telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

# ✅ ENDPOINT DE SALUD QUE ACTIVA LA AUTO-CURACIÓN
@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    # Aquí hacemos el chequeo real
    is_healthy = await check_system_health()
    if is_healthy:
        return {"status": "ok"}
    else:
        # Esto nunca debería ejecutarse porque check_system_health mata el proceso antes
        raise HTTPException(status_code=500)

@app.get("/")
async def root(): return {"status": "TheOneHive Online"}

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
