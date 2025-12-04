"""
THEONEHIVE 2.0 - PLATAFORMA DISRUPTIVA DE INGRESOS Y VIRALIDAD
Optimizado para Render (Python 3.11+) + Telegram Bot API v20+
"""

import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
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
# CONFIGURACIÓN Y LOGS
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("TheOneHive")

# Variables de Entorno
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
DB_PATH = "theonehive.db"

# Validación crítica para Render
if not TELEGRAM_TOKEN:
    logger.error("CRITICAL: TELEGRAM_TOKEN no encontrado en variables de entorno.")

# Constantes de Negocio
APP_NAME = "TheOneHive 🐝"
PREMIUM_PRICE = 15.00

# Configuración Avanzada por País (Disruptivo: Ajuste dinámico)
COUNTRY_CONFIG = {
    "GLOBAL": {"currency": "USD", "min_withdraw": 5.0, "cap_daily": 50},
    "US": {"currency": "USD", "min_withdraw": 10.0, "cap_daily": 200},
    "ES": {"currency": "EUR", "min_withdraw": 10.0, "cap_daily": 150},
    "MX": {"currency": "MXN", "min_withdraw": 2.0, "cap_daily": 60}, # ~1200 MXN
    "AR": {"currency": "ARS", "min_withdraw": 1.0, "cap_daily": 40},
    "CO": {"currency": "COP", "min_withdraw": 2.0, "cap_daily": 50},
}

# ---------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None

# ---------------------------------------------------------------------
# BASE DE DATOS (OPTIMIZADA)
# ---------------------------------------------------------------------

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabla Usuarios con Niveles y XP
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
                plan TEXT DEFAULT 'FREE',
                country_code TEXT DEFAULT 'GLOBAL',
                created_at TEXT,
                last_active TEXT
            )
        """)
        
        # Tabla de Tareas (Marketplace)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                reward_usd REAL,
                xp_reward INTEGER,
                type TEXT, -- 'CPA', 'ENCUESTA', 'VIRAL'
                url TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Tabla de Retiros
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                status TEXT DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
                created_at TEXT
            )
        """)
        
        # Precarga de Tareas Mock (Para que el usuario vea algo al inicio)
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, description, reward_usd, xp_reward, type, url) VALUES (1, 'Encuesta de Perfil', 'Completa tus datos básicos', 0.50, 100, 'ENCUESTA', 'https://google.com')")
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, description, reward_usd, xp_reward, type, url) VALUES (2, 'Reto TikTok Viral', 'Sube un video usando #TheOneHive', 2.00, 500, 'VIRAL', 'https://tiktok.com')")
        
        await db.commit()
    logger.info("✅ Base de datos inicializada correctamente.")

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

# Lógica de Niveles (Gamificación)
def calculate_level(xp: int) -> str:
    if xp < 500: return "Novato 🥚"
    if xp < 2000: return "Aprendiz 🐛"
    if xp < 10000: return "Maestro 🐝"
    return "Leyenda 👑"

async def register_user(user: Any, ref_code_input: str = None):
    now = datetime.utcnow().isoformat()
    # Generar código único
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
# BOT HANDLERS
# ---------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    ref_input = args[0] if args else None
    user_data = await register_user(update.effective_user, ref_input)
    
    keyboard = [
        ["🚀 Ganar Dinero (Tareas)", "📱 Retos Virales"],
        ["💰 Mi Billetera", "🏆 Mi Nivel"],
        ["💎 Plan Premium", "👥 Referidos"]
    ]
    
    msg = (
        f"👋 **¡Hola, {user_data['first_name']}!**\n\n"
        f"Bienvenido a **TheOneHive**, el ecosistema donde tus acciones valen oro.\n\n"
        f"🎖 **Nivel Actual:** {user_data['level']}\n"
        f"💸 **Saldo:** ${user_data['balance']:.2f} USD\n\n"
        "¿Qué quieres hacer hoy?"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), 
        parse_mode="Markdown"
    )

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Aquí se conecta tu lógica de "Algoritmo de Optimización"
    # Simulamos traer las mejores tareas para el usuario
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE is_active=1 LIMIT 5") as cursor:
            tasks = await cursor.fetchall()
            
    if not tasks:
        await update.message.reply_text("🔍 Buscando nuevas ofertas para tu perfil... intenta en un minuto.")
        return

    keyboard = []
    msg = "📋 **TAREAS DISPONIBLES (Optimizadas para ti):**\n\n"
    
    for t in tasks:
        icon = "📹" if t['type'] == 'VIRAL' else "📝"
        msg += f"{icon} **{t['title']}**\nRecompensa: ${t['reward_usd']} + {t['xp_reward']} XP\n\n"
        keyboard.append([InlineKeyboardButton(f"Hacer: {t['title']}", url=t['url'])])
        
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def viral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Innovación: Monetización por contenido
    msg = (
        "🎬 **ZONA VIRAL - Gana por Crear Contenido**\n\n"
        "1. Crea un video en TikTok/Shorts/Reels sobre TheOneHive.\n"
        "2. Usa el hashtag #TheOneHiveMoney.\n"
        "3. Envíanos el link aquí (próximamente validación automática).\n\n"
        "🔥 **Bono:** $2.00 USD por cada video que supere las 1k vistas.\n"
        "🚀 **Viralidad:** Si tu video llega a 100k, te damos el **Plan Premium GRATIS**."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    country = COUNTRY_CONFIG.get(user['country_code'], COUNTRY_CONFIG['GLOBAL'])
    
    msg = (
        f"💰 **TU BILLETERA DIGITAL**\n\n"
        f"💵 **Saldo Disponible:** ${user['balance']:.2f} USD\n"
        f"🪙 **Tokens Invisibles:** {user['tokens_invisibles']}\n"
        f"🕐 **Retiros Pendientes:** $0.00\n\n"
        f"🌍 **Configuración ({user['country_code']}):**\n"
        f"- Mínimo retiro: ${country['min_withdraw']} USD\n"
        f"- Moneda local: {country['currency']}\n\n"
        "Pulsa abajo para retirar tus ganancias."
    )
    
    kb = [[InlineKeyboardButton("💸 RETIRAR AHORA", callback_data="withdraw_start")]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    next_level_xp = 500 if user['xp'] < 500 else 2000
    progress = (user['xp'] / next_level_xp) * 100
    
    msg = (
        f"🏆 **TU PROGRESO**\n\n"
        f"👤 **Rango:** {user['level']}\n"
        f"✨ **XP Actual:** {user['xp']} / {next_level_xp}\n"
        f"📊 **Progreso:** {progress:.1f}%\n\n"
        "💡 *Sube de nivel para desbloquear tareas VIP mejor pagadas.*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Ganar Dinero" in text: await tasks_command(update, context)
    elif "Retos Virales" in text: await viral_command(update, context)
    elif "Mi Billetera" in text: await wallet_command(update, context)
    elif "Mi Nivel" in text: await level_command(update, context)
    elif "Referidos" in text: 
        user = await get_user(update.effective_user.id)
        link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
        await update.message.reply_text(f"👥 **Invita y Gana**\n\nComparte tu enlace:\n`{link}`", parse_mode="Markdown")
    elif "Premium" in text:
        await update.message.reply_text("💎 **Plan Premium ($15/mes)**\n\n- Tareas x2 valor\n- Retiros instantáneos\n- Soporte VIP\n\n_Próximamente pagos con Cripto/Stripe._", parse_mode="Markdown")

# ---------------------------------------------------------------------
# INICIALIZACIÓN DEL BOT
# ---------------------------------------------------------------------

async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    
    logger.info("🚀 Inicializando Bot TheOneHive...")
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    await telegram_app.initialize()
    return telegram_app

# ---------------------------------------------------------------------
# ENDPOINTS RENDER
# ---------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    await init_db()
    bot = await init_bot_app()
    
    # Configurar Webhook
    if RENDER_EXTERNAL_URL and TELEGRAM_TOKEN:
        webhook_url = f"{RENDER_EXTERNAL_URL}/telegram/{TELEGRAM_TOKEN}"
        await bot.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook establecido: {webhook_url}")
    
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
    return {"status": "active", "system": "TheOneHive 2.0"}
