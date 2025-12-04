"""
THEONEHIVE 16.0 - PROFESSIONAL ECOSYSTEM
Características:
1. Retención: Racha Diaria (Daily Streak) + Niveles.
2. Crecimiento: Sistema de Referidos (10%).
3. Ingresos: Offerwall (OfferToro) integrado.
4. Activos: Inventario NFT y Tokens HIVE (Sin apuestas).
5. Seguridad: Auto-Healing y cero fricción.
"""

import logging
import os
import sys
import asyncio
from datetime import datetime, timedelta
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

APP_NAME = "TheOneHive Pro"
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
        os._exit(1)
        return False

# ---------------------------------------------------------------------
# 🎨 MOTOR VISUAL (Barras de Progreso)
# ---------------------------------------------------------------------
def generate_progress_bar(current, total, length=10):
    if total == 0: total = 1
    percent = min(current / total, 1.0)
    filled = int(length * percent)
    bar = "▰" * filled + "▱" * (length - filled)
    return f"{bar} {int(percent * 100)}%"

def get_level_info(xp):
    # Sistema de niveles RPG simple
    level = int(xp / 1000) + 1
    next_level_xp = level * 1000
    return level, next_level_xp

# ---------------------------------------------------------------------
# 🗄️ BASE DE DATOS (ESTRUCTURA FINAL)
# ---------------------------------------------------------------------
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        async with db_pool.acquire() as conn:
            # Usuarios
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
                    referrer_id BIGINT,
                    referral_count INTEGER DEFAULT 0,
                    last_daily_claim TEXT, -- NUEVO: Para racha diaria
                    daily_streak INTEGER DEFAULT 0, -- NUEVO: Racha
                    xp INTEGER DEFAULT 0, -- NUEVO: Experiencia Global
                    created_at TEXT
                )
            """)
            
            # Actualización segura de columnas nuevas
            try: await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily_claim TEXT")
            except: pass
            try: await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_streak INTEGER DEFAULT 0")
            except: pass
            try: await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0")
            except: pass

            # Tablas Assets
            await conn.execute("CREATE TABLE IF NOT EXISTS nfts (id SERIAL PRIMARY KEY, user_id BIGINT, name TEXT, rarity TEXT, image_url TEXT, minted_at TEXT)")
            await conn.execute("CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id BIGINT, type TEXT, amount DOUBLE PRECISION, source TEXT, status TEXT, created_at TEXT)")
        logger.info("✅ DB Professional Ready.")
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
# 🎁 RECOMPENSA DIARIA (RETENCIÓN SANA)
# ---------------------------------------------------------------------
async def claim_daily(update, context):
    user = await get_user(update.effective_user.id)
    now = datetime.utcnow()
    
    last_claim = None
    if user['last_daily_claim']:
        try: last_claim = datetime.fromisoformat(user['last_daily_claim'])
        except: pass
    
    # Verificar si ya pasaron 24h
    if last_claim and (now - last_claim).total_seconds() < 86400:
        hours_left = int((86400 - (now - last_claim).total_seconds()) / 3600)
        await update.message.reply_text(f"⏳ <b>Espera {hours_left} horas</b> para tu siguiente recompensa.", parse_mode="HTML")
        return

    # Calcular Racha
    streak = user['daily_streak']
    if last_claim and (now - last_claim).total_seconds() > 172800: # Si pasan 48h, pierde racha
        streak = 0
    
    streak += 1
    reward_tokens = 50 + (streak * 10) # Cada día gana más
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE users 
            SET hive_tokens = hive_tokens + $1, 
                daily_streak = $2, 
                last_daily_claim = $3 
            WHERE telegram_id = $4
        """, float(reward_tokens), streak, now.isoformat(), user['telegram_id'])
    
    await update.message.reply_text(f"📅 <b>¡DÍA {streak} COMPLETADO!</b>\n\n💎 Recibiste: <b>+{reward_tokens} HIVE</b>\n🔥 ¡Vuelve mañana para mantener la racha!", parse_mode="HTML")

# ---------------------------------------------------------------------
# 💰 LÓGICA DE PAGOS + REFERIDOS
# ---------------------------------------------------------------------
async def postback_handler_logic(user_id, amount):
    user_share = amount * 0.40 
    tokens_mined = user_share * 10 
    xp_gained = int(user_share * 100)
    
    async with db_pool.acquire() as conn:
        # Pagar Usuario + XP
        await conn.execute("""
            UPDATE users 
            SET balance = balance + $1, 
                hive_tokens = hive_tokens + $2,
                xp = xp + $3
            WHERE telegram_id = $4
        """, user_share, tokens_mined, xp_gained, user_id)
        
        await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'EARN', $2, 'Offerwall', 'COMPLETED', $3)", user_id, user_share, datetime.utcnow().isoformat())
        
        # Referidos (10%)
        user_data = await conn.fetchrow("SELECT referrer_id FROM users WHERE telegram_id = $1", user_id)
        if user_data and user_data['referrer_id']:
            bonus = user_share * 0.10 
            if bonus > 0.01: await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", bonus, user_data['referrer_id'])

        # NFT Drop (Aleatorio si la tarea es grande)
        won_nft = False
        if user_share >= 1.5:
            won_nft = True
            await conn.execute("INSERT INTO nfts (user_id, name, rarity, image_url, minted_at) VALUES ($1, 'Task Master Badge', 'Rare', 'url', $2)", user_id, datetime.utcnow().isoformat())

    return user_share, tokens_mined, won_nft

@app.get("/postback")
async def postback_endpoint(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(status_code=403, detail="Acceso Denegado")
    usd, tokens, nft = await postback_handler_logic(user_id, amount)
    try:
        bot = await init_bot_app()
        nft_text = "\n🏆 <b>¡NFT RARO OBTENIDO!</b>" if nft else ""
        msg = (f"✅ <b>TAREA COMPLETADA</b>\n💵 +${usd:.2f}\n💎 +{tokens:.2f} HIVE{nft_text}")
        await bot.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
    except: pass
    return {"status": "success"}

# ---------------------------------------------------------------------
# 🤖 BOT INTERFAZ (CLEAN & PROFESSIONAL)
# ---------------------------------------------------------------------
async def start_command(update, context):
    ref_id = None
    if context.args: 
        try: ref_id = int(context.args[0])
        except: pass
    if ref_id: context.user_data['ref'] = ref_id
    
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_main(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 <b>Bienvenido a TheOneHive</b>\nPlataforma de Recompensas Global.\n\n📧 <b>Tu Email:</b>", parse_mode="HTML")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 <b>País (2 letras, ej: MX):</b>", parse_mode="HTML")
    return ASK_COUNTRY

async def receive_country(update, context):
    code = update.message.text.upper().strip()
    email = context.user_data.get('email')
    tier, _ = get_tier_info(code)
    ref_id = context.user_data.get('ref')
    
    user = update.effective_user
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (telegram_id, first_name, email, country_code, tier, referrer_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (telegram_id) DO UPDATE SET email=$3, country_code=$4, tier=$5
            """, user.id, user.first_name, email, code, tier, ref_id, datetime.utcnow().isoformat())
            if ref_id: 
                await conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE telegram_id = $1", ref_id)
                try: 
                    bot = await init_bot_app()
                    await bot.bot.send_message(ref_id, "👥 <b>Nuevo Referido Registrado</b>", parse_mode="HTML")
                except: pass
    
    await dashboard_main(update, context)
    return ConversationHandler.END

# --- DASHBOARD FINAL ---
async def dashboard_main(update, context):
    user = await get_user(update.effective_user.id)
    if not user: await update.message.reply_text("⚠️ /start"); return
    
    usd = user['balance']
    tokens = user.get('hive_tokens', 0)
    xp = user.get('xp', 0)
    level, next_xp = get_level_info(xp)
    
    p_bar = generate_progress_bar(xp % 1000, 1000)
    
    msg = (
        f"📱 <b>THE ONE HIVE</b> | {user['country_code']}\n"
        f"👤 {update.effective_user.first_name} | 🏆 Nivel {level}\n"
        f"<code>{p_bar}</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
        f"💵 <b>Saldo Real:</b> ${usd:.2f}\n"
        f"💎 <b>HIVE Tokens:</b> {tokens:.1f}\n"
        f"🔥 <b>Racha Diaria:</b> {user.get('daily_streak', 0)} días\n\n"
        
        f"👇 <b>Selecciona una opción:</b>"
    )
    
    kb = [
        ["⚡️ MINAR (Ofertas)", "📅 Bonus Diario"], # Ganchos principales
        ["👥 Invitar (+10%)", "🎒 Mis NFTs"],
        ["🏦 Retirar", "👤 Perfil"]
    ]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

async def show_referral(update, context):
    user = await get_user(update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start={user['telegram_id']}"
    await update.message.reply_text(
        f"👥 <b>PROGRAMA DE REFERIDOS</b>\n\nGana el <b>10%</b> de lo que generen tus amigos.\n\n🔗 <b>Tu Enlace:</b>\n<code>{link}</code>", 
        parse_mode="HTML"
    )

# --- MENUS STANDARD ---
async def offerwall_menu(update, context):
    user_id = update.effective_user.id
    link = f"https://www.offertoro.com/ifr/show/{OFFERTORO_PUB_ID}/{user_id}/{OFFERTORO_SECRET}"
    kb = [[InlineKeyboardButton("🟢 IR A OFERTAS", url=link)]]
    await update.message.reply_text("⚡️ <b>PANEL DE TAREAS</b>\nInstala apps verificadas para ganar saldo.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def show_inventory(update, context):
    user_id = update.effective_user.id
    rows = []
    if db_pool:
        async with db_pool.acquire() as conn: rows = await conn.fetch("SELECT * FROM nfts WHERE user_id = $1", user_id)
    if not rows: await update.message.reply_text("🎒 <b>Sin NFTs</b>\nCompleta tareas de alto valor para ganar medallas.", parse_mode="HTML"); return
    msg = "🏆 <b>COLECCIÓN NFT</b>\n\n"
    for nft in rows: msg += f"• {nft['name']} ({nft['rarity']})\n"
    await update.message.reply_text(msg, parse_mode="HTML")

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
    await update.message.reply_text("✅ <b>Retiro Solicitado</b>\nSe procesará en 24h.", parse_mode="HTML")
    return ConversationHandler.END

async def cancel(update, context): await update.message.reply_text("❌"); return ConversationHandler.END

# --- RUTEO ---
async def handle_text(update, context):
    text = update.message.text
    if "MINAR" in text: await offerwall_menu(update, context)
    elif "Bonus" in text: await claim_daily(update, context) # NUEVO: Diario
    elif "Invitar" in text: await show_referral(update, context)
    elif "Retirar" in text: await start_withdraw(update, context)
    elif "Perfil" in text: await dashboard_main(update, context)
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
    
    conv_s = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    conv_w = ConversationHandler(entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)], states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]}, fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start_command)])
    
    telegram_app.add_handler(conv_s)
    telegram_app.add_handler(conv_w)
    telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    if await check_system_health(): return {"status": "ok"}
    else: raise HTTPException(500)

@app.get("/")
async def root(): return {"status": "TheOneHive Pro Online"}

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
