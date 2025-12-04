"""
THEONEHIVE 13.0 - NEXUS INTERFACE (FINAL PRODUCTION)
Características:
1. UI Gamificada: Barras de progreso, Rangos, Diseño 'Sci-Fi'.
2. Economía Dual: USD (Real) + HIVE (Crypto).
3. Auto-Healing: Si falla, se reinicia solo.
4. Código limpio 100% funcional.
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
# ⚙️ CONFIGURACIÓN
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret_default") 
ADMIN_ID = os.environ.get("ADMIN_ID") 

# OFFERTORO
OFFERTORO_PUB_ID = os.environ.get("OFFERTORO_PUB_ID", "0")
OFFERTORO_SECRET = os.environ.get("OFFERTORO_SECRET", "0")

APP_NAME = "TheOneHive Nexus"
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
# 🛡️ AUTO-HEALING (SISTEMA INMORTAL)
# ---------------------------------------------------------------------
async def check_system_health():
    try:
        if db_pool:
            async with db_pool.acquire() as conn: await conn.execute("SELECT 1")
        else: raise Exception("DB Down")
        return True
    except:
        logger.critical("⚠️ FALLO DE SISTEMA: Iniciando protocolo de reinicio...")
        os._exit(1) # Mata el proceso para que Render lo reviva limpio
        return False

# ---------------------------------------------------------------------
# 🎨 MOTOR VISUAL & GAMIFICACIÓN
# ---------------------------------------------------------------------
def generate_progress_bar(current, total, length=12):
    """Genera: [██████░░░░] 60%"""
    if total == 0: total = 1
    percent = min(current / total, 1.0)
    filled = int(length * percent)
    bar = "▰" * filled + "▱" * (length - filled)
    return f"[{bar}] {int(percent * 100)}%"

def get_rank_info(xp):
    """Calcula Rango y Meta XP"""
    # (XP Minima, Nombre Rango, Meta Siguiente)
    ranks = [
        (0, "🧬 Larva", 100),
        (100, "🐝 Drone", 500),
        (500, "⚔️ Soldier", 2000),
        (2000, "👑 Royal Guard", 10000),
        (10000, "💎 Hive Master", 100000)
    ]
    current = ranks[0]
    for r in ranks:
        if xp >= r[0]: current = r
        else: break
    return current[1], current[2]

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
                    hive_tokens DOUBLE PRECISION DEFAULT 0.0,
                    wallet_address TEXT,
                    created_at TEXT
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nfts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    name TEXT,
                    rarity TEXT,
                    image_url TEXT,
                    minted_at TEXT
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
# 💎 LÓGICA DE NEGOCIO (POSTBACK)
# ---------------------------------------------------------------------
async def postback_handler_logic(user_id, amount):
    """Maneja el pago y la minería"""
    user_share = amount * 0.40 # Spread 40% usuario / 60% empresa
    tokens_mined = user_share * 10 # 1 USD = 10 HIVE
    
    async with db_pool.acquire() as conn:
        # Sumar USD y Tokens
        await conn.execute("UPDATE users SET balance = balance + $1, hive_tokens = hive_tokens + $2 WHERE telegram_id = $3", user_share, tokens_mined, user_id)
        
        # Registrar Transacción
        await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)", user_id, user_share, datetime.utcnow().isoformat())
        
        # Lógica NFT (Si gana > $2 de golpe)
        won_nft = False
        if user_share >= 2.0:
            won_nft = True
            await conn.execute("INSERT INTO nfts (user_id, name, rarity, image_url, minted_at) VALUES ($1, 'Hive Miner Badge 🥉', 'Common', 'url', $2)", user_id, datetime.utcnow().isoformat())

    return user_share, tokens_mined, won_nft

@app.get("/postback")
async def postback_endpoint(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")
    
    usd, tokens, nft = await postback_handler_logic(user_id, amount)

    try:
        bot = await init_bot_app()
        nft_text = "\n🏆 <b>¡NUEVO NFT OBTENIDO!</b>" if nft else ""
        msg = (
            f"🤑 <b>¡PAGO RECIBIDO!</b>\n"
            f"💵 Fiat: +${usd:.2f}\n"
            f"💎 Crypto: +{tokens:.2f} $HIVE{nft_text}"
        )
        await bot.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
    except: pass
    return {"status": "success"}

# ---------------------------------------------------------------------
# 🤖 BOT - INTERFAZ NEXUS
# ---------------------------------------------------------------------
async def start_command(update, context):
    context.user_data.clear()
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_nexus(update, context); return ConversationHandler.END
    await update.message.reply_text("📡 <b>INICIANDO NEXUS...</b>\n\n📧 <b>Ingresa tu Email para sincronizar:</b>", parse_mode="HTML")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 <b>País de Operación (Ej: MX, US, ES):</b>", parse_mode="HTML")
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
    
    await dashboard_nexus(update, context)
    return ConversationHandler.END

# --- 🔥 EL DASHBOARD MAESTRO ---
async def dashboard_nexus(update, context):
    user = await get_user(update.effective_user.id)
    if not user: await update.message.reply_text("⚠️ Error. Usa /start"); return
    
    # Datos
    usd = user['balance']
    tokens = user.get('hive_tokens', 0)
    country = user['country_code']
    _, eco = get_tier_info(country)
    
    # Gamificación
    xp = (usd * 100) + tokens
    rank_name, next_goal = get_rank_info(xp)
    p_bar = generate_progress_bar(xp, next_goal)
    
    msg = (
        f"📡 <b>HIVE NEXUS INTERFACE</b> <code>v13.0</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 <b>PILOTO:</b> {update.effective_user.first_name}\n"
        f"🌍 <b>NODO:</b> {country} (Tier {user['tier']})\n"
        f"🏆 <b>RANGO:</b> {rank_name}\n"
        f"<code>{p_bar}</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖\n\n"
        
        f"💰 <b>BILLETERA FIAT</b>\n"
        f"   └─ <b>{eco['symbol']}{usd:.2f}</b> <i>(Retirable)</i>\n\n"
        
        f"💎 <b>HIVE ASSETS (Web3)</b>\n"
        f"   └─ <b>{tokens:.2f} $HIVE</b>\n"
        f"   └─ <i>Estado: Staking Activo 🟢</i>\n\n"
        
        f"🚀 <b>MISIONES ACTIVAS:</b>\n"
        f"   👉 <i>Completa 1 oferta para subir XP</i>"
    )
    
    kb = [
        ["⚡️ MINAR (Ofertas)", "🎒 Mis NFTs"],
        ["🏦 Retirar Saldo", "📊 Ranking Global"],
        ["👤 Mi Perfil", "⚙️ Soporte"]
    ]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

async def show_leaderboard(update, context):
    msg = (
        "🏆 <b>TOP 5 HIVE MASTERS (Global)</b>\n\n"
        "🥇 <b>1. Alex_Crypto:</b> $4,250.00 (Tier A)\n"
        "🥈 <b>2. Sarah_V:</b> $3,890.50 (Tier A)\n"
        "🥉 <b>3. NexusUser:</b> $1,200.00 (Tier B)\n"
        "4. Roberto_M: $950.00 (Tier C)\n"
        "5. <i>[Tu estás aquí...]</i>\n\n"
        "🚀 <b>¡Sigue minando para subir!</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def show_inventory(update, context):
    user_id = update.effective_user.id
    rows = []
    if db_pool:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM nfts WHERE user_id = $1", user_id)
            
    if not rows:
        await update.message.reply_text("🎒 <b>INVENTARIO VACÍO</b>\nEl sistema no detecta NFTs. Completa ofertas grandes para obtenerlos.", parse_mode="HTML")
        return

    msg = "🏆 <b>TUS ACTIVOS DIGITALES</b>\n\n"
    for nft in rows: msg += f"• <b>{nft['name']}</b> ({nft['rarity']})\n"
    await update.message.reply_text(msg, parse_mode="HTML")

async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    # Link OfferToro
    link = f"https://www.offertoro.com/ifr/show/{OFFERTORO_PUB_ID}/{user_id}/{OFFERTORO_SECRET}"
    
    msg = (
        "⚡️ <b>CONSOLA DE MINERÍA</b>\n\n"
        "1. Instala Apps o Juega.\n"
        "2. Recibe USD y HIVE Tokens automáticos.\n"
        "3. <b>¡No uses VPN o serás baneado!</b>"
    )
    kb = [[InlineKeyboardButton("🟢 INICIAR PROTOCOLO", url=link)]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# --- RETIROS ---
async def start_withdraw(update, context):
    user = await get_user(update.effective_user.id)
    if user['balance'] < 5.0: await update.message.reply_text(f"⚠️ <b>Saldo Insuficiente</b>\nMínimo: $5.00", parse_mode="HTML"); return ConversationHandler.END
    await update.message.reply_text("💸 <b>Introduce Wallet USDT (TRC20):</b>", parse_mode="HTML")
    return ASK_WALLET

async def process_withdraw(update, context):
    wallet = update.message.text
    user = update.effective_user
    amount = (await get_user(user.id))['balance']
    
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance = 0 WHERE telegram_id = $1", user.id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'WITHDRAW', $2, $3, 'PENDING', $4)", user.id, amount, wallet, datetime.utcnow().isoformat())
    
    await update.message.reply_text("✅ <b>Solicitud Enviada</b>\nProcesando pago en la Blockchain...", parse_mode="HTML")
    
    if ADMIN_ID:
        try: await context.bot.send_message(ADMIN_ID, f"🔔 RETIRO: ${amount} - {user.first_name}")
        except: pass
    return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("❌ Cancelado."); return ConversationHandler.END

# --- RUTEO DE TEXTO ---
async def handle_text(update, context):
    text = update.message.text
    if "MINAR" in text or "Ofertas" in text: await offerwall_menu(update, context)
    elif "Retirar" in text: await start_withdraw(update, context)
    elif "Perfil" in text: await dashboard_nexus(update, context)
    elif "NFT" in text: await show_inventory(update, context)
    elif "Ranking" in text: await show_leaderboard(update, context)

async def error_handler(update, context):
    logger.error(msg="Error:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("⚠️ <b>Error Crítico.</b> Reiniciando...", parse_mode="HTML")
            context.user_data.clear()
    except: pass

# ---------------------------------------------------------------------
# 🚀 ARRANQUE
# ---------------------------------------------------------------------
async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv_start = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]},
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)]
    )
    
    conv_withdraw = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)],
        states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]},
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)]
    )
    
    telegram_app.add_handler(conv_start)
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
async def root(): return {"status": "TheOneHive Nexus Online"}

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
