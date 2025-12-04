"""
THEONEHIVE 3.0 - FINAL FIX & FEATURES
Optimizado para Render (Python 3.11) + Full Handlers
"""

import logging
import os
import asyncio
from datetime import datetime
from typing import Optional, Any
import hashlib

# Librerías externas
import aiosqlite
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
DB_PATH = "theonehive.db"

if not TELEGRAM_TOKEN:
    logger.error("CRITICAL: Faltan variables de entorno.")

APP_NAME = "TheOneHive 🐝"

# Configuración de País
COUNTRY_CONFIG = {
    "GLOBAL": {"currency": "USD", "min_withdraw": 5.0},
    "MX": {"currency": "MXN", "min_withdraw": 2.0}, 
    "AR": {"currency": "ARS", "min_withdraw": 1.0},
    "US": {"currency": "USD", "min_withdraw": 10.0},
}

# ---------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None

# ---------------------------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------------------------

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                balance REAL DEFAULT 0.0,
                tokens_invisibles INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                level TEXT DEFAULT 'Novato',
                country_code TEXT DEFAULT 'GLOBAL',
                created_at TEXT,
                last_active TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                reward_usd REAL,
                xp_reward INTEGER,
                type TEXT,
                url TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Tareas de ejemplo
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, reward_usd, xp_reward, type, url) VALUES (1, 'Encuesta Inicial', 0.50, 100, 'ENCUESTA', 'https://google.com')")
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, reward_usd, xp_reward, type, url) VALUES (2, 'Reto TikTok', 2.00, 500, 'VIRAL', 'https://tiktok.com')")
        await db.commit()
    logger.info("✅ DB Inicializada.")

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def register_user(user: Any, ref_code_input: str = None):
    now = datetime.utcnow().isoformat()
    my_ref_code = hashlib.md5(str(user.id).encode()).hexdigest()[:8].upper()
    
    referrer_id = None
    if ref_code_input:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code_input,)) as cursor:
                row = await cursor.fetchone()
                if row: referrer_id = row[0]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (telegram_id, first_name, username, referral_code, referred_by, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user.id, user.first_name, user.username, my_ref_code, referrer_id, now, now))
        await db.commit()
    return await get_user(user.id)

# ---------------------------------------------------------------------
# BOT: COMANDOS Y MENÚS
# ---------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    ref_input = args[0] if args else None
    user_data = await register_user(update.effective_user, ref_input)
    
    keyboard = [
        ["🚀 Ganar Dinero", "📱 Retos Virales"],
        ["💰 Billetera", "🏆 Nivel"],
        ["💎 Premium", "👥 Referidos"]
    ]
    
    msg = (
        f"👋 **¡Hola, {user_data['first_name']}!**\n\n"
        f"Bienvenido a **TheOneHive**. Tu centro de ingresos digitales.\n\n"
        f"🏅 Nivel: {user_data['level']}\n"
        f"💵 Saldo: ${user_data['balance']:.2f}\n\n"
        "👇 Selecciona una opción:"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode="Markdown"
    )

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE is_active=1") as cursor:
            tasks = await cursor.fetchall()
            
    keyboard = []
    msg = "📋 **TAREAS DISPONIBLES**\n\n"
    
    for t in tasks:
        msg += f"🔹 **{t['title']}**\n💵 ${t['reward_usd']} | ✨ {t['xp_reward']} XP\n\n"
        # Botón que lleva a la URL de la tarea
        keyboard.append([InlineKeyboardButton(f"Ir a: {t['title']}", url=t['url'])])
        
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    country = COUNTRY_CONFIG.get(user['country_code'], COUNTRY_CONFIG['GLOBAL'])
    
    msg = (
        f"💰 **BILLETERA**\n\n"
        f"💵 Disponible: ${user['balance']:.2f}\n"
        f"🏦 Moneda local: {country['currency']}\n"
        f"📉 Mínimo retiro: ${country['min_withdraw']}\n"
    )
    
    # ESTE BOTÓN CAUSÓ EL ERROR ANTES. AHORA YA TIENE HANDLER.
    kb = [[InlineKeyboardButton("💸 SOLICITAR RETIRO", callback_data="withdraw_click")]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def viral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎬 **ZONA VIRAL**\n\n"
        "Sube videos a TikTok/Reels con #TheOneHive.\n"
        "Gana $2.00 por cada 1k vistas.\n\n"
        "Envía el link de tu video aquí:"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------------------------------------------------------------
# BOT: MANEJADOR DE BOTONES (LO QUE FALTABA)
# ---------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los clics en botones Inline"""
    query = update.callback_query
    await query.answer() # IMPORTANTE: Avisa a Telegram que se recibió el clic
    
    data = query.data
    
    if data == "withdraw_click":
        await query.edit_message_text(
            text="⏳ **Solicitud de Retiro**\n\nPara procesar tu retiro, necesitas alcanzar el mínimo de retiro.\n\nActualmente estamos integrando PayPal y Crypto. ¡Pronto disponible!",
            parse_mode="Markdown"
        )

# ---------------------------------------------------------------------
# BOT: MANEJADOR DE TEXTO
# ---------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Ganar Dinero" in text: await tasks_menu(update, context)
    elif "Retos Virales" in text: await viral_menu(update, context)
    elif "Billetera" in text: await wallet_menu(update, context)
    elif "Nivel" in text: await update.message.reply_text("🏆 Tu nivel es: Novato (0 XP)")
    elif "Referidos" in text: 
         user = await get_user(update.effective_user.id)
         link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
         await update.message.reply_text(f"🔗 Tu enlace:\n`{link}`", parse_mode="Markdown")
    elif "Premium" in text: await update.message.reply_text("💎 Premium próximamente.")

# ---------------------------------------------------------------------
# MANEJO DE ERRORES (PARA QUE NO SALGA ROJO EN RENDER)
# ---------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # Opcional: Avisar al usuario
    # if isinstance(update, Update) and update.effective_message:
    #     await update.effective_message.reply_text("⚠️ Ocurrió un error interno. Intenta de nuevo.")

# ---------------------------------------------------------------------
# INICIALIZACIÓN
# ---------------------------------------------------------------------

async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # REGISTRO DE TODOS LOS HANDLERS
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CallbackQueryHandler(button_handler)) # <--- ESTO FALTABA
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    telegram_app.add_error_handler(error_handler) # <--- ESTO EVITA CRASHES
    
    await telegram_app.initialize()
    return telegram_app

# ---------------------------------------------------------------------
# WEBHOOK
# ---------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    await init_db()
    bot = await init_bot_app()
    if RENDER_EXTERNAL_URL and TELEGRAM_TOKEN:
        webhook_url = f"{RENDER_EXTERNAL_URL}/telegram/{TELEGRAM_TOKEN}"
        await bot.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook OK: {webhook_url}")
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()

@app.post("/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN:
        return JSONResponse(content={"error": "Forbidden"}, status_code=403)
    data = await request.json()
    bot = await init_bot_app()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "TheOneHive 3.0 Active"}
