"""
THEONEHIVE 14.0 - REFERRAL GROWTH EDITION
Novedad Principal:
Sistema de Referidos Multinivel (1 Nivel).
- Gana 10% de lo que generen tus amigos.
- Enlaces de invitación únicos.
- Base de Datos actualizada automáticamente.
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
# 🛡️ AUTO-HEALING
# ---------------------------------------------------------------------
async def check_system_health():
    try:
        if db_pool:
            async with db_pool.acquire() as conn: await conn.execute("SELECT 1")
        else: raise Exception("DB Down")
        return True
    except:
        logger.critical("⚠️ FALLO DE SISTEMA: Iniciando protocolo de reinicio...")
        os._exit(1)
        return False

# ---------------------------------------------------------------------
# 🎨 MOTOR VISUAL
# ---------------------------------------------------------------------
def generate_progress_bar(current, total, length=12):
    if total == 0: total = 1
    percent = min(current / total, 1.0)
    filled = int(length * percent)
    bar = "▰" * filled + "▱" * (length - filled)
    return f"[{bar}] {int(percent * 100)}%"

def get_rank_info(xp):
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
# 🗄️ BASE DE DATOS (ACTUALIZADA PARA REFERIDOS)
# ---------------------------------------------------------------------
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        async with db_pool.acquire() as conn:
            # Tabla Usuarios
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
                    referrer_id BIGINT, -- NUEVO: CAMPO PARA EL PADRE
                    referral_count INTEGER DEFAULT 0, -- NUEVO: CONTADOR
                    created_at TEXT
                )
            """)
            
            # INTENTAMOS AGREGAR COLUMNAS SI YA EXISTE LA TABLA (MIGRACIÓN AUTOMÁTICA)
            try:
                await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT")
                await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_count INTEGER DEFAULT 0")
            except: pass # Ya existen
            
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
        logger.info("✅ DB Conectada y Actualizada (Referidos).")
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
# 💰 LÓGICA DE PAGOS + COMISIÓN REFERIDOS
# ---------------------------------------------------------------------
async def postback_handler_logic(user_id, amount):
    user_share = amount * 0.40 
    tokens_mined = user_share * 10 
    
    async with db_pool.acquire() as conn:
        # 1. Pagar al Usuario
        await conn.execute("UPDATE users SET balance = balance + $1, hive_tokens = hive_tokens + $2 WHERE telegram_id = $3", user_share, tokens_mined, user_id)
        await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)", user_id, user_share, datetime.utcnow().isoformat())
        
        # 2. Pagar al Referidor (Si existe)
        user_data = await conn.fetchrow("SELECT referrer_id FROM users WHERE telegram_id = $1", user_id)
        referrer_bonus = 0
        
        if user_data and user_data['referrer_id']:
            ref_id = user_data['referrer_id']
            # 10% del user_share para el padre
            bonus = user_share * 0.10 
            if bonus > 0.01:
                await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", bonus, ref_id)
                referrer_bonus = bonus
                # Notificar al Padre (luego en la función principal)

        # 3. Lógica NFT
        won_nft = False
        if user_share >= 2.0:
            won_nft = True
            await conn.execute("INSERT INTO nfts (user_id, name, rarity, image_url, minted_at) VALUES ($1, 'Hive Miner Badge 🥉', 'Common', 'url', $2)", user_id, datetime.utcnow().isoformat())

    return user_share, tokens_mined, won_nft, referrer_bonus, user_data['referrer_id'] if user_data else None

@app.get("/postback")
async def postback_endpoint(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")
    
    usd, tokens, nft, ref_bonus, ref_id = await postback_handler_logic(user_id, amount)

    try:
        bot = await init_bot_app()
        
        # Avisar Usuario
        nft_text = "\n🏆 <b>¡NUEVO NFT OBTENIDO!</b>" if nft else ""
        msg = (f"🤑 <b>¡PAGO RECIBIDO!</b>\n💵 Fiat: +${usd:.2f}\n💎 Crypto: +{tokens:.2f} $HIVE{nft_text}")
        await bot.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
        
        # Avisar Referidor (Padre)
        if ref_bonus > 0 and ref_id:
            msg_ref = (f"🔔 <b>BONUS DE REFERIDO</b>\nTu amigo completó una tarea.\nHas ganado: <b>+${ref_bonus:.2f}</b> (10% Pasivo)")
            await bot.bot.send_message(chat_id=ref_id, text=msg_ref, parse_mode="HTML")
            
    except: pass
    return {"status": "success"}

# ---------------------------------------------------------------------
# 🤖 BOT - INTERFAZ NEXUS
# ---------------------------------------------------------------------
async def start_command(update, context):
    # CAPTURA DE REFERIDO (/start 12345)
    referrer_id = None
    if context.args and len(context.args) > 0:
        try:
            potential_ref = int(context.args[0])
            if potential_ref != update.effective_user.id: # No auto-referirse
                referrer_id = potential_ref
        except: pass
        
    # Guardamos el referrer en el contexto temporal
    if referrer_id: context.user_data['pending_referrer'] = referrer_id
    
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
    
    # RECUPERAR REFERRER DEL PASO 1
    referrer_id = context.user_data.get('pending_referrer')
    
    if db_pool:
        async with db_pool.acquire() as conn:
            # Insertamos usuario con Referrer
            await conn.execute("""
                INSERT INTO users (telegram_id, first_name, email, country_code, tier, referrer_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (telegram_id) DO UPDATE SET email=$3, country_code=$4, tier=$5
            """, user.id, user.first_name, email, code, tier, referrer_id, datetime.utcnow().isoformat())
            
            # Si hubo referido, actualizamos contador del padre
            if referrer_id:
                await conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE telegram_id = $1", referrer_id)
                try:
                    # Avisar al padre que tiene un nuevo recluta
                    bot = await init_bot_app()
                    await bot.bot.send_message(chat_id=referrer_id, text="🎉 <b>¡NUEVO RECLUTA!</b>\nUn usuario se registró con tu enlace.", parse_mode="HTML")
                except: pass

    await dashboard_nexus(update, context)
    return ConversationHandler.END

async def dashboard_nexus(update, context):
    user = await get_user(update.effective_user.id)
    if not user: await update.message.reply_text("⚠️ Error. Usa /start"); return
    
    usd = user['balance']
    tokens = user.get('hive_tokens', 0)
    country = user['country_code']
    _, eco = get_tier_info(country)
    
    # Gamificación
    xp = (usd * 100) + tokens
    rank_name, next_goal = get_rank_info(xp)
    p_bar = generate_progress_bar(xp, next_goal)
    
    msg = (
        f"📡 <b>HIVE NEXUS INTERFACE</b> <code>v14.0</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 <b>PILOTO:</b> {update.effective_user.first_name}\n"
        f"🌍 <b>NODO:</b> {country} (Tier {user['tier']})\n"
        f"🏆 <b>RANGO:</b> {rank_name}\n"
        f"<code>{p_bar}</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖\n\n"
        
        f"💰 <b>BILLETERA:</b> {eco['symbol']}{usd:.2f}\n"
        f"💎 <b>HIVE:</b> {tokens:.2f}\n\n"
        
        f"🚀 <b>MISIONES:</b>\n"
        f"   👉 Completa ofertas o Invita Amigos"
    )
    
    kb = [
        ["⚡️ MINAR", "👥 Invitar Amigos"], # Botón Nuevo
        ["🏦 Retirar", "🎒 NFTs / Ranking"],
        ["👤 Perfil", "⚙️ Soporte"]
    ]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

async def show_referral_system(update, context):
    user = await get_user(update.effective_user.id)
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user['telegram_id']}"
    
    ref_count = user.get('referral_count', 0)
    
    msg = (
        "👥 <b>SISTEMA DE RECLUTAMIENTO</b>\n\n"
        "Gana el <b>10% DE POR VIDA</b> de todo lo que generen tus amigos.\n\n"
        f"📊 <b>Tus Estadísticas:</b>\n"
        f"• Reclutas: {ref_count}\n"
        f"• Ganancia Pasiva: Activada ✅\n\n"
        f"🔗 <b>Tu Enlace Único:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        "<i>(Toca el enlace para copiar y mándalo a tus grupos)</i>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# --- MENUS Y RETIROS (Igual que antes) ---
async def show_inventory(update, context):
    user_id = update.effective_user.id
    rows = []
    if db_pool:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM nfts WHERE user_id = $1", user_id)
    if not rows:
        await update.message.reply_text("🎒 <b>SIN NFTs</b>\nCompleta ofertas para ganar.", parse_mode="HTML"); return
    msg = "🏆 <b>TUS ACTIVOS</b>\n\n"
    for nft in rows: msg += f"• <b>{nft['name']}</b> ({nft['rarity']})\n"
    await update.message.reply_text(msg, parse_mode="HTML")

async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    link = f"https://www.offertoro.com/ifr/show/{OFFERTORO_PUB_ID}/{user_id}/{OFFERTORO_SECRET}"
    kb = [[InlineKeyboardButton("🟢 INICIAR MINERÍA", url=link)]]
    await update.message.reply_text("⚡️ <b>CONSOLA DE MINERÍA</b>\nInstala apps para ganar.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

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
    await update.message.reply_text("✅ <b>Solicitud Enviada</b>", parse_mode="HTML")
    if ADMIN_ID: 
        try: await context.bot.send_message(ADMIN_ID, f"🔔 RETIRO: ${amount} - {user.first_name}") 
        except: pass
    return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("❌"); return ConversationHandler.END

async def handle_text(update, context):
    text = update.message.text
    if "MINAR" in text: await offerwall_menu(update, context)
    elif "Invitar" in text: await show_referral_system(update, context) # NUEVO
    elif "Retirar" in text: await start_withdraw(update, context)
    elif "Perfil" in text: await dashboard_nexus(update, context)
    elif "NFT" in text: await show_inventory(update, context)

async def error_handler(update, context):
    logger.error(msg="Error:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("⚠️ Reiniciando...", parse_mode="HTML")
            context.user_data.clear()
    except: pass

# ---------------------------------------------------------------------
# 🚀 ARRANQUE
# ---------------------------------------------------------------------
async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv_start = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    conv_withdraw = ConversationHandler(entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)], states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    
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
