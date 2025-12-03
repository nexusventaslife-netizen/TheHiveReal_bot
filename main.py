import os
import logging
import hashlib
from http import HTTPStatus
from datetime import datetime

from quart import Quart, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram. constants import ParseMode

import psycopg2
from psycopg2 import pool
import aiohttp

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ. get("TELEGRAM_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ. get("PORT", 10000))

connection_pool = None
application = None
app = Quart(__name__)
http_session = None

COUNTRY_DATA = {
    "US": {
        "name": "USA",
        "max_daily": 180,
        "methods": ["paypal", "stripe"],
        "min_withdraw": 5.0
    },
    "MX": {
        "name": "Mexico",
        "max_daily": 60,
        "methods": ["paypal", "oxxo"],
        "min_withdraw": 2.0
    },
    "BR": {
        "name": "Brasil",
        "max_daily": 70,
        "methods": ["pix", "paypal"],
        "min_withdraw": 2.0
    },
    "Global": {
        "name": "Global",
        "max_daily": 80,
        "methods": ["paypal", "binance"],
        "min_withdraw": 2.0
    }
}

def setup_db_pool():
    global connection_pool
    if not DATABASE_URL:
        return False
    try:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
        connection_pool = pool.SimpleConnectionPool(minconn=1, maxconn=20, dsn=db_url)
        logger.info("Pool BD OK")
        return True
    except Exception as e:
        logger. error(f"Error pool: {e}")
        return False

def get_db_conn():
    if connection_pool:
        try:
            return connection_pool. getconn()
        except:
            pass
    return None

def put_db_conn(conn):
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except:
            pass

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
                    tokens INT DEFAULT 100,
                    referral_code VARCHAR(20) UNIQUE,
                    total_earned DECIMAL(12,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tasks_completed (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    platform VARCHAR(50),
                    reward DECIMAL(10,2),
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        logger. info("BD OK")
        return True
    except Exception as e:
        logger.error(f"Error BD: {e}")
        return False
    finally:
        put_db_conn(conn)

def get_or_create_user(user_id, first_name, username):
    conn = get_db_conn()
    if not conn:
        return None
    try:
        with conn. cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]. upper()
                cur.execute("""
                    INSERT INTO users (id, first_name, username, referral_code)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, first_name, username, country, tokens, referral_code, total_earned
                """, (user_id, first_name, username, ref_code))
                user = cur.fetchone()
                conn.commit()
        return user
    except Exception as e:
        logger.error(f"Error user: {e}")
        return None
    finally:
        put_db_conn(conn)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_or_create_user(user.id, user.first_name, user.username or "user")
    if not user_data:
        await update.message. reply_text("Error.  Intenta /start de nuevo")
        return
    msg = f"Bienvenido {user. first_name} a GRIDDLED V3\n\nTokens: {user_data[4]}\nGanado: ${user_data[6]}"
    keyboard = [["Ver Tareas", "Dashboard"], ["Stats", "Ayuda"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "TAREAS DISPONIBLES\n\n1. Encuesta - $0.25\n2. Instalar App - $0.80\n3. Ver Video - $0.10\n\nEscribe el numero"
    await update.message.reply_text(msg)

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user. id, "User", "user")
    if user_data:
        msg = f"DASHBOARD\n\nTokens: {user_data[4]}\nGanado: ${user_data[6]}\nCodigo: {user_data[5]}"
        await update.message.reply_text(msg)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("STATS\n\nUsuarios: 50,000+\nPagado: $1. 2M")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, application. bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return "ok", 200

@app.route("/health")
async def health():
    return {"status": "ok"}, 200

@app.route("/")
async def index():
    return {"status": "GRIDDLED V3", "version": "3.0"}, 200

@app.before_serving
async def startup():
    global application, http_session
    logger.info("Starting bot...")
    if not init_db():
        raise RuntimeError("DB failed")
    http_session = aiohttp.ClientSession()
    application = Application.builder().token(TELEGRAM_TOKEN). build()
    application.add_handler(CommandHandler("start", start))
    application. add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^Ver Tareas$"), show_tasks))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^Dashboard$"), dashboard))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^Stats$"), stats))
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    await application.start()
    logger. info("Bot ON")

@app.after_serving
async def shutdown():
    global application, http_session, connection_pool
    if http_session:
        await http_session.close()
    if application:
        await application.stop()
        await application.shutdown()
    if connection_pool:
        connection_pool.closeall()

if __name__ == "__main__":
    app.run(host="0.0. 0.0", port=PORT)
