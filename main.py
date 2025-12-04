"""
THEONEHIVE 17.0 - SMART GEO-ROUTING EDITION
Características:
1. Routing Inteligente: Menús diferentes para Tier 1 (USA/EU) vs Tier 3 (Latam).
2. Ingresos Híbridos: API (OfferToro) + Affiliate (Swagbucks) + Adsterra.
3. Retención: Racha Diaria.
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

# --- MONETIZACIÓN ---
ADSTERRA_LINK = os.environ.get("ADSTERRA_LINK", "https://google.com")
# Pon aquí tus enlaces de referido (Swagbucks, Freecash, etc.)
AFFILIATE_LINK_1 = os.environ.get("AFFILIATE_LINK_1", "https://www.swagbucks.com") 
AFFILIATE_TEXT_1 = "🎁 Gana $5 en Swagbucks"

# OFFERTORO
OFFERTORO_PUB_ID = os.environ.get("OFFERTORO_PUB_ID", "0")
OFFERTORO_SECRET = os.environ.get("OFFERTORO_SECRET", "0")

APP_NAME = "TheOneHive Pro"
ASK_EMAIL, ASK_COUNTRY, ASK_WALLET = range(3)

# CLASIFICACIÓN DE PAÍSES (CRÍTICO PARA GANAR MÁS)
GEO_ECONOMY = {
    "TIER_A": {"countries": ["US", "AU", "GB", "CA", "DE", "CH", "NO", "SE"], "symbol": "$$$"}, # Países Ricos
    "TIER_B": {"countries": ["ES", "FR", "IT", "NL", "BE", "DK"], "symbol": "€€"}, # Europa
    "TIER_C": {"countries": ["MX", "AR", "CO", "BR", "CL", "PE"], "symbol": "$"}, # Latam Fuerte
    "TIER_D": {"countries": ["GLOBAL"], "symbol": "¢"} # Resto del mundo
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
# 🎨 MOTOR VISUAL
# ---------------------------------------------------------------------
def generate_progress_bar(current, total, length=10):
    if total == 0: total = 1
    percent = min(current / total, 1.0)
    filled = int(length * percent)
    bar = "▰" * filled + "▱" * (length - filled)
    return f"{bar} {int(percent * 100)}%"

def get_level_info(xp):
    level = int(xp / 1000) + 1
    next_level_xp = level * 1000
    return level, next_level_xp

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
                    referrer_id BIGINT,
                    referral_count INTEGER DEFAULT 0,
                    last_daily_claim TEXT, 
                    daily_streak INTEGER DEFAULT 0, 
                    xp INTEGER DEFAULT 0, 
                    created_at TEXT
                )
            """)
            # Migraciones seguras
            for col in ["last_daily_claim", "daily_streak", "xp"]:
                try: await conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} TEXT") # Simplificado a TEXT/INT según corresponda
                except: pass
                
            await conn.execute("CREATE TABLE IF NOT EXISTS nfts (id SERIAL PRIMARY KEY, user_id BIGINT, name TEXT, rarity TEXT, image_url TEXT, minted_at TEXT)")
            await conn.execute("CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id BIGINT, type TEXT, amount DOUBLE PRECISION, source TEXT, status TEXT, created_at TEXT)")
        logger.info("✅ DB Smart-Routing Ready.")
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
# 🎁 RECOMPENSA DIARIA
# ---------------------------------------------------------------------
async def claim_daily(update, context):
    user = await get_user(update.effective_user.id)
    now = datetime.utcnow()
    last_claim = None
    if user.get('last_daily_claim'):
        try: last_claim = datetime.fromisoformat(user['last_daily_claim'])
        except: pass
    
    if last_claim and (now - last_claim).total_seconds() < 86400:
        hours_left = int((86400 - (now - last_claim).total_seconds()) / 3600)
        kb = [[InlineKeyboardButton("🎁 GANA EXTRA AHORA", url=ADSTERRA_LINK)]]
        await update.message.reply_text(f"⏳ <b>Faltan {hours_left}h</b>\n\n👇 Mientras, gana aquí:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    streak = int(user.get('daily_streak', 0))
    if last_claim and (now - last_claim).total_seconds() > 172800: streak = 0
    streak += 1
    reward = 50 + (streak * 10)
    
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET hive_tokens = hive_tokens + $1, daily_streak = $2, last_daily_claim = $3 WHERE telegram_id = $4", float(reward), streak, now.isoformat(), user['telegram_id'])
    
    kb = [[InlineKeyboardButton("🎁 DOBLAR PREMIO (Clic)", url=ADSTERRA_LINK)]]
    await update.message.reply_text(f"📅 <b>DÍA {streak}</b>: +{reward} HIVE\n\n👇 ¡Toca para ganar más!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ---------------------------------------------------------------------
# 🧠 SMART OFFERWALL MENU (OPTIMIZACIÓN GEO)
# ---------------------------------------------------------------------
async def offerwall_menu(update, context):
    user = await get_user(update.effective_user.id)
    if not user: return
    
    tier = user['tier']
    country = user['country_code']
    
    # Enlace base de OfferToro (cambiaremos esto cuando Monlix te acepte)
    link_toro = f"https://www.offertoro.com/ifr/show/{OFFERTORO_PUB_ID}/{user['telegram_id']}/{OFFERTORO_SECRET}"
    
    kb = []
    
    # --- LÓGICA DE OPTIMIZACIÓN ---
    if tier == "TIER_A" or tier == "TIER_B":
        # 🇺🇸🇪🇺 PAÍSES RICOS: Mostrar Encuestas Caras y Afiliados Premium
        kb.append([InlineKeyboardButton("💎 PREMIUM SURVEYS ($2 - $10)", url=link_toro)])
        kb.append([InlineKeyboardButton(f"🏦 {AFFILIATE_TEXT_1}", url=AFFILIATE_LINK_1)])
        # Bonus siempre presente
        kb.append([InlineKeyboardButton("🎲 BONUS RÁPIDO", url=ADSTERRA_LINK)])
        
        msg = f"🇺🇸 <b>Ofertas Premium Detectadas ({country})</b>\nEstás en una zona de alto valor. Completa una encuesta para ganar hasta 5000 HIVE."

    else:
        # 🌎 RESTO DEL MUNDO: Volumen, Apps ligeras y Adsterra
        kb.append([InlineKeyboardButton("📱 INSTALAR APPS (Fácil)", url=link_toro)])
        kb.append([InlineKeyboardButton("🎁 BONUS DIARIO (Gana Ya)", url=ADSTERRA_LINK)])
        kb.append([InlineKeyboardButton("⚡️ OFERTAS RÁPIDAS", url=link_toro)])
        
        msg = f"🌎 <b>Zona Global ({country})</b>\nInstala aplicaciones ligeras o usa el Bonus Diario para sumar puntos rápido."

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ---------------------------------------------------------------------
# 💰 POSTBACK & CORE
# ---------------------------------------------------------------------
async def postback_handler_logic(user_id, amount):
    user_share = amount * 0.40 
    tokens = user_share * 10 
    xp = int(user_share * 100)
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance=balance+$1, hive_tokens=hive_tokens+$2, xp=xp+$3 WHERE telegram_id=$4", user_share, tokens, xp, user_id)
        # Referidos
        ref = await conn.fetchrow("SELECT referrer_id FROM users WHERE telegram_id=$1", user_id)
        if ref and ref['referrer_id']:
            await conn.execute("UPDATE users SET balance=balance+$1 WHERE telegram_id=$2", user_share*0.10, ref['referrer_id'])
    return user_share, tokens

@app.get("/postback")
async def postback_endpoint(user_id: int, amount: float, secret: str, trans_id: str):
    if secret != POSTBACK_SECRET: raise HTTPException(403)
    usd, tokens = await postback_handler_logic(user_id, amount)
    try:
        bot = await init_bot_app()
        await bot.bot.send_message(user_id, f"✅ <b>PAGO RECIBIDO</b>\n💵 +${usd:.2f}\n💎 +{tokens:.2f} HIVE", parse_mode="HTML")
    except: pass
    return {"status": "success"}

# ---------------------------------------------------------------------
# 🚀 BOT STANDARD COMMANDS
# ---------------------------------------------------------------------
async def start_command(update, context):
    ref_id = int(context.args[0]) if context.args else None
    if ref_id: context.user_data['ref'] = ref_id
    user = await get_user(update.effective_user.id)
    if user and user['email']: await dashboard_main(update, context); return ConversationHandler.END
    await update.message.reply_text("👋 <b>Bienvenido a TheOneHive</b>\n\n📧 <b>Tu Email:</b>", parse_mode="HTML")
    return ASK_EMAIL

async def receive_email(update, context):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🌍 <b>País (2 letras, ej: MX, US, ES):</b>\nEsto define tus ganancias.", parse_mode="HTML")
    return ASK_COUNTRY

async def receive_country(update, context):
    code = update.message.text.upper().strip()
    tier, _ = get_tier_info(code)
    user = update.effective_user
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, email, country_code, tier, referrer_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (telegram_id) DO UPDATE SET email=$3, country_code=$4, tier=$5
        """, user.id, user.first_name, context.user_data.get('email'), code, tier, context.user_data.get('ref'), datetime.utcnow().isoformat())
    
    await dashboard_main(update, context)
    return ConversationHandler.END

async def dashboard_main(update, context):
    user = await get_user(update.effective_user.id)
    if not user: await update.message.reply_text("⚠️ /start"); return
    
    p_bar = generate_progress_bar(user.get('xp',0) % 1000, 1000)
    tier_icon = "🇺🇸 VIP" if user['tier'] in ["TIER_A", "TIER_B"] else "🌎 Global"
    
    msg = (
        f"📱 <b>THE ONE HIVE</b> | {tier_icon}\n"
        f"👤 {user['first_name']} | 🏆 Nivel {int(user.get('xp',0)/1000)+1}\n"
        f"<code>{p_bar}</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💵 Saldo: <b>${user['balance']:.2f}</b>\n"
        f"💎 Tokens: <b>{user.get('hive_tokens',0):.1f}</b>\n"
        f"🔥 Racha: <b>{user.get('daily_streak',0)} días</b>\n\n"
        f"👇 <b>¿Qué quieres hacer hoy?</b>"
    )
    kb = [["⚡️ MINAR (Ofertas)", "📅 Bonus Diario"], ["👥 Invitar (+10%)", "🎒 Mis NFTs"], ["🏦 Retirar", "👤 Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")

async def show_referral(update, context):
    link = f"https://t.me/{context.bot.username}?start={update.effective_user.id}"
    await update.message.reply_text(f"👥 <b>INVITA Y GANA</b>\nRecibes el 10% de por vida.\n\n🔗 <code>{link}</code>", parse_mode="HTML")

async def start_withdraw(update, context):
    await update.message.reply_text("💸 <b>Wallet USDT (TRC20):</b>", parse_mode="HTML"); return ASK_WALLET

async def process_withdraw(update, context):
    user = update.effective_user
    amount = (await get_user(user.id))['balance']
    if amount < 5: await update.message.reply_text("⚠️ Mínimo $5.00"); return ConversationHandler.END
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = 0 WHERE telegram_id = $1", user.id)
        await conn.execute("INSERT INTO transactions (user_id, type, amount, source, status, created_at) VALUES ($1, 'WITHDRAW', $2, $3, 'PENDING', $4)", user.id, amount, update.message.text, datetime.utcnow().isoformat())
    await update.message.reply_text("✅ <b>Retiro en proceso.</b>"); return ConversationHandler.END

async def handle_text(update, context):
    text = update.message.text
    if "MINAR" in text: await offerwall_menu(update, context) # AQUÍ ESTÁ LA MAGIA
    elif "Bonus" in text: await claim_daily(update, context)
    elif "Invitar" in text: await show_referral(update, context)
    elif "Retirar" in text: await start_withdraw(update, context)
    elif "Perfil" in text: await dashboard_main(update, context)

async def cancel(update, context): await update.message.reply_text("❌"); return ConversationHandler.END
async def error_handler(update, context): logger.error(f"Error: {context.error}")

# ---------------------------------------------------------------------
# 🚀 ARRANQUE
# ---------------------------------------------------------------------
async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_s = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_EMAIL:[MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY:[MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel)])
    conv_w = ConversationHandler(entry_points=[MessageHandler(filters.Regex("Retirar"), start_withdraw)], states={ASK_WALLET: [MessageHandler(filters.TEXT, process_withdraw)]}, fallbacks=[CommandHandler("cancel", cancel)])
    telegram_app.add_handler(conv_s); telegram_app.add_handler(conv_w); telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text)); telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize(); return telegram_app

@app.api_route("/health", methods=["GET", "HEAD"])
async def health(): return {"status": "ok"} if await check_system_health() else HTTPException(500)

@app.post("/telegram/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN: return JSONResponse(403, {})
    data = await request.json(); bot=await init_bot_app(); await bot.process_update(Update.de_json(data, bot.bot)); return {"ok":True}
@app.on_event("startup")
async def startup(): await init_db(); bot=await init_bot_app(); await bot.start() 
@app.on_event("shutdown")
async def shutdown(): await telegram_app.stop(); await db_pool.close()
