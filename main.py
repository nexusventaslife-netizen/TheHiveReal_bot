"""
THEONEHIVE 12.0 - CRYPTO ECOSYSTEM
Novedades:
1. Motor de Tokens (HiveCoin) y NFTs Invisibles (Database Assets).
2. Sistema de Inventario Digital.
3. Conexión OfferToro arreglada con Variables de Entorno.
4. Auto-Healing (Si falla, revive).
"""

import logging
import os
import sys
import asyncio
from datetime import datetime
from typing import Optional, List

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

# OFFERTORO CREDENTIALS (DESDE RENDER)
OFFERTORO_PUB_ID = os.environ.get("OFFERTORO_PUB_ID", "0")
OFFERTORO_SECRET = os.environ.get("OFFERTORO_SECRET", "0")

APP_NAME = "TheOneHive Crypto"
ASK_EMAIL, ASK_COUNTRY, ASK_WALLET = range(3)

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
# 🛡️ AUTO-HEALING
# ---------------------------------------------------------------------
async def check_system_health():
    try:
        if db_pool:
            async with db_pool.acquire() as conn: await conn.execute("SELECT 1")
        else: raise Exception("DB Down")
        return True
    except:
        logger.critical("REINICIANDO SISTEMA...")
        os._exit(1)
        return False

# ---------------------------------------------------------------------
# 🗄️ BASE DE DATOS (AHORA CON CRYPTO ASSETS)
# ---------------------------------------------------------------------
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        async with db_pool.acquire() as conn:
            # Tabla Usuarios (Con saldo HIVE Tokens)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    email TEXT,
                    country_code TEXT,
                    tier TEXT,
                    balance DOUBLE PRECISION DEFAULT 0.0,
                    hive_tokens DOUBLE PRECISION DEFAULT 0.0, -- NUEVO: TU TOKEN
                    wallet_address TEXT,
                    created_at TEXT
                )
            """)
            # Tabla NFTs / Inventario
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nfts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    name TEXT,
                    rarity TEXT, -- Common, Rare, Legendary
                    image_url TEXT,
                    minted_at TEXT
                )
            """)
            # Transacciones
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
        logger.info("✅ DB Crypto Ready.")
    except Exception as e: logger.error(f"DB Error: {e}")

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
# 💎 MOTOR DE TOKENS Y NFTs (MINERÍA VIRTUAL)
# ---------------------------------------------------------------------
async def mint_invisible_assets(user_id: int, dollar_amount: float):
    """
    Cada vez que el usuario gana Dólares, 'mina' tokens HIVE y genera NFTs.
    """
    # 1. Calcular Tokens: Por cada $1 ganado, minan 10 HIVE Coins
    tokens_mined = dollar_amount * 10 
    
    async with db_pool.acquire() as conn:
        # Sumar Tokens
        await conn.execute("UPDATE users SET hive_tokens = hive_tokens + $1 WHERE telegram_id = $2", tokens_mined, user_id)
        
        # 2. Lógica NFT (Ejemplo: Si gana más de $5 de golpe, recibe un NFT Raro)
        if dollar_amount >= 2.0:
            nft_name = "Hive Miner Badge 🥉"
            await conn.execute("""
                INSERT INTO nfts (user_id, name, rarity, image_url, minted_at)
                VALUES ($1, $2, 'Common', 'https://example.com/badge.png', $3)
            """, user_id, nft_name, datetime.utcnow().isoformat())
            return tokens_mined, True # True = Ganó NFT
            
    return tokens_mined, False

# ---------------------------------------------------------------------
# 💰 POSTBACK CON MINERÍA
# ---------------------------------------------------------------------
@app.get("/postback")
async def postback_handler(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")

    user_share = amount * 0.40 # Spread 40/60
    
    # Actualizar Saldo USD
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", user_share, user_id)
        await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)", user_id, user_share, datetime.utcnow().isoformat())

    # 🔥 ACTIVAR MINERÍA CRYPTO
    tokens, won_nft = await mint_invisible_assets(user_id, user_share)

    # Notificar
    try:
        bot = await init_bot_app()
        nft_msg = "\n🏆 <b>¡NUEVO NFT DESBLOQUEADO!</b>" if won_nft else ""
        msg = (
            f"🤑 <b>¡TAREA PAGADA!</b>\n"
            f"💵 USD: +${user_share:.2f}\n"
            f"💎 HIVE: +{tokens:.2f} (Minado){nft_msg}"
        )
        await bot.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
    except: pass
    
    return {"status": "success"}

# ---------------------------------------------------------------------
# 🤖 BOT INTERFACE
# ---------------------------------------------------------------------
async def start_command(update, context):
    context.user_data.clear()
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_pro(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 <b>TheOneHive Crypto</b>\n\n📧 <b>Tu Email:</b>", parse_mode="HTML")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 <b>País (2 letras):</b>", parse_mode="HTML")
    return ASK_COUNTRY

async def receive_country(update, context):
    code = update.message.text.upper().strip()
    email = context.user_data.get('email')
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
    if not user: await update.message.reply_text("⚠️ /start"); return
    _, eco = get_tier_info(user['country_code'])
    
    # Mostrar Saldo USD y Saldo TOKEN
    msg = (
        f"📊 <b>DASHBOARD WEB3</b> | {user['country_code']}\n\n"
        f"💵 <b>Saldo Fiat:</b> {eco['symbol']}{user['balance']:.2f}\n"
        f"💎 <b>HiveCoin:</b> {user.get('hive_tokens', 0):.2f} $HIVE\n"
        f"🚀 <b>Nivel:</b> {user['tier']}\n\n"
        "👇 <b>Selecciona:</b>"
    )
    kb = [["⚡️ Ofertas (Minar)", "🎒 Mis NFTs"], ["💸 Retirar", "👤 Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

async def show_inventory(update, context):
    user_id = update.effective_user.id
    if db_pool:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM nfts WHERE user_id = $1", user_id)
            
    if not rows:
        await update.message.reply_text("🎒 <b>Inventario Vacío</b>\nCompleta tareas para ganar NFTs.", parse_mode="HTML")
        return

    msg = "🏆 <b>TUS ACTIVOS DIGITALES</b>\n\n"
    for nft in rows:
        msg += f"• <b>{nft['name']}</b> ({nft['rarity']})\n"
        
    await update.message.reply_text(msg, parse_mode="HTML")

async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    # USAMOS LAS VARIABLES DE ENTORNO REALES
    pub_id = os.environ.get("OFFERTORO_PUB_ID", "0") 
    secret_key = os.environ.get("OFFERTORO_SECRET", "0")
    
    link_toro = f"https://www.offertoro.com/ifr/show/{pub_id}/{user_id}/{secret_key}"
    
    msg = "⚡️ <b>MINERÍA DE TAREAS</b>\nCompleta acciones para ganar USD + HIVE Tokens."
    kb = [[InlineKeyboardButton("🟢 Abrir OfferToro", url=link_toro)]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def start_withdraw(update, context):
    user = await get_user(update.effective_user.id)
    if user['balance'] < 5.0: await update.message.reply_text(f"⚠️ Mínimo $5.00", parse_mode="HTML"); return ConversationHandler.END
    await update.message.reply_text("💸 <b>Wallet USDT (TRC20):</b>", parse_mode="HTML")
    return ASK_WALLET

async def process_withdraw(update, context):
    wallet = update.message.text
    user = update.effective_user
    amount = (await get_user(user.id))['balance']
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance = 0 WHERE telegram_id = $1", user.id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'WITHDRAW', $2, $3, 'PENDING', $4)", user.id, amount, wallet, datetime.utcnow().isoformat())
    
    # Mensaje de éxito con Upsell Crypto
    await update.message.reply_text("✅ <b>Retiro en Proceso</b>\nTus HIVE Tokens se mantienen en tu cuenta (Staking automático).", parse_mode="HTML")
    
    if ADMIN_ID: 
        try: await context.bot.send_message(ADMIN_ID, f"🔔 RETIRO: ${amount} - {user.first_name}") 
        except: pass
    return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("❌"); return ConversationHandler.END

async def handle_text(update, context):
    text = update.message.text
    if "Ofertas" in text: await offerwall_menu(update, context)
    elif "Retirar" in text: await start_withdraw(update, context)
    elif "Perfil" in text: await dashboard_pro(update, context)
    elif "NFTs" in text: await show_inventory(update, context)

async def error_handler(update, context):
    logger.error(msg="Error:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("⚠️ Error interno. Escribe /start", parse_mode="HTML")
            context.user_data.clear()
    except: pass

# ---------------------------------------------------------------------
# 🚀 STARTUP
# ---------------------------------------------------------------------
async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv_s = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    conv_w = ConversationHandler(entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)], states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    
    telegram_app.add_handler(conv_s)
    telegram_app.add_handler(conv_withdraw)
    telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    if await check_system_health(): return {"status": "ok"}
    else: raise HTTPException(500)

@app.get("/")
async def root(): return {"status": "TheOneHive Crypto Online"}

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
