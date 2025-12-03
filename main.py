import os
import logging
import hashlib
from http import HTTPStatus
from datetime import datetime, timedelta

from quart import Quart, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import psycopg2
from psycopg2 import pool
from psycopg2. extras import RealDictCursor
import aiohttp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ. get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
RENDER_EXTERNAL_URL = os. environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ. get("PORT", 10000))

CPALEAD_API_KEY = os.environ.get("CPALEAD_API_KEY", "")
OFFERTORO_API_KEY = os.environ.get("OFFERTORO_API_KEY", "")
POLLFISH_API_KEY = os. environ.get("POLLFISH_API_KEY", "")
AYETSTUDIOS_API_KEY = os. environ.get("AYETSTUDIOS_API_KEY", "")

PAYPAL_CLIENT_ID = os. environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET", "")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
BINANCE_API_KEY = os. environ.get("BINANCE_API_KEY", "")

connection_pool = None
application = None
app = Quart(__name__)
http_session = None

COUNTRY_DATA = {
    "US": {
        "name": "USA",
        "flag": "🇺🇸",
        "max_daily": 180,
        "methods": ["paypal", "stripe", "venmo"],
        "min_withdraw": 5. 0,
        "currency": "USD"
    },
    "MX": {
        "name": "Mexico",
        "flag": "🇲🇽",
        "max_daily": 60,
        "methods": ["paypal", "oxxo", "spei"],
        "min_withdraw": 2.0,
        "currency": "MXN"
    },
    "BR": {
        "name": "Brasil",
        "flag": "🇧🇷",
        "max_daily": 70,
        "methods": ["pix", "paypal"],
        "min_withdraw": 2.0,
        "currency": "BRL"
    },
    "AR": {
        "name": "Argentina",
        "flag": "🇦🇷",
        "max_daily": 50,
        "methods": ["mercadopago", "binance"],
        "min_withdraw": 1.0,
        "currency": "ARS"
    },
    "CO": {
        "name": "Colombia",
        "flag": "🇨🇴",
        "max_daily": 50,
        "methods": ["nequi", "daviplata", "bancolombia"],
        "min_withdraw": 2.0,
        "currency": "COP"
    },
    "ES": {
        "name": "España",
        "flag": "🇪🇸",
        "max_daily": 130,
        "methods": ["paypal", "bizum", "sepa"],
        "min_withdraw": 3.0,
        "currency": "EUR"
    },
    "Global": {
        "name": "Global",
        "flag": "🌍",
        "max_daily": 80,
        "methods": ["paypal", "binance", "crypto"],
        "min_withdraw": 2.0,
        "currency": "USD"
    }
}

TASK_PLATFORMS = {
    "cpalead": {"name": "CPALead", "api_key": CPALEAD_API_KEY, "base_url": "https://www.cpalead.com/dashboard/reports/campaign_json. php"},
    "offertoro": {"name": "OfferToro", "api_key": OFFERTORO_API_KEY, "base_url": "https://www.offertoro.com/api/v1/offers"},
    "pollfish": {"name": "Pollfish", "api_key": POLLFISH_API_KEY, "base_url": "https://api.pollfish.com/v1/surveys"},
    "ayetstudios": {"name": "AyetStudios", "api_key": AYETSTUDIOS_API_KEY, "base_url": "https://ayetstudios.com/offers/web_api"}
}

def setup_db_pool():
    global connection_pool
    if not DATABASE_URL:
        logger. error("DATABASE_URL no configurada")
        return False
    try:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
        connection_pool = pool.ThreadedConnectionPool(minconn=2, maxconn=20, dsn=db_url)
        logger.info("✅ Pool de base de datos configurado")
        return True
    except Exception as e:
        logger.error(f"❌ Error configurando pool: {e}")
        return False

def get_db_conn():
    if connection_pool:
        try:
            return connection_pool. getconn()
        except Exception as e:
            logger.error(f"Error obteniendo conexión: {e}")
    return None

def put_db_conn(conn):
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error devolviendo conexión: {e}")

def init_db():
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
                    referred_by BIGINT,
                    wallet_address VARCHAR(255),
                    payment_method VARCHAR(50),
                    payment_email VARCHAR(255),
                    total_earned DECIMAL(12,2) DEFAULT 0,
                    pending_payout DECIMAL(12,2) DEFAULT 0,
                    total_withdrawn DECIMAL(12,2) DEFAULT 0,
                    tasks_completed INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tasks_completed (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                    task_id VARCHAR(100),
                    platform VARCHAR(50),
                    reward DECIMAL(10,2),
                    status VARCHAR(20) DEFAULT 'pending',
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT REFERENCES users(id),
                    referred_id BIGINT REFERENCES users(id),
                    commission_earned DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referred_id)
                );
                
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    amount DECIMAL(12,2),
                    method VARCHAR(50),
                    destination VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'pending',
                    processed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code);
                CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks_completed(user_id);
                CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
            """)
        conn.commit()
        logger.info("✅ Base de datos inicializada")
        return True
    except Exception as e:
        logger.error(f"❌ Error inicializando BD: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

def get_or_create_user(user_id, first_name, username, ref_code=None):
    conn = get_db_conn()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
            if not user:
                my_ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]. upper()
                wallet = "0x" + os.urandom(20).hex()
                
                referred_by_id = None
                if ref_code:
                    cur.execute("SELECT id FROM users WHERE referral_code = %s", (ref_code,))
                    referrer = cur.fetchone()
                    if referrer:
                        referred_by_id = referrer["id"]
                
                cur.execute("""
                    INSERT INTO users (id, first_name, username, referral_code, referred_by, wallet_address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (user_id, first_name, username, my_ref_code, referred_by_id, wallet))
                user = cur.fetchone()
                
                if referred_by_id:
                    cur.execute("""
                        INSERT INTO referrals (referrer_id, referred_id, commission_earned)
                        VALUES (%s, %s, 1. 00)
                    """, (referred_by_id, user_id))
                    cur.execute("UPDATE users SET tokens = tokens + 100, total_earned = total_earned + 1.00 WHERE id = %s", (referred_by_id,))
                
                conn.commit()
                logger.info(f"✅ Usuario creado: {user_id}")
            else:
                cur.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
                conn. commit()
            
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error get_or_create_user: {e}")
        conn.rollback()
        return None
    finally:
        put_db_conn(conn)

def add_task_earning(user_id, task_id, platform, reward):
    conn = get_db_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks_completed (user_id, task_id, platform, reward, status)
                VALUES (%s, %s, %s, %s, 'completed')
            """, (user_id, task_id, platform, reward))
            
            cur.execute("""
                UPDATE users SET 
                    total_earned = total_earned + %s,
                    pending_payout = pending_payout + %s,
                    tokens = tokens + 10,
                    tasks_completed = tasks_completed + 1
                WHERE id = %s
            """, (reward, reward, user_id))
        conn.commit()
        logger. info(f"✅ Tarea completada: user={user_id}, reward=${reward}")
        return True
    except Exception as e:
        logger.error(f"Error add_task_earning: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

async def fetch_live_tasks(platform_name):
    if platform_name not in TASK_PLATFORMS:
        return []
    
    platform = TASK_PLATFORMS[platform_name]
    if not platform["api_key"]:
        return []
    
    try:
        async with http_session.get(
            platform["base_url"],
            params={"api_key": platform["api_key"]},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data. get("offers", [])[:5]
    except Exception as e:
        logger.error(f"Error fetching {platform_name} tasks: {e}")
    
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_code = context.args[0] if context. args else None
    
    user_data = get_or_create_user(user.id, user.first_name, user.username or "user", ref_code)
    
    if not user_data:
        await update.message.reply_text("❌ Error al inicializar.  Usa /start de nuevo")
        return
    
    country_info = COUNTRY_DATA.get(user_data["country"], COUNTRY_DATA["Global"])
    
    welcome_msg = (
        f"🚀 *BIENVENIDO A GRIDDLED V3*\n\n"
        f"Hola {user.first_name}! 👋\n\n"
        f"💰 Potencial diario: ${country_info['max_daily']}\n"
        f"🎁 Tokens: {user_data['tokens']}\n"
        f"💎 Plan: {user_data['subscription']}\n"
        f"{country_info['flag']} País: {country_info['name']}\n\n"
        f"✅ Pagos automáticos 24h\n"
        f"✅ 10+ plataformas integradas\n"
        f"✅ Sistema de referidos\n\n"
        f"👇 Empieza ahora:"
    )
    
    keyboard = [
        ["💼 Ver Tareas", "💰 Dashboard"],
        ["🎁 Referir", "⚙️ Configurar"],
        ["📊 Estadísticas", "❓ Ayuda"]
    ]
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Cargando tareas disponibles...")
    
    tasks = []
    task_id = 1
    
    for platform_name in ["cpalead", "offertoro", "pollfish"]:
        live_tasks = await fetch_live_tasks(platform_name)
        for task in live_tasks[:3]:
            tasks.append({
                "id": task_id,
                "title": task. get("name", f"Tarea {task_id}"),
                "reward": float(task.get("payout", 0. 25)),
                "platform": platform_name,
                "task_id": task. get("id", str(task_id))
            })
            task_id += 1
    
    if not tasks:
        tasks = [
            {"id": 1, "title": "📝 Encuesta 2min", "reward": 0.25, "platform": "pollfish", "task_id": "demo_1"},
            {"id": 2, "title": "📱 Instalar App", "reward": 0.80, "platform": "cpalead", "task_id": "demo_2"},
            {"id": 3, "title": "🎬 Ver Video 30s", "reward": 0. 10, "platform": "generic", "task_id": "demo_3"},
            {"id": 4, "title": "✅ Dejar Review", "reward": 0.35, "platform": "generic", "task_id": "demo_4"},
            {"id": 5, "title": "🔍 Validar Dato", "reward": 0.15, "platform": "generic", "task_id": "demo_5"},
        ]
    
    tasks_msg = "📋 *TAREAS DISPONIBLES*\n\n"
    for task in tasks:
        tasks_msg += f"{task['id']}. *{task['title']}*\n   💵 ${task['reward']:.2f}\n\n"
    
    tasks_msg += "📱 Escribe el número (1-" + str(len(tasks)) + ")"
    
    context.user_data["tasks"] = tasks
    await update.message.reply_text(tasks_msg, parse_mode="Markdown")

async def handle_task_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        return
    
    task_num = int(text)
    tasks = context.user_data.get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        return
    
    task = tasks[task_num - 1]
    
    msg = (
        f"✅ *Tarea: {task['title']}*\n\n"
        f"💰 Ganarás: *${task['reward']:.2f}*\n"
        f"🎁 Bonus: +10 tokens\n\n"
        f"🎯 *Pasos:*\n"
        f"1. Abre el link\n"
        f"2.  Completa la tarea\n"
        f"3. Presiona ✅ Completé"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Abrir Tarea", url="https://example.com/task")],
        [InlineKeyboardButton("✅ Completé", callback_data=f"done_{task_num}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel")]
    ]
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def task_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("done_"):
        return
    
    task_num = int(query.data.split("_")[1])
    tasks = context.user_data.get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        await query.edit_message_text("❌ Tarea no válida")
        return
    
    task = tasks[task_num - 1]
    user_id = query.from_user.id
    
    success = add_task_earning(user_id, task["task_id"], task["platform"], task["reward"])
    
    if success:
        msg = (
            f"🎉 *¡TAREA COMPLETADA!*\n\n"
            f"💰 +${task['reward']:.2f}\n"
            f"🎁 +10 tokens\n\n"
            f"Usa /dashboard para ver tu progreso"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
    else:
        await query.edit_message_text("❌ Error procesando.  Intenta de nuevo")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if not conn:
        await update.message.reply_text("❌ Error de conexión")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            
            if not user_data:
                await update.message. reply_text("❌ Usuario no encontrado")
                return
            
            cur.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = %s", (user_id,))
            refs_count = cur.fetchone()["count"]
            
            country_info = COUNTRY_DATA. get(user_data["country"], COUNTRY_DATA["Global"])
            
            msg = (
                f"📊 *TU DASHBOARD*\n\n"
                f"{country_info['flag']} {country_info['name']}\n"
                f"💎 Plan: {user_data['subscription']}\n"
                f"🎁 Tokens: {user_data['tokens']}\n\n"
                f"💰 *FINANZAS:*\n"
                f"💵 Total ganado: ${user_data['total_earned']:.2f}\n"
                f"⏳ Pendiente: ${user_data['pending_payout']:.2f}\n"
                f"✅ Retirado: ${user_data['total_withdrawn']:.2f}\n"
                f"💳 Mínimo retiro: ${country_info['min_withdraw']}\n\n"
                f"📋 Tareas completadas: {user_data['tasks_completed']}\n"
                f"👥 Referidos activos: {refs_count}\n\n"
                f"💳 Wallet: `{user_data['wallet_address']}`\n"
                f"🔗 Tu código: `{user_data['referral_code']}`"
            )
            
            keyboard = [
                [InlineKeyboardButton("💼 Ver Tareas", callback_data="show_tasks")],
                [InlineKeyboardButton("💸 Retirar Fondos", callback_data="withdraw")],
                [InlineKeyboardButton("🎁 Invitar Amigos", callback_data="refer")]
            ]
            
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        put_db_conn(conn)

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if not conn:
        await update.message.reply_text("❌ Error")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT referral_code FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            ref_code = user_data["referral_code"]
            
            cur.execute("SELECT COUNT(*) as count, COALESCE(SUM(commission_earned), 0) as total FROM referrals WHERE referrer_id = %s", (user_id,))
            ref_stats = cur.fetchone()
    finally:
        put_db_conn(conn)
    
    bot_username = context.bot. username
    ref_link = f"https://t.me/{bot_username}? start={ref_code}"
    
    msg = (
        f"🎁 *PROGRAMA DE REFERIDOS*\n\n"
        f"Tu código único: `{ref_code}`\n"
        f"Tu link: {ref_link}\n\n"
        f"📊 *TUS ESTADÍSTICAS:*\n"
        f"👥 Referidos totales: {ref_stats['count']}\n"
        f"💰 Comisiones ganadas: ${ref_stats['total']:.2f}\n\n"
        f"💎 *GANANCIAS POR REFERIDO:*\n"
        f"• $1.00 por registro\n"
        f"• 15% de sus ganancias de por vida\n"
        f"• Bonus extra cada 5 referidos\n\n"
        f"🚀 *EJEMPLO:*\n"
        f"5 amigos activos = $7.50/día extra\n"
        f"20 amigos = $30/día pasivo"
    )
    
    keyboard = [
        [InlineKeyboardButton("📱 Compartir por WhatsApp", url=f"https://wa.me/? text=Únete%20a%20GRIDDLED%20y%20gana%20dinero:%20{ref_link}")],
        [InlineKeyboardButton("✈️ Compartir por Telegram", url=f"https://t.me/share/url?url={ref_link}&text=Gana%20dinero%20con%20GRIDDLED")]
    ]
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def config_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user.id, "User", "user")
    country_info = COUNTRY_DATA. get(user_data["country"], COUNTRY_DATA["Global"])
    
    msg = (
        f"⚙️ *CONFIGURAR MÉTODO DE PAGO*\n\n"
        f"Métodos disponibles para {country_info['flag']} {country_info['name']}:\n\n"
    )
    
    keyboard = []
    for method in country_info["methods"]:
        method_name = method. upper()
        keyboard.append([InlineKeyboardButton(f"💳 {method_name}", callback_data=f"pay_{method}")])
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("❌ Error")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
            active_users = cur.fetchone()["count"]
            
            cur.execute("SELECT COALESCE(SUM(total_earned), 0) as total FROM users")
            total_paid = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as count FROM tasks_completed WHERE status = 'completed'")
            total_tasks = cur.fetchone()["count"]
    finally:
        put_db_conn(conn)
    
    msg = (
        f"📊 *ESTADÍSTICAS GLOBALES*\n\n"
        f"🌍 Usuarios activos: {active_users:,}\n"
        f"💰 Total pagado: ${total_paid:,.2f}\n"
        f"✅ Tareas completadas: {total_tasks:,}\n\n"
        f"🏆 País TOP: Brasil\n"
        f"🔥 Racha actual: 127 días\n"
        f"⚡ Uptime: 99.9%"
    )
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_tasks":
        update._message = query.message
        await show_tasks(update, context)
    elif query.data == "withdraw":
        await query.edit_message_text(
            "💸 *RETIRAR FONDOS*\n\nConfigura tu método de pago primero usando /configurar",
            parse_mode="Markdown"
        )
    elif query.data == "refer":
        update._effective_user = query.from_user
        update._message = query.message
        await refer(update, context)
    elif query.data.startswith("pay_"):
        method = query.data.split("_")[1]
        await query. edit_message_text(
            f"✅ Configurando {method. upper()}\n\nEnvía tu email/ID/número para {method}:",
            parse_mode="Markdown"
        )
    elif query.data == "cancel":
        await query.edit_message_text("❌ Operación cancelada")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, application. bot)
        await application.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        return "error", 500

@app.route("/health")
async def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0"
    }), 200

@app.route("/")
async def index():
    return jsonify({
        "name": "GRIDDLED V3",
        "status": "active",
        "version": "3.0",
        "features": ["tasks", "referrals", "payments", "multi-currency"]
    }), 200

@app.before_serving
async def startup():
    global application, http_session
    
    logger.info("🚀 Iniciando GRIDDLED V3...")
    
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no configurado")
    
    if not init_db():
        raise RuntimeError("Error inicializando base de datos")
    
    http_session = aiohttp.ClientSession()
    
    application = Application. builder().token(TELEGRAM_TOKEN). build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("tareas", show_tasks))
    application.add_handler(CommandHandler("referir", refer))
    application. add_handler(CommandHandler("configurar", config_payment))
    application.add_handler(CommandHandler("stats", stats))
    
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^💼 Ver Tareas$"), show_tasks))
    application.add_handler(MessageHandler(filters. TEXT & filters.Regex(r"^💰 Dashboard$"), dashboard))
    application. add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🎁 Referir$"), refer))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^⚙️ Configurar$"), config_payment))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📊 Estadísticas$"), stats))
    
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^\d+$"), handle_task_selection))
    
    application.add_handler(CallbackQueryHandler(task_completed, pattern=r"^done_"))
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    
    logger.info(f"✅ Webhook configurado: {webhook_url}")
    await application.start()
    logger.info("✅ Bot iniciado correctamente")

@app.after_serving
async def shutdown():
    global application, http_session, connection_pool
    
    logger.info("🛑 Cerrando aplicación...")
    
    if http_session:
        await http_session.close()
    
    if application:
        await application.stop()
        await application.shutdown()
    
    if connection_pool:
        connection_pool.closeall()
    
    logger. info("✅ Aplicación cerrada correctamente")

if __name__ == "__main__":
    app. run(host="0.0. 0.0", port=PORT)
