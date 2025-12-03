import os
import logging
import hashlib
from datetime import datetime

from quart import Quart, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import psycopg2
from psycopg2 import pool
from psycopg2. extras import RealDictCursor

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os. environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

connection_pool = None
application = None
app = Quart(__name__)

COUNTRY_DATA = {
    "US": {"name": "USA", "max_daily": 180, "min_withdraw": 5. 0},
    "MX": {"name": "Mexico", "max_daily": 60, "min_withdraw": 2.0},
    "BR": {"name": "Brasil", "max_daily": 70, "min_withdraw": 2.0},
    "Global": {"name": "Global", "max_daily": 80, "min_withdraw": 2.0}
}

def setup_db_pool():
    global connection_pool
    if not DATABASE_URL:
        return False
    try:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
        connection_pool = pool.ThreadedConnectionPool(minconn=2, maxconn=20, dsn=db_url)
        logger.info("Pool BD configurado")
        return True
    except Exception as e:
        logger.error(f"Error pool: {e}")
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
                    pending_payout DECIMAL(12,2) DEFAULT 0,
                    tasks_completed INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tasks_completed (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    task_id VARCHAR(100),
                    platform VARCHAR(50),
                    reward DECIMAL(10,2),
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT REFERENCES users(id),
                    referred_id BIGINT REFERENCES users(id) UNIQUE,
                    commission DECIMAL(10,2) DEFAULT 1.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        logger. info("BD inicializada")
        return True
    except Exception as e:
        logger.error(f"Error BD: {e}")
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
                my_ref = hashlib.md5(str(user_id).encode()).hexdigest()[:8]. upper()
                cur.execute("""
                    INSERT INTO users (id, first_name, username, referral_code)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                """, (user_id, first_name, username, my_ref))
                user = cur.fetchone()
                
                if ref_code:
                    cur. execute("SELECT id FROM users WHERE referral_code = %s", (ref_code,))
                    referrer = cur.fetchone()
                    if referrer:
                        cur.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (referrer["id"], user_id))
                        cur.execute("UPDATE users SET tokens = tokens + 100, total_earned = total_earned + 1. 00 WHERE id = %s", (referrer["id"],))
                
                conn.commit()
            
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error user: {e}")
        return None
    finally:
        put_db_conn(conn)

def add_task(user_id, task_id, platform, reward):
    conn = get_db_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks_completed (user_id, task_id, platform, reward) VALUES (%s, %s, %s, %s)", (user_id, task_id, platform, reward))
            cur.execute("UPDATE users SET total_earned = total_earned + %s, pending_payout = pending_payout + %s, tokens = tokens + 10, tasks_completed = tasks_completed + 1 WHERE id = %s", (reward, reward, user_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error task: {e}")
        return False
    finally:
        put_db_conn(conn)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = context.args[0] if context. args else None
    user_data = get_or_create_user(user.id, user.first_name, user.username or "user", ref)
    
    if not user_data:
        await update.message.reply_text("Error.  Intenta /start")
        return
    
    msg = f"Bienvenido {user. first_name} a GRIDDLED V3\n\nTokens: {user_data['tokens']}\nGanado: ${user_data['total_earned']:. 2f}\nCodigo: {user_data['referral_code']}"
    keyboard = [["Ver Tareas", "Dashboard"], ["Referir", "Stats"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = [
        {"id": 1, "title": "Encuesta 2min", "reward": 0.25, "platform": "pollfish", "task_id": "demo1"},
        {"id": 2, "title": "Instalar App", "reward": 0.80, "platform": "cpalead", "task_id": "demo2"},
        {"id": 3, "title": "Ver Video", "reward": 0.10, "platform": "generic", "task_id": "demo3"},
        {"id": 4, "title": "Review", "reward": 0.35, "platform": "generic", "task_id": "demo4"},
        {"id": 5, "title": "Validar Dato", "reward": 0.15, "platform": "generic", "task_id": "demo5"}
    ]
    
    msg = "TAREAS DISPONIBLES\n\n"
    for t in tasks:
        msg += f"{t['id']}. {t['title']} - ${t['reward']:.2f}\n"
    msg += "\nEscribe el numero (1-5)"
    
    context.user_data["tasks"] = tasks
    await update.message.reply_text(msg)

async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text. isdigit():
        return
    
    num = int(text)
    tasks = context.user_data.get("tasks", [])
    if num < 1 or num > len(tasks):
        return
    
    task = tasks[num - 1]
    msg = f"Tarea: {task['title']}\nGanaras: ${task['reward']:.2f}\n+10 tokens\n\n1. Abre el link\n2. Completa\n3. Presiona OK"
    
    keyboard = [
        [InlineKeyboardButton("Abrir", url="https://example.com")],
        [InlineKeyboardButton("Complete", callback_data=f"done_{num}")]
    ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("done_"):
        return
    
    num = int(query.data.split("_")[1])
    tasks = context.user_data.get("tasks", [])
    if num < 1 or num > len(tasks):
        await query.edit_message_text("Tarea invalida")
        return
    
    task = tasks[num - 1]
    success = add_task(query.from_user.id, task["task_id"], task["platform"], task["reward"])
    
    if success:
        await query.edit_message_text(f"Completada!\n+${task['reward']:.2f}\n+10 tokens\n\nUsa /dashboard")
    else:
        await query.edit_message_text("Error.  Intenta de nuevo")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("Error")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (update.effective_user.id,))
            user = cur.fetchone()
            
            if not user:
                await update.message. reply_text("Usuario no encontrado")
                return
            
            cur.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = %s", (user["id"],))
            refs = cur.fetchone()["count"]
            
            msg = f"TU DASHBOARD\n\nTokens: {user['tokens']}\nTotal: ${user['total_earned']:.2f}\nPendiente: ${user['pending_payout']:.2f}\nTareas: {user['tasks_completed']}\nReferidos: {refs}\n\nCodigo: {user['referral_code']}"
            await update.message. reply_text(msg)
    finally:
        put_db_conn(conn)

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user.id, "User", "user")
    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start={user_data['referral_code']}"
    
    msg = f"REFERIDOS\n\nTu codigo: {user_data['referral_code']}\nLink: {link}\n\n$1 por registro\n15% de por vida"
    
    keyboard = [
        [InlineKeyboardButton("WhatsApp", url=f"https://wa.me/? text={link}")],
        [InlineKeyboardButton("Telegram", url=f"https://t.me/share/url?url={link}")]
    ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_conn()
    if not conn:
        await update. message.reply_text("Error")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as count FROM users")
            users = cur.fetchone()["count"]
            
            cur.execute("SELECT COALESCE(SUM(total_earned), 0) as total FROM users")
            earned = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as count FROM tasks_completed")
            tasks = cur.fetchone()["count"]
            
            msg = f"ESTADISTICAS GLOBALES\n\nUsuarios: {users:,}\nPagado: ${earned:,.2f}\nTareas: {tasks:,}"
            await update.message.reply_text(msg)
    finally:
        put_db_conn(conn)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, application. bot)
        await application.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "error", 500

@app.route("/health")
async def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200

@app.route("/")
async def index():
    return jsonify({"name": "GRIDDLED V3", "version": "3.0"}), 200

@app.before_serving
async def startup():
    global application
    
    logger.info("Iniciando bot...")
    
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no configurado")
    
    if not init_db():
        raise RuntimeError("Error BD")
    
    application = Application.builder().token(TELEGRAM_TOKEN). build()
    
    application.add_handler(CommandHandler("start", start))
    application. add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("tareas", show_tasks))
    application.add_handler(CommandHandler("referir", refer))
    application. add_handler(CommandHandler("stats", stats))
    
    application.add_handler(MessageHandler(filters.TEXT & filters. Regex(r"^Ver Tareas$"), show_tasks))
    application.add_handler(MessageHandler(filters. TEXT & filters.Regex(r"^Dashboard$"), dashboard))
    application. add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^Referir$"), refer))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^Stats$"), stats))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), handle_task))
    
    application.add_handler(CallbackQueryHandler(task_done, pattern=r"^done_"))
    
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application. bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    await application.start()
    
    logger.info("Bot iniciado")

@app.after_serving
async def shutdown():
    global application, connection_pool
    
    if application:
        await application.stop()
        await application.shutdown()
    
    if connection_pool:
        connection_pool.closeall()
    
    logger. info("Bot cerrado")

if __name__ == "__main__":
    app. run(host="0.0.0.0", port=PORT)
