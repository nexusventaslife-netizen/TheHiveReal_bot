"""
THEONEHIVE 7.0 - GLOBAL SYSTEM FINAL
Correcciones:
1. Reset automático de DB (Arregla error 'telegram_id')
2. Endpoints Web (Arregla error 404)
3. Economía Global y Proyecciones
"""

import logging
import os
import asyncio
from datetime import datetime
from typing import Optional, Any

# Librerías
import asyncpg 
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
DATABASE_URL = os.environ.get("DATABASE_URL")

APP_NAME = "TheOneHive 🌍"

# ESTADOS CONVERSACIÓN
ASK_EMAIL, ASK_COUNTRY = range(2)

# ECONOMÍA GLOBAL (TIERS)
GEO_ECONOMY = {
    "TIER_A": {"countries": ["US", "AU", "GB", "CA"], "daily_target": 25.0, "currency": "USD", "symbol": "$"},
    "TIER_B": {"countries": ["ES", "DE", "FR", "IT", "KR", "JP"], "daily_target": 20.0, "currency": "EUR", "symbol": "€"},
    "TIER_C": {"countries": ["MX", "AR", "CO", "BR", "CL", "CN", "RU"], "daily_target": 15.0, "currency": "USD", "symbol": "$"},
    "TIER_D": {"countries": ["GLOBAL", "VE", "NG", "IN", "PK"], "daily_target": 6.0, "currency": "USD", "symbol": "$"}
}

# ---------------------------------------------------------------------
# GESTIÓN DE BASE DE DATOS (POSTGRESQL)
# ---------------------------------------------------------------------
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None
db_pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Inicializa Postgres y resetea esquema corrupto"""
    global db_pool
    if not DATABASE_URL:
        logger.error("CRITICAL: No DATABASE_URL found.")
        return

    # Crear pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    
    async with db_pool.acquire() as conn:
        # --- SOLUCIÓN ERROR DB ---
        # Borramos tablas viejas para asegurar que las nuevas tengan las columnas correctas
        await conn.execute("DROP TABLE IF EXISTS users CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS tasks CASCADE;")
        # -------------------------

        # Crear Tabla Usuarios Correcta
        await conn.execute("""
            CREATE TABLE users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                email TEXT,
                country_code TEXT,
                tier TEXT,
                balance DOUBLE PRECISION DEFAULT 0.0,
                xp INTEGER DEFAULT 0,
                performance_multiplier DOUBLE PRECISION DEFAULT 1.0,
                created_at TEXT
            )
        """)
        
        # Crear Tabla Tareas
        await conn.execute("""
            CREATE TABLE tasks (
                id SERIAL PRIMARY KEY,
                title TEXT,
                tier_req TEXT,
                reward DOUBLE PRECISION,
                url TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Datos Semilla
        await conn.execute("INSERT INTO tasks (title, tier_req, reward, url) VALUES ($1, $2, $3, $4)", 'Encuesta Premium (Finanzas)', 'TIER_A', 2.50, 'https://google.com')
        await conn.execute("INSERT INTO tasks (title, tier_req, reward, url) VALUES ($1, $2, $3, $4)", 'Instalar App Ligera', 'TIER_D', 0.20, 'https://google.com')
        await conn.execute("INSERT INTO tasks (title, tier_req, reward, url) VALUES ($1, $2, $3, $4)", 'Registro Exchange', 'TIER_C', 1.50, 'https://google.com')
            
    logger.info("✅ Base de Datos RESETEADA y lista (Error telegram_id corregido).")

async def get_user(tg_id: int):
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", tg_id)
        return dict(row) if row else None

def get_tier_info(country_code: str):
    code = str(country_code).upper()
    for tier, data in GEO_ECONOMY.items():
        if code in data["countries"]:
            return tier, data
    return "TIER_D", GEO_ECONOMY["TIER_D"]

# ---------------------------------------------------------------------
# BOT HANDLERS
# ---------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if user and user['email']:
        await dashboard_pro(update, context)
        return ConversationHandler.END
        
    await update.message.reply_text(
        "👋 **Bienvenido al Sistema Global TheOneHive.**\n\n"
        "Datos seguros en la Nube ☁️.\n"
        "Para calcular tu sueldo digno según tu país, necesitamos configurar tu perfil.\n\n"
        "📧 **1. Escribe tu Email:**"
    )
    return ASK_EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    await update.message.reply_text(
        "🌍 **2. ¿Desde qué país te conectas?**\n"
        "(Ej: MX, ES, VE, US, AR)"
    )
    return ASK_COUNTRY

async def receive_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country_code = update.message.text.upper().strip()
    email = context.user_data['email']
    user = update.effective_user
    
    tier_name, _ = get_tier_info(country_code)
    created_at = datetime.utcnow().isoformat()
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, email, country_code, tier, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (telegram_id) 
            DO UPDATE SET email = $3, country_code = $4, tier = $5
        """, user.id, user.first_name, email, country_code, tier_name, created_at)
        
    await update.message.reply_text(f"✅ Perfil Guardado en Nube: **{country_code} ({tier_name})**")
    await dashboard_pro(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelado.")
    return ConversationHandler.END

async def dashboard_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user: return
    
    _, eco_data = get_tier_info(user['country_code'])
    symbol = eco_data['symbol']
    
    base_daily = eco_data['daily_target']
    multiplier = user['performance_multiplier']
    potential_daily = base_daily * multiplier
    projected_monthly = potential_daily * 30
    
    msg = (
        f"📊 **DASHBOARD FINANCIERO** | {user['country_code']}\n\n"
        f"💰 **Saldo:** {symbol}{user['balance']:.2f}\n"
        f"🚀 **Nivel Rendimiento:** {multiplier:.1f}x\n\n"
        f"🔮 **PROYECCIÓN MENSUAL:**\n"
        f"💵 **{symbol}{projected_monthly:.2f}**\n"
        f"_(Basado en completar tus tareas diarias)_"
    )
    
    keyboard = [["⚡️ Tareas Optimizadas", "💸 Retirar"], ["🌍 Mi Perfil"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="Markdown")

async def optimized_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user: return
    tier = user['tier']
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM tasks WHERE (tier_req = $1 OR tier_req = 'TIER_D') AND is_active=1", tier)
    
    if not rows:
        await update.message.reply_text("🔍 Buscando tareas...")
        return

    keyboard = []
    for r in rows:
        btn = f"{r['title']} | +{r['reward']}"
        keyboard.append([InlineKeyboardButton(btn, url=r['url'])])
        
    await update.message.reply_text("⚡️ **TAREAS DISPONIBLES**", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------------------------------------------------------
# SETUP & ROUTES (SOLUCIÓN ERROR 404)
# ---------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception:", exc_info=context.error)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Tareas" in text: await optimized_tasks(update, context)
    elif "Retirar" in text: await update.message.reply_text("💸 Retiros automáticos vía USDT/Binance.")
    elif "Perfil" in text: await dashboard_pro(update, context)

async def init_bot_app():
    global telegram_app
    if telegram_app: return telegram_app
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={ASK_EMAIL: [MessageHandler(filters.TEXT, receive_email)], ASK_COUNTRY: [MessageHandler(filters.TEXT, receive_country)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    telegram_app.add_handler(conv)
    telegram_app.add_handler(MessageHandler(filters.TEXT, handle_text))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    return telegram_app

# --- NUEVOS ENDPOINTS PARA ARREGLAR ERROR 404 ---
@app.get("/")
async def root():
    return {"status": "Online", "message": "TheOneHive Bot is Running 🟢"}

@app.get("/health")
async def health():
    return {"status": "ok"}
# ------------------------------------------------

@app.on_event("startup")
async def startup():
    await init_db()
    bot = await init_bot_app()
    if RENDER_EXTERNAL_URL: await bot.bot.set_webhook(f"{RENDER_EXTERNAL_URL}/telegram/{TELEGRAM_TOKEN}")
    await bot.start()

@app.on_event("shutdown")
async def shutdown():
    if telegram_app: await telegram_app.stop(); await telegram_app.shutdown()
    if db_pool: await db_pool.close()

@app.post("/telegram/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN: return JSONResponse(status_code=403, content={})
    data = await request.json()
    bot = await init_bot_app()
    await bot.process_update(Update.de_json(data, bot.bot))
    return {"ok": True}
