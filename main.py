import os
import logging
import asyncio
import json
import hashlib
from http import HTTPStatus
from datetime import datetime

from quart import Quart, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram. ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram. constants import ParseMode

import psycopg2
from psycopg2 import pool
import aiohttp

# === LOGGING ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === CONFIGURACIÓN ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_USER_ID = os. environ.get("ADMIN_USER_ID", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ. get("PORT", 10000))

# APIs Plataformas de Tareas
CPALEAD_ID = os.environ. get("CPALEAD_ID", "")
OFFERTORO_ID = os.environ.get("OFFERTORO_ID", "")
POLLFISH_KEY = os.environ.get("POLLFISH_KEY", "")

# APIs Marketplace
UDEMY_AFFILIATE = os.environ. get("UDEMY_AFFILIATE", "griddled")
FIVERR_AFFILIATE = os.environ.get("FIVERR_AFFILIATE", "griddled")

# === INSTANCIAS ===
connection_pool = None
application = None
app = Quart(__name__)
http_session = None

# === DATOS PAÍSES ===
COUNTRY_DATA = {
    "US": {"name": "🇺🇸 USA", "max_daily": 180, "methods": ["paypal", "stripe"], "min_withdraw": 5. 0},
    "MX": {"name": "🇲🇽 Mexico", "max_daily": 60, "methods": ["paypal", "oxxo"], "min_withdraw": 2.0},
    "BR": {"name": "🇧🇷 Brasil", "max_daily": 70, "methods": ["pix", "paypal"], "min_withdraw": 2. 0},
    "AR": {"name": "🇦🇷 Argentina", "max_daily": 50, "methods": ["mercadopago", "binance"], "min_withdraw": 1.0},
    "CO": {"name": "🇨🇴 Colombia", "max_daily": 50, "methods": ["nequi", "daviplata"], "min_withdraw": 2.0},
    "ES": {"name": "🇪🇸 España", "max_daily": 130, "methods": ["paypal", "bizum"], "min_withdraw": 3.0},
    "Global": {"name": "🌍 Global", "max_daily": 80, "methods": ["paypal", "binance"], "min_withdraw": 2.0}
}

# === MARKETPLACE ===
MARKETPLACE_PLATFORMS = {
    "udemy": {
        "name": "📘 Udemy",
        "url": "https://udemy.com",
        "commission": 15,
        "description": "Cursos de Freelancing, Marketing, Programación"
    },
    "coursera": {
        "name": "🎓 Coursera",
        "url": "https://coursera.org",
        "commission": 20,
        "description": "Certificaciones profesionales"
    },
    "skillshare": {
        "name": "🎨 Skillshare",
        "url": "https://skillshare.com",
        "commission": 25,
        "description": "Diseño, Video, Creatividad"
    },
    "fiverr": {
        "name": "💼 Fiverr",
        "url": "https://fiverr.com",
        "commission": 30,
        "description": "Vende tus servicios freelance"
    },
    "upwork": {
        "name": "👔 Upwork",
        "url": "https://upwork.com",
        "commission": 10,
        "description": "Consigue clientes a largo plazo"
    }
}

# === BASE DE DATOS ===

def setup_db_pool():
    """Configura pool de BD."""
    global connection_pool
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL no configurada")
        return False
    
    try:
        # Corregir URL si es necesario
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=db_url
        )
        logger.info("✅ Pool BD configurado")
        return True
    except Exception as e:
        logger.error(f"❌ Error pool BD: {e}")
        return False

def get_db_conn():
    """Obtiene conexión."""
    if connection_pool:
        try:
            return connection_pool. getconn()
        except Exception as e:
            logger.error(f"Error obteniendo conexión: {e}")
    return None

def put_db_conn(conn):
    """Devuelve conexión."""
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error devolviendo conexión: {e}")

def init_db():
    """Inicializa BD."""
    if not setup_db_pool():
        return False
    
    conn = get_db_conn()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    first_name VARCHAR(255),
                    username VARCHAR(255),
                    country VARCHAR(50) DEFAULT 'Global',
                    subscription VARCHAR(50) DEFAULT 'FREE',
                    tokens INT DEFAULT 100,
                    referral_code VARCHAR(20) UNIQUE,
                    wallet_address VARCHAR(42),
                    total_earned DECIMAL(12,2) DEFAULT 0,
                    pending_payout DECIMAL(12,2) DEFAULT 0,
                    payout_method VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tasks_completed (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                    platform VARCHAR(50),
                    reward DECIMAL(10,2),
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT REFERENCES users(id),
                    referred_id BIGINT REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referred_id)
                );
            """)
        conn.commit()
        logger.info("✅ BD inicializada")
        return True
    except Exception as e:
        logger. error(f"❌ Error BD: {e}")
        conn. rollback()
        return False
    finally:
        put_db_conn(conn)

# === FUNCIONES USUARIO ===

def get_or_create_user(user_id, first_name, username, country="Global", ref_code=None):
    """Obtiene o crea usuario."""
    conn = get_db_conn()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            user = cur.fetchone()
            
            if not user:
                wallet = "0x" + os.urandom(20).hex()
                my_ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]. upper()
                
                cur. execute("""
                    INSERT INTO users (id, first_name, username, wallet_address, referral_code, country)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, first_name, username, country, subscription, tokens, referral_code, 
                             wallet_address, total_earned, pending_payout, payout_method;
                """, (user_id, first_name, username, wallet, my_ref_code, country))
                user = cur.fetchone()
                
                # Si vino por referido
                if ref_code:
                    cur.execute("SELECT id FROM users WHERE referral_code = %s;", (ref_code,))
                    referrer = cur.fetchone()
                    if referrer:
                        referrer_id = referrer[0]
                        cur.execute("""
                            INSERT INTO referrals (referrer_id, referred_id) 
                            VALUES (%s, %s) ON CONFLICT DO NOTHING;
                        """, (referrer_id, user_id))
                        # Bonus para referidor
                        cur.execute("""
                            UPDATE users SET tokens = tokens + 100 WHERE id = %s;
                        """, (referrer_id,))
                
                conn.commit()
                logger.info(f"✅ Usuario creado: {user_id}")
            
            return user
    except Exception as e:
        logger.error(f"Error get_or_create_user: {e}")
        conn.rollback()
        return None
    finally:
        put_db_conn(conn)

def add_task_earning(user_id, platform, reward):
    """Registra tarea completada."""
    conn = get_db_conn()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks_completed (user_id, platform, reward)
                VALUES (%s, %s, %s);
            """, (user_id, platform, reward))
            
            cur.execute("""
                UPDATE users SET 
                    total_earned = total_earned + %s,
                    pending_payout = pending_payout + %s,
                    tokens = tokens + 10
                WHERE id = %s;
            """, (reward, reward, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error add_task: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

# === HANDLERS TELEGRAM ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start."""
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    username = user.username or "user"
    
    # Detectar referido
    ref_code = context.args[0] if context. args else None
    
    user_data = get_or_create_user(user_id, first_name, username, "Global", ref_code)
    
    if not user_data:
        await update.message.reply_text("❌ Error al inicializar.  Usa /start de nuevo")
        return
    
    welcome_msg = f"""
🚀 *¡Bienvenido a GRIDDLED V3!*

Hola {first_name}, la plataforma revolucionaria de ingresos. 

💰 *Potencial diario:* hasta $80
🎁 *Tokens:* {user_data[5] or 100}
💎 *Plan:* {user_data[4]}

✅ Pagos automáticos 24h
✅ 10+ plataformas integradas
✅ Marketplace con comisiones
✅ Sistema de referidos viral

👇 Empezá ahora:
"""
    
    keyboard = [
        ["💼 Ver Tareas", "💰 Dashboard"],
        ["🛒 Marketplace", "🎁 Referir"],
        ["⚙️ Config Pagos", "📊 Stats"]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra tareas."""
    tasks = [
        {"id": 1, "title": "📝 Encuesta 2min", "reward": 0.25, "platform": "pollfish"},
        {"id": 2, "title": "📱 Instalar App", "reward": 0.80, "platform": "cpalead"},
        {"id": 3, "title": "🎬 Ver Video 30s", "reward": 0. 10, "platform": "admob"},
        {"id": 4, "title": "✅ Review", "reward": 0.35, "platform": "generic"},
        {"id": 5, "title": "🔍 Validar Dato", "reward": 0.15, "platform": "generic"},
        {"id": 6, "title": "📸 Etiquetar", "reward": 0.08, "platform": "generic"},
        {"id": 7, "title": "💬 Red Social", "reward": 0. 40, "platform": "generic"},
        {"id": 8, "title": "📊 Research", "reward": 0.60, "platform": "generic"},
    ]
    
    tasks_msg = "📋 *Tareas Disponibles*\n\n"
    
    for task in tasks:
        tasks_msg += f"{task['id']}. *{task['title']}*\n   💵 ${task['reward']:. 2f}\n\n"
    
    tasks_msg += "📱 Escribí el número (1-8)"
    
    context.user_data["tasks"] = tasks
    
    await update.message. reply_text(tasks_msg, parse_mode=ParseMode.MARKDOWN)

async def handle_task_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja número de tarea."""
    text = update.message.text
    
    if not text.isdigit():
        return
    
    task_num = int(text)
    tasks = context.user_data. get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        return
    
    task = tasks[task_num - 1]
    
    msg = f"""
✅ *Tarea: {task['title']}*

💰 Ganarás: *${task['reward']:.2f}*
🎁 +10 tokens

🎯 *Pasos:*
1. Abre el link
2. Completa
3. Presiona ✅
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Abrir", url="https://example.com")],
        [InlineKeyboardButton("✅ Completé", callback_data=f"done_{task_num}")],
        [InlineKeyboardButton("❌ Salir", callback_data="cancel")]
    ]
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback tarea completada."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("done_"):
        return
    
    task_num = int(data.split("_")[1])
    tasks = context.user_data.get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        await query.edit_message_text("❌ Tarea no válida")
        return
    
    task = tasks[task_num - 1]
    user_id = query.from_user.id
    
    success = add_task_earning(user_id, task["platform"], task["reward"])
    
    if success:
        await query.edit_message_text(
            f"🎉 *¡Completada!*\n\n"
            f"💰 +${task['reward']:.2f}\n"
            f"🎁 +10 tokens\n\n"
            f"Usa /dashboard para ver tu progreso",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text("❌ Error.  Intenta de nuevo")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dashboard usuario."""
    user_id = update.effective_user.id
    
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("❌ Error conexión")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT country, subscription, tokens, total_earned, pending_payout, 
                       wallet_address, referral_code
                FROM users WHERE id = %s;
            """, (user_id,))
            data = cur.fetchone()
            
            if not data:
                await update.message.reply_text("❌ Usuario no encontrado")
                return
            
            country, plan, tokens, total, pending, wallet, ref_code = data
            
            cur.execute("""
                SELECT COUNT(*) FROM tasks_completed WHERE user_id = %s;
            """, (user_id,))
            tasks_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM referrals WHERE referrer_id = %s;
            """, (user_id,))
            refs_count = cur.fetchone()[0]
    finally:
        put_db_conn(conn)
    
    country_info = COUNTRY_DATA.get(country, COUNTRY_DATA["Global"])
    
    msg = f"""
📊 *TU DASHBOARD*

🌍 {country_info['name']}
💎 Plan: {plan}
🎁 Tokens: {tokens}

💰 *Finanzas:*
💵 Total: ${total:.2f}
⏳ Pendiente: ${pending:.2f}
💳 Mínimo: ${country_info['min_withdraw']}

📋 Tareas: {tasks_count}
👥 Referidos: {refs_count}

💳 Wallet: `{wallet}`
🔗 Código: `{ref_code}`
"""
    
    keyboard = [
        [InlineKeyboardButton("💼 Tareas", callback_data="tasks")],
        [InlineKeyboardButton("💸 Retirar", callback_data="withdraw")]
    ]
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marketplace."""
    msg = "🛒 *MARKETPLACE*\n\nCursos y servicios con comisión:\n\n"
    
    keyboard = []
    for key, platform in MARKETPLACE_PLATFORMS.items():
        msg += f"{platform['name']}\n💰 Comisión: {platform['commission']}%\n"
        msg += f"📝 {platform['description']}\n\n"
        
        url = f"{platform['url']}?ref={UDEMY_AFFILIATE if key == 'udemy' else FIVERR_AFFILIATE}"
        keyboard.append([InlineKeyboardButton(platform["name"], url=url)])
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Referidos."""
    user_id = update.effective_user.id
    
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("❌ Error")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT referral_code FROM users WHERE id = %s;", (user_id,))
            ref_code = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = %s;", (user_id,))
            count = cur.fetchone()[0]
    finally:
        put_db_conn(conn)
    
    bot_username = context.bot. username
    link = f"https://t.me/{bot_username}?start={ref_code}"
    
    msg = f"""
🎁 *REFERIDOS*

Tu código: `{ref_code}`
Link: {link}

👥 Referidos: {count}

💎 Ganancias:
• $1 por registro
• 15% de por vida

🚀 5 amigos = $7.50/día
"""
    
    keyboard = [
        [InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/? text={link}")],
        [InlineKeyboardButton("✈️ Telegram", url=f"https://t.me/share/url? url={link}")]
    ]
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def config_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Config pagos."""
    msg = """
⚙️ *CONFIGURAR PAGOS*

Métodos:
💳 PayPal
🔶 Binance Pay
💰 AirTM
🇧🇷 PIX (Brasil)
🇲🇽 OXXO (México)

Selecciona:
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 PayPal", callback_data="pay_paypal")],
        [InlineKeyboardButton("🔶 Binance", callback_data="pay_binance")],
        [InlineKeyboardButton("💰 AirTM", callback_data="pay_airtm")]
    ]
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stats globales."""
    msg = """
📊 *STATS GRIDDLED*

🌍 Usuarios: 50,000+
💰 Pagado: $1. 2M
✅ Tareas: 2. 5M

🏆 Top: Brasil
🔥 Racha: 89 días
"""
    
    await update.message.reply_text(msg, parse_mode=ParseMode. MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja callbacks."""
    query = update.callback_query
    data = query.data
    
    if data == "tasks":
        await query.answer()
        # Crear un update simulado para reutilizar show_tasks
        update._message = query.message
        await show_tasks(update, context)
    
    elif data == "withdraw":
        await query.answer()
        await query.edit_message_text(
            "💸 Configura primero tu método de pago\n\n⚙️ Config Pagos",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data. startswith("pay_"):
        method = data. split("_")[1]
        await query.answer()
        await query.edit_message_text(
            f"✅ Configurando {method. upper()}\n\nEnvía tu email/ID:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "cancel":
        await query.answer()
        await query.edit_message_text("❌ Cancelado")

# === QUART ===

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    """Webhook."""
    try:
        data = await request.get_json()
        update = Update.de_json(data, application. bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error webhook: {e}")
    return "ok", HTTPStatus.OK

@app.route("/health", methods=["GET"])
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}, HTTPStatus.OK

@app.route("/", methods=["GET"])
async def index():
    """Root endpoint."""
    return {"status": "GRIDDLED V3 Bot", "version": "3.0"}, HTTPStatus.OK

async def startup():
    """Startup."""
    global application, http_session
    
    logger.info("🚀 Iniciando bot...")
    
    if not init_db():
        logger.error("❌ BD failed")
        return
    
    http_session = aiohttp.ClientSession()
    application = Application. builder().token(TELEGRAM_TOKEN). build()
    
    # HANDLERS
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dashboard", dashboard))
    
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^💼 Ver Tareas$"), show_tasks))
    application.add_handler(MessageHandler(filters. TEXT & filters.Regex(r"^💰 Dashboard$"), dashboard))
    application. add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🛒 Marketplace$"), marketplace))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🎁 Referir$"), refer))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^⚙️ Config Pagos$"), config_payments))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📊 Stats$"), stats))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), handle_task_num))
    
    application.add_handler(CallbackQueryHandler(task_done, pattern=r"^done_"))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook: {webhook_url}")
    
    await application.start()
    logger.info("✅ Bot ON")

async def shutdown():
    """Shutdown."""
    global application, http_session, connection_pool
    
    logger.info("🛑 Cerrando bot...")
    
    if http_session:
        await http_session.close()
    
    if application:
        await application.stop()
        await application.shutdown()
    
    if connection_pool:
        connection_pool.closeall()
    
    logger. info("✅ Bot cerrado correctamente")

# === MAIN ===

if __name__ == "__main__":
    import hypercorn.asyncio
    from hypercorn.config import Config
    
    # Configurar Hypercorn
    config = Config()
    config.bind = [f"0.0.0. 0:{PORT}"]
    config.use_reloader = False
    config.accesslog = "-"
    config.errorlog = "-"
    
    async def main():
        """Main function."""
        await startup()
        try:
            await hypercorn. asyncio.serve(app, config)
        except KeyboardInterrupt:
            pass
        finally:
            await shutdown()
    
    # Ejecutar
    asyncio.run(main())
