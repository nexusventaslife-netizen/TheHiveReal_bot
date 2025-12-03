import os
import logging
import hashlib
from http import HTTPStatus
from datetime import datetime
from functools import wraps

from quart import Quart, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram. error import TelegramError

import psycopg2
from psycopg2 import pool, OperationalError
from psycopg2. extras import RealDictCursor
import aiohttp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os. environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
DATABASE_URL = os. environ.get("DATABASE_URL")
RENDER_EXTERNAL_URL = os.environ. get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

CPALEAD_ID = os.environ. get("CPALEAD_ID", "")
OFFERTORO_ID = os. environ.get("OFFERTORO_ID", "")
POLLFISH_KEY = os.environ. get("POLLFISH_KEY", "")
AYETSTUDIOS_KEY = os.environ.get("AYETSTUDIOS_KEY", "")

UDEMY_AFFILIATE = os.environ.get("UDEMY_AFFILIATE", "griddled")
FIVERR_AFFILIATE = os.environ.get("FIVERR_AFFILIATE", "griddled")

PAYPAL_CLIENT_ID = os. environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET", "")
STRIPE_API_KEY = os. environ.get("STRIPE_API_KEY", "")
BINANCE_API_KEY = os.environ. get("BINANCE_API_KEY", "")

connection_pool = None
application = None
app = Quart(__name__)
http_session = None

COUNTRY_DATA = {
    "US": {
        "name": "USA",
        "flag": "US",
        "max_daily": 180,
        "methods": ["paypal", "stripe", "venmo"],
        "min_withdraw": 5. 0,
        "currency": "USD"
    },
    "MX": {
        "name": "Mexico",
        "flag": "MX",
        "max_daily": 60,
        "methods": ["paypal", "oxxo", "spei"],
        "min_withdraw": 2.0,
        "currency": "MXN"
    },
    "BR": {
        "name": "Brasil",
        "flag": "BR",
        "max_daily": 70,
        "methods": ["pix", "paypal"],
        "min_withdraw": 2.0,
        "currency": "BRL"
    },
    "AR": {
        "name": "Argentina",
        "flag": "AR",
        "max_daily": 50,
        "methods": ["mercadopago", "binance"],
        "min_withdraw": 1.0,
        "currency": "ARS"
    },
    "CO": {
        "name": "Colombia",
        "flag": "CO",
        "max_daily": 50,
        "methods": ["nequi", "daviplata", "bancolombia"],
        "min_withdraw": 2.0,
        "currency": "COP"
    },
    "ES": {
        "name": "Espana",
        "flag": "ES",
        "max_daily": 130,
        "methods": ["paypal", "bizum", "sepa"],
        "min_withdraw": 3.0,
        "currency": "EUR"
    },
    "CN": {
        "name": "China",
        "flag": "CN",
        "max_daily": 80,
        "methods": ["alipay", "wechat", "unionpay", "crypto"],
        "min_withdraw": 100.0,
        "currency": "CNY"
    },
    "RU": {
        "name": "Russia",
        "flag": "RU",
        "max_daily": 60,
        "methods": ["crypto", "yoomoney", "qiwi", "webmoney"],
        "min_withdraw": 500.0,
        "currency": "RUB"
    },
    "KR": {
        "name": "South Korea",
        "flag": "KR",
        "max_daily": 140,
        "methods": ["paypal", "toss", "kakaopay", "naverpay", "crypto"],
        "min_withdraw": 10000.0,
        "currency": "KRW"
    },
    "VE": {
        "name": "Venezuela",
        "flag": "VE",
        "max_daily": 35,
        "methods": ["crypto", "binance", "airtm", "reserve"],
        "min_withdraw": 2.0,
        "currency": "USD"
    },
    "NG": {
        "name": "Nigeria",
        "flag": "NG",
        "max_daily": 50,
        "methods": ["paystack", "flutterwave", "crypto"],
        "min_withdraw": 5000.0,
        "currency": "NGN"
    },
    "AU": {
        "name": "Australia",
        "flag": "AU",
        "max_daily": 180,
        "methods": ["paypal", "stripe", "poli", "bpay", "crypto"],
        "min_withdraw": 10.0,
        "currency": "AUD"
    },
    "IN": {
        "name": "India",
        "flag": "IN",
        "max_daily": 60,
        "methods": ["paypal", "paytm", "phonepe", "upi", "crypto"],
        "min_withdraw": 500.0,
        "currency": "INR"
    },
    "ZA": {
        "name": "South Africa",
        "flag": "ZA",
        "max_daily": 70,
        "methods": ["paypal", "ozow", "snapscan", "crypto"],
        "min_withdraw": 100.0,
        "currency": "ZAR"
    },
    "GLOBAL": {
        "name": "Global",
        "flag": "GLOBAL",
        "max_daily": 80,
        "methods": ["paypal", "binance", "crypto", "payoneer", "wise"],
        "min_withdraw": 2.0,
        "currency": "USD"
    }
}

MARKETPLACE_PLATFORMS = {
    "udemy": {
        "name": "Udemy",
        "url": "https://udemy.com",
        "commission": 15,
        "description": "Cursos de Freelancing Marketing Programacion"
    },
    "coursera": {
        "name": "Coursera",
        "url": "https://coursera.org",
        "commission": 20,
        "description": "Certificaciones profesionales"
    },
    "skillshare": {
        "name": "Skillshare",
        "url": "https://skillshare.com",
        "commission": 25,
        "description": "Diseno Video Creatividad"
    },
    "fiverr": {
        "name": "Fiverr",
        "url": "https://fiverr. com",
        "commission": 30,
        "description": "Vende tus servicios freelance"
    },
    "upwork": {
        "name": "Upwork",
        "url": "https://upwork.com",
        "commission": 10,
        "description": "Consigue clientes a largo plazo"
    }
}

TASK_PLATFORMS = {
    "cpalead": {"name": "CPALead", "api_key": CPALEAD_ID},
    "offertoro": {"name": "OfferToro", "api_key": OFFERTORO_ID},
    "pollfish": {"name": "Pollfish", "api_key": POLLFISH_KEY},
    "ayetstudios": {"name": "AyetStudios", "api_key": AYETSTUDIOS_KEY}
}

def error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TelegramError as e:
            logger.error(f"Telegram error in {func.__name__}: {e}")
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
    return wrapper

def setup_db_pool():
    global connection_pool
    if not DATABASE_URL:
        logger.error("DATABASE_URL no configurada")
        return False
    try:
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url. replace("postgres://", "postgresql://", 1)
        connection_pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=db_url,
            connect_timeout=10
        )
        logger.info("Pool BD configurado correctamente")
        return True
    except OperationalError as e:
        logger. error(f"Error operacional BD: {e}")
        return False
    except Exception as e:
        logger. error(f"Error inesperado pool: {e}")
        return False

def get_db_conn():
    if connection_pool:
        try:
            conn = connection_pool. getconn()
            if conn:
                return conn
        except Exception as e:
            logger.error(f"Error obteniendo conexion: {e}")
    return None

def put_db_conn(conn):
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error devolviendo conexion: {e}")

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
                    country VARCHAR(10) DEFAULT 'GLOBAL',
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
        logger.info("BD inicializada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error inicializando BD: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

def get_or_create_user(user_id, first_name, username, ref_code=None, country_code="GLOBAL"):
    conn = get_db_conn()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur. fetchone()
            
            if not user:
                my_ref_code = hashlib.md5(str(user_id).encode()). hexdigest()[:8]. upper()
                wallet = "0x" + os.urandom(20).hex()
                
                referred_by_id = None
                if ref_code:
                    cur. execute("SELECT id FROM users WHERE referral_code = %s", (ref_code,))
                    referrer = cur.fetchone()
                    if referrer:
                        referred_by_id = referrer["id"]
                
                cur.execute("""
                    INSERT INTO users (id, first_name, username, referral_code, referred_by, wallet_address, country)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (user_id, first_name, username, my_ref_code, referred_by_id, wallet, country_code))
                user = cur.fetchone()
                
                if referred_by_id:
                    cur. execute("""
                        INSERT INTO referrals (referrer_id, referred_id, commission_earned)
                        VALUES (%s, %s, 1.00)
                        ON CONFLICT (referred_id) DO NOTHING
                    """, (referred_by_id, user_id))
                    cur.execute("UPDATE users SET tokens = tokens + 100, total_earned = total_earned + 1.00 WHERE id = %s", (referred_by_id,))
                
                conn.commit()
                logger.info(f"Usuario creado: {user_id} - {first_name}")
            else:
                cur.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
                conn.commit()
            
            return dict(user) if user else None
    except Exception as e:
        logger. error(f"Error get_or_create_user: {e}")
        conn.rollback()
        return None
    finally:
        put_db_conn(conn)

def add_task_earning(user_id, task_id, platform, reward):
    if reward <= 0 or reward > 100:
        logger.warning(f"Reward invalido: {reward}")
        return False
    
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
        logger.info(f"Tarea completada: user={user_id}, reward=${reward:. 2f}")
        return True
    except Exception as e:
        logger.error(f"Error add_task: {e}")
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
            f"https://api.{platform_name}.com/offers",
            params={"api_key": platform["api_key"]},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("offers", [])[:5]
    except aiohttp.ClientError as e:
        logger.error(f"Error HTTP fetching {platform_name}: {e}")
    except Exception as e:
        logger.error(f"Error inesperado fetching {platform_name}: {e}")
    return []

@error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_code = context. args[0] if context.args else None
    
    user_data = get_or_create_user(user.id, user. first_name, user.username or "user", ref_code)
    
    if not user_data:
        await update.message.reply_text("Error al inicializar.  Usa /start de nuevo")
        return
    
    country_config = COUNTRY_DATA.get(user_data["country"], COUNTRY_DATA["GLOBAL"])
    
    welcome_msg = (
        f"BIENVENIDO A GRIDDLED V3\n\n"
        f"Hola {user. first_name}\n\n"
        f"Tu pais: {country_config['name']}\n"
        f"Potencial diario: ${country_config['max_daily']}\n"
        f"Tokens: {user_data['tokens']}\n"
        f"Plan: {user_data['subscription']}\n\n"
        f"Metodos de pago:\n"
    )
    
    for method in country_config["methods"][:3]:
        welcome_msg += f"- {method. upper()}\n"
    
    welcome_msg += "\nEmpieza ahora:"
    
    keyboard = [
        ["Ver Tareas", "Dashboard"],
        ["Marketplace", "Referir"],
        ["Config Pagos", "Stats"]
    ]
    
    await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

@error_handler
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cargando tareas disponibles...")
    
    tasks = []
    task_id = 1
    
    for platform_name in ["cpalead", "offertoro", "pollfish"]:
        live_tasks = await fetch_live_tasks(platform_name)
        for task in live_tasks[:3]:
            tasks.append({
                "id": task_id,
                "title": task.get("name", f"Tarea {task_id}"),
                "reward": float(task.get("payout", 0. 25)),
                "platform": platform_name,
                "task_id": task. get("id", str(task_id))
            })
            task_id += 1
    
    if not tasks:
        tasks = [
            {"id": 1, "title": "Encuesta 2min", "reward": 0.25, "platform": "pollfish", "task_id": "demo_1"},
            {"id": 2, "title": "Instalar App", "reward": 0.80, "platform": "cpalead", "task_id": "demo_2"},
            {"id": 3, "title": "Ver Video 30s", "reward": 0.10, "platform": "generic", "task_id": "demo_3"},
            {"id": 4, "title": "Review", "reward": 0.35, "platform": "generic", "task_id": "demo_4"},
            {"id": 5, "title": "Validar Dato", "reward": 0.15, "platform": "generic", "task_id": "demo_5"},
            {"id": 6, "title": "Etiquetar Foto", "reward": 0.08, "platform": "generic", "task_id": "demo_6"},
            {"id": 7, "title": "Red Social", "reward": 0.40, "platform": "generic", "task_id": "demo_7"},
            {"id": 8, "title": "Research", "reward": 0.60, "platform": "generic", "task_id": "demo_8"}
        ]
    
    tasks_msg = "TAREAS DISPONIBLES\n\n"
    for task in tasks:
        tasks_msg += f"{task['id']}. {task['title']}\n   ${task['reward']:. 2f}\n\n"
    tasks_msg += f"Escribe el numero (1-{len(tasks)})"
    
    context. user_data["tasks"] = tasks
    await update.message.reply_text(tasks_msg)

@error_handler
async def handle_task_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message. text
    if not text.isdigit():
        return
    
    task_num = int(text)
    tasks = context.user_data.get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        return
    
    task = tasks[task_num - 1]
    
    msg = (
        f"Tarea: {task['title']}\n\n"
        f"Ganaras: ${task['reward']:. 2f}\n"
        f"Bonus: +10 tokens\n\n"
        f"Pasos:\n"
        f"1.  Abre el link\n"
        f"2. Completa la tarea\n"
        f"3. Presiona Complete"
    )
    
    keyboard = [
        [InlineKeyboardButton("Abrir Tarea", url="https://example.com/task")],
        [InlineKeyboardButton("Complete", callback_data=f"done_{task_num}")],
        [InlineKeyboardButton("Cancelar", callback_data="cancel")]
    ]
    
    await update. message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

@error_handler
async def task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("done_"):
        return
    
    task_num = int(query.data. split("_")[1])
    tasks = context.user_data.get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        await query.edit_message_text("Tarea no valida")
        return
    
    task = tasks[task_num - 1]
    user_id = query.from_user. id
    
    success = add_task_earning(user_id, task["task_id"], task["platform"], task["reward"])
    
    if success:
        msg = (
            f"TAREA COMPLETADA\n\n"
            f"+${task['reward']:. 2f}\n"
            f"+10 tokens\n\n"
            f"Usa /dashboard para ver tu progreso"
        )
        await query.edit_message_text(msg)
    else:
        await query.edit_message_text("Error procesando.  Intenta de nuevo")

@error_handler
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if not conn:
        await update.message. reply_text("Error de conexion")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            
            if not user_data:
                await update.message.reply_text("Usuario no encontrado")
                return
            
            cur.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = %s", (user_id,))
            refs_count = cur.fetchone()["count"]
            
            country_config = COUNTRY_DATA.get(user_data["country"], COUNTRY_DATA["GLOBAL"])
            
            msg = (
                f"TU DASHBOARD\n\n"
                f"{country_config['name']}\n"
                f"Plan: {user_data['subscription']}\n"
                f"Tokens: {user_data['tokens']}\n\n"
                f"FINANZAS:\n"
                f"Total ganado: ${user_data['total_earned']:.2f}\n"
                f"Pendiente: ${user_data['pending_payout']:.2f}\n"
                f"Retirado: ${user_data['total_withdrawn']:.2f}\n"
                f"Minimo retiro: ${country_config['min_withdraw']:.2f}\n\n"
                f"Tareas: {user_data['tasks_completed']}\n"
                f"Referidos: {refs_count}\n\n"
                f"Wallet: {user_data['wallet_address']}\n"
                f"Codigo: {user_data['referral_code']}"
            )
            
            keyboard = [
                [InlineKeyboardButton("Ver Tareas", callback_data="show_tasks")],
                [InlineKeyboardButton("Retirar", callback_data="withdraw")],
                [InlineKeyboardButton("Referir", callback_data="refer")]
            ]
            
            await update. message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        put_db_conn(conn)

@error_handler
async def marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "MARKETPLACE\n\nCursos y servicios con comision:\n\n"
    
    keyboard = []
    for key, platform in MARKETPLACE_PLATFORMS.items():
        msg += f"{platform['name']}\nComision: {platform['commission']}%\n{platform['description']}\n\n"
        url = f"{platform['url']}?ref={UDEMY_AFFILIATE if key == 'udemy' else FIVERR_AFFILIATE}"
        keyboard. append([InlineKeyboardButton(platform["name"], url=url)])
    
    await update.message. reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

@error_handler
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update. effective_user.id
    conn = get_db_conn()
    
    if not conn:
        await update.message. reply_text("Error")
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
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"
    
    msg = (
        f"PROGRAMA DE REFERIDOS\n\n"
        f"Tu codigo: {ref_code}\n"
        f"Tu link: {ref_link}\n\n"
        f"ESTADISTICAS:\n"
        f"Referidos: {ref_stats['count']}\n"
        f"Comisiones: ${ref_stats['total']:.2f}\n\n"
        f"GANANCIAS:\n"
        f"$1.00 por registro\n"
        f"15% de por vida\n\n"
        f"5 amigos = $7.50/dia"
    )
    
    keyboard = [
        [InlineKeyboardButton("WhatsApp", url=f"https://wa.me/? text={ref_link}")],
        [InlineKeyboardButton("Telegram", url=f"https://t.me/share/url?url={ref_link}")]
    ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

@error_handler
async def config_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user.id, "User", "user")
    country_config = COUNTRY_DATA.get(user_data["country"], COUNTRY_DATA["GLOBAL"])
    
    msg = f"CONFIGURAR PAGO\n\nMetodos para {country_config['name']}:\n\n"
    
    keyboard = []
    for method in country_config["methods"]:
        keyboard.append([InlineKeyboardButton(f"{method. upper()}", callback_data=f"pay_{method}")])
    
    await update.message. reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

@error_handler
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_conn()
    if not conn:
        await update.message. reply_text("Error")
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
        f"ESTADISTICAS GLOBALES\n\n"
        f"Usuarios activos: {active_users:,}\n"
        f"Total pagado: ${total_paid:,.2f}\n"
        f"Tareas completadas: {total_tasks:,}\n\n"
        f"Pais TOP: Brasil\n"
        f"Racha: 127 dias"
    )
    
    await update. message.reply_text(msg)

@error_handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_tasks":
        update._message = query.message
        await show_tasks(update, context)
    elif query.data == "withdraw":
        await query.edit_message_text("Configura tu metodo de pago primero usando Config Pagos")
    elif query.data == "refer":
        update._effective_user = query. from_user
        update._message = query. message
        await refer(update, context)
    elif query. data. startswith("pay_"):
        method = query.data. split("_")[1]
        await query.edit_message_text(f"Configurando {method.upper()}\n\nEnvia tu email/ID:")
    elif query. data == "cancel":
        await query.edit_message_text("Cancelado")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    try:
        data = await request.get_json()
        update = Update. de_json(data, application. bot)
        await application.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Error webhook: {e}")
        return "error", 500

@app.route("/health")
async def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

@app.route("/")
async def index():
    return jsonify({"name": "GRIDDLED V3", "version": "3.0", "status": "active"}), 200

@app.before_serving
async def startup():
    global application, http_session
    
    logger.info("Iniciando GRIDDLED V3...")
    
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no configurado")
    
    if not init_db():
        raise RuntimeError("Error BD")
    
    http_session = aiohttp.ClientSession()
    application = Application. builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application. add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("tareas", show_tasks))
    application. add_handler(CommandHandler("marketplace", marketplace))
    application.add_handler(CommandHandler("referir", refer))
    application.add_handler(CommandHandler("configurar", config_payments))
    application.add_handler(CommandHandler("stats", stats))
    
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^Ver Tareas$"), show_tasks))
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^Dashboard$"), dashboard))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^Marketplace$"), marketplace))
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^Referir$"), refer))
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^Config Pagos$"), config_payments))
    application. add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^Stats$"), stats))
    
    application.add_handler(MessageHandler(filters. TEXT & filters. Regex(r"^\d+$"), handle_task_num))
    
    application.add_handler(CallbackQueryHandler(task_done, pattern=r"^done_"))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    await application.start()
    
    logger.info("Bot iniciado correctamente")

@app.after_serving
async def shutdown():
    global application, http_session, connection_pool
    
    logger.info("Cerrando bot...")
    
    if http_session:
        await http_session. close()
    if application:
        await application.stop()
        await application.shutdown()
    if connection_pool:
        connection_pool.closeall()
    
    logger.info("Bot cerrado correctamente")

if __name__ == "__main__":
    app.run(host="0.0. 0.0", port=PORT)
