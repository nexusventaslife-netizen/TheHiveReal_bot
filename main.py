"""
THEONEHIVE 5.0 - DIGNIDAD GLOBAL & PROYECCIONES
Estrategia: Tiers Geoeconómicos + Multiplicador de Rendimiento
"""

import logging
import os
import asyncio
from datetime import datetime
import hashlib
from typing import Optional, Any

# Librerías
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
    ConversationHandler
)

# ---------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
DB_PATH = "theonehive.db"
APP_NAME = "TheOneHive 🌍"

# ESTADOS CONVERSACIÓN
ASK_EMAIL, ASK_COUNTRY = range(2)

# ---------------------------------------------------------------------
# MOTOR ECONÓMICO GLOBAL (TIERS)
# Aquí definimos la "Dignidad" por región
# ---------------------------------------------------------------------
GEO_ECONOMY = {
    "TIER_A": { # USA, Australia, UK, Canadá
        "countries": ["US", "AU", "GB", "CA"],
        "daily_target": 25.0, 
        "currency": "USD",
        "symbol": "$"
    },
    "TIER_B": { # Europa Occidental, Corea, Japón
        "countries": ["ES", "DE", "FR", "IT", "KR", "JP"],
        "daily_target": 20.0,
        "currency": "EUR",
        "symbol": "€"
    },
    "TIER_C": { # Latam, China, Rusia, Brasil
        "countries": ["MX", "AR", "CO", "BR", "CL", "CN", "RU"],
        "daily_target": 15.0,
        "currency": "USD",
        "symbol": "$"
    },
    "TIER_D": { # África, India, Venezuela, Resto
        "countries": ["GLOBAL", "VE", "NG", "IN", "PK", "PH"],
        "daily_target": 6.0,
        "currency": "USD",
        "symbol": "$"
    }
}

# ---------------------------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------------------------
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                first_name TEXT,
                email TEXT,
                country_code TEXT,
                tier TEXT, -- TIER_A, TIER_B, etc.
                
                -- ECONOMÍA PERSONAL
                balance REAL DEFAULT 0.0,
                xp INTEGER DEFAULT 0,
                performance_multiplier REAL DEFAULT 1.0, -- Empieza en 1.0 (100%), puede subir a 1.5 (150%)
                
                created_at TEXT
            )
        """)
        # Tareas con filtro de Tier (Para asegurar el realismo)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                tier_req TEXT, -- Para qué tier es esta tarea
                reward REAL,
                url TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Datos semilla (Ejemplos reales)
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, tier_req, reward, url) VALUES (1, 'Encuesta Premium (Finanzas)', 'TIER_A', 2.50, 'https://google.com')")
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, tier_req, reward, url) VALUES (2, 'Instalar App Ligera', 'TIER_D', 0.20, 'https://google.com')")
        await db.execute("INSERT OR IGNORE INTO tasks (id, title, tier_req, reward, url) VALUES (3, 'Registro Exchange', 'TIER_C', 1.50, 'https://google.com')")
        await db.commit()

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

# ---------------------------------------------------------------------
# LÓGICA DE DETERMINACIÓN DE TIER
# ---------------------------------------------------------------------
def get_tier_info(country_code: str):
    code = country_code.upper()
    for tier, data in GEO_ECONOMY.items():
        if code in data["countries"]:
            return tier, data
    return "TIER_D", GEO_ECONOMY["TIER_D"]

# ---------------------------------------------------------------------
# FLUJO DE INICIO (PERFILADO)
# ---------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if user and user['email']:
        await dashboard_pro(update, context)
        return ConversationHandler.END
        
    await update.message.reply_text(
        "👋 **Bienvenido al Sistema Global TheOneHive.**\n\n"
        "Nuestra misión es garantizarte un ingreso digno según tu ubicación.\n"
        "Para calcular tu potencial de ganancias, necesitamos configurar tu perfil.\n\n"
        "📧 **1. Escribe tu Email (para notificarte pagos):**"
    )
    return ASK_EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    await update.message.reply_text(
        "🌍 **2. ¿Desde qué país te conectas?**\n\n"
        "Escribe el código de 2 letras (Ej: MX para México, ES para España, VE para Venezuela, US para USA)."
    )
    return ASK_COUNTRY

async def receive_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country_code = update.message.text.upper().strip()
    email = context.user_data['email']
    user = update.effective_user
    
    # Determinar Tier y Economía
    tier_name, tier_data = get_tier_info(country_code)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, first_name, email, country_code, tier, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET email=excluded.email, country_code=excluded.country_code, tier=excluded.tier
        """, (user.id, user.first_name, email, country_code, tier_name, datetime.utcnow().isoformat()))
        await db.commit()
        
    await update.message.reply_text(f"✅ Perfil Configurado: **{country_code} (Nivel {tier_name})**\n\nHemos ajustado las tareas y pagos a tu economía local.")
    await dashboard_pro(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registro cancelado.")
    return ConversationHandler.END

# ---------------------------------------------------------------------
# DASHBOARD PRO (EL ANZUELO VISUAL)
# ---------------------------------------------------------------------
async def dashboard_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user: return # Safety check
    
    _, eco_data = get_tier_info(user['country_code'])
    symbol = eco_data['symbol']
    
    # CÁLCULOS DE PROYECCIÓN (EL REALISMO)
    base_daily = eco_data['daily_target']
    multiplier = user['performance_multiplier'] # Si trabaja mejor, gana más
    
    potential_daily = base_daily * multiplier
    projected_weekly = potential_daily * 7
    projected_monthly = potential_daily * 30
    
    # Barra de optimización (Gamificación)
    opt_percent = int((multiplier - 1.0) * 200) # Ejemplo visual
    progress_bar = "▓" * (opt_percent // 10) + "░" * (10 - (opt_percent // 10))
    
    msg = (
        f"📊 **TU CENTRO DE MANDO FINANCIERO** | {user['country_code']}\n\n"
        f"💰 **Saldo Real:** {symbol}{user['balance']:.2f}\n"
        f"🚀 **Rendimiento:** {multiplier:.1f}x (Normal)\n"
        f"[{progress_bar}] Optimización: {opt_percent}%\n\n"
        
        f"🔮 **TUS PROYECCIONES REALES:**\n"
        f"📅 Día: {symbol}{potential_daily:.2f} (Objetivo: {symbol}{base_daily})\n"
        f"🗓 Semanal: {symbol}{projected_weekly:.2f}\n"
        f"📆 **Mensual: {symbol}{projected_monthly:.2f}**\n\n"
        
        f"💡 *Consejo: Para alcanzar los {symbol}{projected_monthly:.2f}, debes completar 3 tareas diarias y mantener calidad alta.*"
    )
    
    keyboard = [
        ["⚡️ Optimizar Ingresos (Tareas)", "📈 Ver Estadísticas"],
        ["💸 Retirar Fondos", "🌍 Mi Perfil Global"]
    ]
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="Markdown")

# ---------------------------------------------------------------------
# LISTA DE TAREAS FILTRADA POR PAÍS/TIER
# ---------------------------------------------------------------------
async def optimized_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    user_tier = user['tier']
    _, eco_data = get_tier_info(user['country_code'])
    
    # Filtramos: Mostramos tareas de su Tier O tareas globales (Tier D)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = f"SELECT * FROM tasks WHERE (tier_req = '{user_tier}' OR tier_req = 'TIER_D') AND is_active=1"
        async with db.execute(sql) as cursor:
            tasks = await cursor.fetchall()
            
    if not tasks:
        await update.message.reply_text("🔍 Buscando tareas de alto valor para tu región... Intenta en 10 min.")
        return

    msg = f"⚡️ **TAREAS DE ALTO RENDIMIENTO ({user['country_code']})**\n"
    msg += "Estas tareas han sido seleccionadas para cumplir tu proyección mensual.\n\n"
    
    keyboard = []
    for t in tasks:
        btn_text = f"{t['title']} | Gana {eco_data['symbol']}{t['reward']}"
        keyboard.append([InlineKeyboardButton(btn_text, url=t['url'])])
        
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Optimizar" in text: await optimized_tasks(update, context)
    elif "Estadísticas" in text: await update.message.reply_text("📈 Gráficos de rendimiento próximamente.")
    elif "Retirar" in text: await update.message.reply_text("💸 Retiros procesados vía USDT (TRC20) o Binance Pay para evitar comisiones.")
    elif "Perfil" in text: await dashboard_pro(update, context)

# ---------------------------------------------------------------------
# SETUP TÉCNICO
# ---------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Error:", exc_info=context.error)

async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            ASK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_country)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    telegram_app.add_handler(conv_handler)
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

@app.on_event("startup")
async def startup():
    await init_db()
    bot = await init_bot_app()
    if RENDER_EXTERNAL_URL: await bot.bot.set_webhook(f"{RENDER_EXTERNAL_URL}/telegram/{TELEGRAM_TOKEN}")
    await bot.start()

@app.post("/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN: return JSONResponse(status_code=403, content={})
    data = await request.json()
    bot = await init_bot_app()
    await bot.process_update(Update.de_json(data, bot.bot))
    return {"ok": True}
