import os
import logging
import hashlib
from datetime import datetime

from quart import Quart, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import aiohttp

# Importar configuración de países
from config import COUNTRIES, get_country_config, get_payment_methods

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

connection_pool = None
application = None
app = Quart(__name__)
http_session = None

def setup_db_pool():
    global connection_pool
    if not DATABASE_URL:
        logger. error("DATABASE_URL no configurada")
        return False
    try:
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
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
        except Exception as e:
            logger.error(f"Error conexion: {e}")
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
        logger.info("BD inicializada")
        return True
    except Exception as e:
        logger.error(f"Error BD: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

async def detect_country_from_user(user_id):
    """Detecta el país del usuario usando API de geolocalización"""
    try:
        # Intentar detectar por IP usando ipapi.co (gratis)
        async with http_session.get(f"https://ipapi.co/json/") as response:
            if response.status == 200:
                data = await response.json()
                country_code = data.get("country_code", "GLOBAL")
                return country_code
    except Exception as e:
        logger.error(f"Error detectando país: {e}")
    
    return "GLOBAL"

def get_or_create_user(user_id, first_name, username, ref_code=None, country_code=None):
    conn = get_db_conn()
    if not conn:
        return None
    try:
        with conn. cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
            if not user:
                my_ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]. upper()
                wallet = "0x" + os.urandom(20).hex()
                
                # Usar país detectado o GLOBAL
                final_country = country_code if country_code else "GLOBAL"
                
                referred_by_id = None
                if ref_code:
                    cur.execute("SELECT id FROM users WHERE referral_code = %s", (ref_code,))
                    referrer = cur.fetchone()
                    if referrer:
                        referred_by_id = referrer["id"]
                
                cur. execute("""
                    INSERT INTO users (id, first_name, username, referral_code, referred_by, wallet_address, country)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (user_id, first_name, username, my_ref_code, referred_by_id, wallet, final_country))
                user = cur.fetchone()
                
                if referred_by_id:
                    cur.execute("""
                        INSERT INTO referrals (referrer_id, referred_id, commission_earned)
                        VALUES (%s, %s, 1. 00)
                    """, (referred_by_id, user_id))
                    cur.execute("UPDATE users SET tokens = tokens + 100, total_earned = total_earned + 1.00 WHERE id = %s", (referred_by_id,))
                
                conn.commit()
                logger.info(f"Usuario creado: {user_id} - País: {final_country}")
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
        logger. info(f"Tarea completada: user={user_id}, reward=${reward}")
        return True
    except Exception as e:
        logger.error(f"Error add_task: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_code = context.args[0] if context. args else None
    
    # Detectar país del usuario
    country_code = await detect_country_from_user(user.id)
    
    user_data = get_or_create_user(user.id, user.first_name, user.username or "user", ref_code, country_code)
    
    if not user_data:
        await update.message.reply_text("Error al inicializar.  Usa /start de nuevo")
        return
    
    # Obtener configuración del país
    country_config = get_country_config(user_data["country"])
    
    welcome_msg = (
        f"BIENVENIDO A GRIDDLED V3\n\n"
        f"Hola {user.first_name}\n\n"
        f"Tu pais: {country_config['name']}\n"
        f"Potencial diario: {country_config['currency_symbol']}{country_config['max_daily']}\n"
        f"Tokens: {user_data['tokens']}\n"
        f"Plan: {user_data['subscription']}\n\n"
        f"Metodos de pago disponibles:\n"
    )
    
    # Listar métodos de pago del país
    for method in country_config["methods"][:3]:
        welcome_msg += f"- {method. upper()}\n"
    
    welcome_msg += "\nEmpieza ahora:"
    
    keyboard = [
        ["Ver Tareas", "Dashboard"],
        ["Metodos Pago", "Referir"],
        ["Cambiar Pais", "Stats"]
    ]
    
    await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user.id, "User", "user")
    country_config = get_country_config(user_data["country"])
    
    tasks = [
        {"id": 1, "title": "Encuesta 2min", "reward": 0.25, "platform": "pollfish", "task_id": "demo_1"},
        {"id": 2, "title": "Instalar App", "reward": 0.80, "platform": "cpalead", "task_id": "demo_2"},
        {"id": 3, "title": "Ver Video 30s", "reward": 0. 10, "platform": "generic", "task_id": "demo_3"},
        {"id": 4, "title": "Review", "reward": 0.35, "platform": "generic", "task_id": "demo_4"},
        {"id": 5, "title": "Validar Dato", "reward": 0.15, "platform": "generic", "task_id": "demo_5"},
    ]
    
    tasks_msg = f"TAREAS DISPONIBLES ({country_config['name']})\n\n"
    for task in tasks:
        tasks_msg += f"{task['id']}. {task['title']}\n   {country_config['currency_symbol']}{task['reward']:.2f}\n\n"
    tasks_msg += f"Escribe el numero (1-{len(tasks)})"
    
    context.user_data["tasks"] = tasks
    await update.message.reply_text(tasks_msg)

async def handle_task_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        return
    
    task_num = int(text)
    tasks = context.user_data. get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        return
    
    task = tasks[task_num - 1]
    user_data = get_or_create_user(update.effective_user.id, "User", "user")
    country_config = get_country_config(user_data["country"])
    
    msg = (
        f"Tarea: {task['title']}\n\n"
        f"Ganaras: {country_config['currency_symbol']}{task['reward']:.2f}\n"
        f"Bonus: +10 tokens\n\n"
        f"Pasos:\n"
        f"1. Abre el link\n"
        f"2.  Completa la tarea\n"
        f"3. Presiona Complete"
    )
    
    keyboard = [
        [InlineKeyboardButton("Abrir Tarea", url="https://example.com/task")],
        [InlineKeyboardButton("Complete", callback_data=f"done_{task_num}")],
        [InlineKeyboardButton("Cancelar", callback_data="cancel")]
    ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("done_"):
        return
    
    task_num = int(query.data.split("_")[1])
    tasks = context.user_data.get("tasks", [])
    
    if task_num < 1 or task_num > len(tasks):
        await query.edit_message_text("Tarea no valida")
        return
    
    task = tasks[task_num - 1]
    user_id = query.from_user.id
    
    success = add_task_earning(user_id, task["task_id"], task["platform"], task["reward"])
    
    if success:
        user_data = get_or_create_user(user_id, "User", "user")
        country_config = get_country_config(user_data["country"])
        
        msg = (
            f"TAREA COMPLETADA\n\n"
            f"+{country_config['currency_symbol']}{task['reward']:.2f}\n"
            f"+10 tokens\n\n"
            f"Usa /dashboard para ver tu progreso"
        )
        await query.edit_message_text(msg)
    else:
        await query.edit_message_text("Error procesando.  Intenta de nuevo")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if not conn:
        await update.message.reply_text("Error de conexion")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            
            if not user_data:
                await update.message. reply_text("Usuario no encontrado")
                return
            
            cur.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = %s", (user_id,))
            refs_count = cur.fetchone()["count"]
            
            country_config = get_country_config(user_data["country"])
            
            msg = (
                f"TU DASHBOARD\n\n"
                f"{country_config['name']}\n"
                f"Plan: {user_data['subscription']}\n"
                f"Tokens: {user_data['tokens']}\n\n"
                f"FINANZAS:\n"
                f"Total ganado: {country_config['currency_symbol']}{user_data['total_earned']:.2f}\n"
                f"Pendiente: {country_config['currency_symbol']}{user_data['pending_payout']:.2f}\n"
                f"Retirado: {country_config['currency_symbol']}{user_data['total_withdrawn']:.2f}\n"
                f"Minimo retiro: {country_config['currency_symbol']}{country_config['min_withdraw']}\n\n"
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
            
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        put_db_conn(conn)

async def show_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_or_create_user(update.effective_user.id, "User", "user")
    country_config = get_country_config(user_data["country"])
    
    msg = f"METODOS DE PAGO ({country_config['name']})\n\n"
    
    keyboard = []
    for method in country_config["methods"]:
        msg += f"- {method.upper()}\n"
        keyboard.append([InlineKeyboardButton(f"{method.upper()}", callback_data=f"pay_{method}")])
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def change_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite al usuario cambiar su país manualmente"""
    msg = "CAMBIAR PAIS\n\nEscribe el codigo de tu pais (ej: US, MX, BR, ES, etc.)\n\nPaises populares:\nUS - USA\nMX - Mexico\nBR - Brasil\nAR - Argentina\nCO - Colombia\nES - Espana\nCN - China\nRU - Russia\nIN - India"
    
    context.user_data["awaiting_country"] = True
    await update.message.reply_text(msg)

async def handle_country_change(update: Update, context: ContextTypes. DEFAULT_TYPE):
    """Procesa el cambio de país"""
    if not context.user_data.get("awaiting_country"):
        return
    
    country_code = update.message.text.upper(). strip()
    
    if country_code not in COUNTRIES:
        await update.message. reply_text(f"Pais '{country_code}' no encontrado.  Intenta de nuevo o usa GLOBAL")
        return
    
    conn = get_db_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET country = %s WHERE id = %s", (country_code, update.effective_user.id))
            conn.commit()
            
            country_config = get_country_config(country_code)
            await update.message.reply_text(
                f"Pais actualizado a: {country_config['name']}\n"
                f"Potencial diario: {country_config['currency_symbol']}{country_config['max_daily']}\n\n"
                f"Usa /start para ver los cambios"
            )
        finally:
            put_db_conn(conn)
    
    context.user_data["awaiting_country"] = False

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if not conn:
        await update.message.reply_text("Error")
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT referral_code, country FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            ref_code = user_data["referral_code"]
            
            cur.execute("SELECT COUNT(*) as count, COALESCE(SUM(commission_earned), 0) as total FROM referrals WHERE referrer_id = %s", (user_id,))
            ref_stats = cur.fetchone()
    finally:
        put_db_conn(conn)
    
    bot_username = context.bot. username
    ref_link = f"https://t.me/{bot_username}? start={ref_code}"
    
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

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("Error")
        return
    
    try:
        with conn. cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
            active_users = cur.fetchone()["count"]
            
            cur.execute("SELECT COALESCE(SUM(total_earned), 0) as total FROM users")
            total_paid = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as count FROM tasks_completed WHERE status = 'completed'")
            total_tasks = cur.fetchone()["count"]
            
            cur.execute("SELECT country, COUNT(*) as count FROM users GROUP BY country ORDER BY count DESC LIMIT 5")
            top_countries = cur.fetchall()
    finally:
        put_db_conn(conn)
    
    msg = (
        f"ESTADISTICAS GLOBALES\n\n"
        f"Usuarios activos: {active_users:,}\n"
        f"Total pagado: ${total_paid:,.2f}\n"
        f"Tareas completadas: {total_tasks:,}\n\n"
        f"TOP 5 PAISES:\n"
    )
    
    for i, country_data in enumerate(top_countries, 1):
        country_config = get_country_config(country_data["country"])
        msg += f"{i}. {country_config['name']}: {country_data['count']} usuarios\n"
    
    await update.message.reply_text(msg)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_tasks":
        update._message = query.message
        await show_tasks(update, context)
    elif query.data == "withdraw":
        await query.edit_message_text("Configura tu metodo de pago primero usando: Metodos Pago")
    elif query.data == "refer":
        update._effective_user = query.from_user
        update._message = query.message
        await refer(update, context)
    elif query.data.startswith("pay_"):
        method = query.data.split("_")[1]
        await query. edit_message_text(f"Configurando {method.upper()}\n\nEnvia tu email/ID:")
    elif query.data == "cancel":
        await query.edit_message_text("Cancelado")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, application. bot)
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
    return jsonify({"name": "GRIDDLED V3", "version": "3.0", "countries": len(COUNTRIES)}), 200

@app.before_serving
async def startup():
    global application, http_session
    
    logger.info("Iniciando GRIDDLED V3...")
    
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no configurado")
    
    if not init_db():
        raise RuntimeError("Error BD")
    
    http_session = aiohttp.ClientSession()
    application = Application. builder().token(TELEGRAM_TOKEN). build()
    
    application.add_handler(CommandHandler("start", start))
    application. add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("tareas", show_tasks))
    application.add_handler(Comman
