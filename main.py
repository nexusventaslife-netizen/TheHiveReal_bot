"""
THEONEHIVE 20.0 - LIQUIDITY POOL ALGORITHM
Estrategia: Arbitraje de Adquisición + Smart Routing.
Objetivo: Maximizar el ingreso por usuario (ARPU) priorizando ofertas High-Ticket.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional
import asyncpg 
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# --- CONFIGURACIÓN & SECRETOS ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("HiveSmartAlgo")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_ID = os.environ.get("ADMIN_ID")
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret")

# --- FUENTES DE INGRESOS (ARBITRAJE) ---
# En el futuro, esto vendrá de una base de datos dinámica
HIGH_TICKET_OFFERS = {
    "TIER_A": { # USA, UK, DE, CA
        "name": "🏦 Bybit Pro Trader",
        "desc": "Regístrate y deposita $100. (Pagan $60 CPA)",
        "payout_user": 30.0, # Le pagamos $30 al usuario
        "payout_owner": 60.0, # Nosotros cobramos $60
        "link": "https://partner.bybit.com/b/tu_link_tier1",
        "type": "CPA"
    },
    "TIER_B": { # ES, FR, IT
        "name": "💳 Revolut / Wise",
        "desc": "Abre cuenta y pide tarjeta física.",
        "payout_user": 15.0,
        "payout_owner": 35.0,
        "link": "https://revolut.com/referral/...",
        "type": "CPA"
    },
    "TIER_GLOBAL": { # LATAM, ASIA
        "name": "🎲 Stake Casino / BingX",
        "desc": "Registro + Depósito de $10.",
        "payout_user": 5.0,
        "payout_owner": 15.0,
        "link": "https://stake.com/...",
        "type": "CPA"
    }
}

# ADSTERRA LINK (Ingreso Pasivo de Respaldo)
ADSTERRA_LINK = os.environ.get("ADSTERRA_LINK", "https://google.com")

APP_NAME = "TheOneHive AI"
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None
db_pool: Optional[asyncpg.Pool] = None

# Estados Conversación
ASK_EMAIL, ASK_COUNTRY, WAITING_PROOF = range(3)

# --- ALGORITMO DE SMART ROUTING ---
def get_optimized_offer(country_code):
    """
    Decide qué oferta mostrar para maximizar el margen.
    """
    code = str(country_code).upper()
    tier_a = ["US", "GB", "CA", "DE", "AU", "CH"]
    tier_b = ["ES", "FR", "IT", "NL", "SE", "NO"]
    
    if code in tier_a:
        return HIGH_TICKET_OFFERS["TIER_A"]
    elif code in tier_b:
        return HIGH_TICKET_OFFERS["TIER_B"]
    else:
        return HIGH_TICKET_OFFERS["TIER_GLOBAL"]

# --- DATABASE ---
async def init_db():
    global db_pool
    if not DATABASE_URL: return
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                country_code TEXT,
                balance DOUBLE PRECISION DEFAULT 0.0,
                pending_balance DOUBLE PRECISION DEFAULT 0.0,
                trust_score INTEGER DEFAULT 50, -- Nuevo: Score de confianza
                created_at TEXT
            )
        """)
        await conn.execute("CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id BIGINT, type TEXT, amount DOUBLE PRECISION, status TEXT, created_at TEXT)")

async def get_user(tg_id):
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        return dict(r) if r else None

# --- BOT LOGIC ---

async def start_command(update, context):
    user = update.effective_user
    db_user = await get_user(user.id)
    if db_user:
        await dashboard(update, context)
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"👋 Hola {user.first_name}.\n\n"
        "Bienvenido a <b>TheOneHive Liquidity Protocol</b>.\n"
        "Pagamos por tareas financieras de alto valor.\n\n"
        "🌍 <b>Para empezar, ¿de qué país eres? (Ej: ES, MX, US)</b>",
        parse_mode="HTML"
    )
    return ASK_COUNTRY

async def receive_country(update, context):
    country = update.message.text.upper().strip()[:2]
    user = update.effective_user
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, country_code, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_id) DO UPDATE SET country_code=$3
        """, user.id, user.first_name, country, datetime.utcnow().isoformat())
    
    await update.message.reply_text("✅ Perfil Creado. Analizando mejores ofertas para tu región...")
    await asyncio.sleep(1.5) # Simular análisis IA
    await dashboard(update, context)
    return ConversationHandler.END

async def dashboard(update, context):
    user_data = await get_user(update.effective_user.id)
    country = user_data['country_code']
    balance = user_data['balance']
    
    # INVOCAR ALGORITMO
    best_offer = get_optimized_offer(country)
    
    msg = (
        f"🏦 <b>BILLETERA HIVE</b> | Región: {country}\n"
        f"💰 Saldo Disponible: <b>${balance:.2f} USD</b>\n\n"
        f"🔥 <b>OFERTA FLASH DETECTADA (Expira en 24h):</b>\n"
        f"📌 <b>{best_offer['name']}</b>\n"
        f"ℹ️ {best_offer['desc']}\n"
        f"💵 <b>TÚ GANAS: ${best_offer['payout_user']:.2f}</b>\n\n"
        "👇 Selecciona una opción:"
    )
    
    kb = [
        [InlineKeyboardButton("🚀 COMENZAR MISIÓN (Alta Ganancia)", callback_data="start_mission")],
        [InlineKeyboardButton("🎁 BONUS RÁPIDO (Ver Anuncio)", url=ADSTERRA_LINK)],
        [InlineKeyboardButton("👤 Mi Cuenta", callback_data="profile")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# --- FLUJO DE MISIÓN ---
async def start_mission_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_data = await get_user(update.effective_user.id)
    offer = get_optimized_offer(user_data['country_code'])
    
    msg = (
        f"🔒 <b>INSTRUCCIONES SEGURAS</b>\n\n"
        f"1. Entra aquí: {offer['link']}\n"
        "2. Completa el registro y el requisito.\n"
        "3. Toma una captura de pantalla CLARA.\n"
        "4. Vuelve aquí y sube la foto.\n\n"
        "⚠️ <i>Solo cuentas nuevas. Detectamos fraudes.</i>"
    )
    kb = [[InlineKeyboardButton("📤 SUBIR PRUEBA AHORA", callback_data="upload_proof")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def ask_proof(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📸 Envía la foto ahora (Captura de pantalla).")
    return WAITING_PROOF

async def handle_proof(update, context):
    photo = update.message.photo[-1]
    user = update.effective_user
    user_db = await get_user(user.id)
    offer = get_optimized_offer(user_db['country_code'])
    
    # ALERTA AL ADMIN
    if ADMIN_ID:
        caption = (
            f"🤑 <b>NUEVO LEAD POTENCIAL</b>\n"
            f"👤 {user.first_name} ({user_db['country_code']})\n"
            f"📌 Oferta: {offer['name']}\n"
            f"💸 A pagar al user: ${offer['payout_user']}\n"
            f"📈 Nuestra ganancia: ${offer['payout_owner'] - offer['payout_user']}"
        )
        kb = [
            [InlineKeyboardButton("✅ APROBAR Y PAGAR", callback_data=f"pay_{user.id}_{offer['payout_user']}")],
            [InlineKeyboardButton("❌ RECHAZAR", callback_data=f"deny_{user.id}")]
        ]
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    
    await update.message.reply_text("✅ <b>Prueba Recibida.</b>\nVerificando con el anunciante... (Tiempo estimado: 2-12 horas).")
    return ConversationHandler.END

# --- ADMIN ACTIONS ---
async def admin_action(update, context):
    query = update.callback_query
    data = query.data
    
    if data.startswith("pay_"):
        _, uid, amount = data.split("_")
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance=balance+$1 WHERE telegram_id=$2", float(amount), int(uid))
        await context.bot.send_message(int(uid), f"💰 <b>¡PAGO APROBADO!</b>\nHas recibido ${float(amount):.2f} USD.", parse_mode="HTML")
        await query.edit_message_caption("✅ PAGADO")
        
    elif data.startswith("deny_"):
        uid = data.split("_")[1]
        await context.bot.send_message(int(uid), "❌ Tu prueba fue rechazada. No cumple los requisitos.")
        await query.edit_message_caption("❌ RECHAZADO")

async def cancel(update, context): await update.message.reply_text("Operación cancelada."); return ConversationHandler.END

# --- SETUP ---
async def init_bot():
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv = ConversationHandler(entry_points=[CommandHandler("start", start_command)], states={ASK_COUNTRY: [MessageHandler(filters.TEXT, receive_country)]}, fallbacks=[CommandHandler("cancel", cancel)])
    proof_conv = ConversationHandler(entry_points=[CallbackQueryHandler(ask_proof, pattern="upload_proof")], states={WAITING_PROOF: [MessageHandler(filters.PHOTO, handle_proof)]}, fallbacks=[CommandHandler("cancel", cancel)])
    
    telegram_app.add_handler(conv)
    telegram_app.add_handler(proof_conv)
    telegram_app.add_handler(CallbackQueryHandler(start_mission_callback, pattern="start_mission"))
    telegram_app.add_handler(CallbackQueryHandler(admin_action, pattern="^(pay|deny)_"))
    
    await telegram_app.initialize()
    return telegram_app

@app.post("/telegram/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN: return JSONResponse(403, {})
    bot = await init_bot()
    await bot.process_update(Update.de_json(await request.json(), bot.bot))
    return {"ok": True}

@app.on_event("startup")
async def startup(): await init_db(); bot = await init_bot(); await bot.start()
