import os
import logging
import asyncio
import json
import hashlib
from http import HTTPStatus
from datetime import datetime
from urllib.parse import urlparse

from quart import Quart, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

import psycopg2
from psycopg2.pool import SimpleConnectionPool
import aiohttp
import pytz

# === LOGGING ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === CONFIGURACIÓN ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
DATABASE_URL = os.environ.get('DATABASE_URL', "")
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
PORT = int(os.environ.get('PORT', 10000))

# === INSTANCIAS GLOBALES ===
connection_pool = None
application = None
app = Quart(__name__)
http_session = None

# === DATOS DE PAÍSES (SIMPLIFICADO) ===
COUNTRY_DATA = {
    'US': {'name': '🇺🇸 USA', 'min_wage': 18, 'max_daily': 180, 'currency': 'USD', 
           'methods': ['paypal', 'stripe', 'cashapp'], 'min_withdraw': 5.0},
    'MX': {'name': '🇲🇽 Mexico', 'min_wage': 6, 'max_daily': 60, 'currency': 'MXN',
           'methods': ['paypal', 'mercadopago', 'oxxo'], 'min_withdraw': 2.0},
    'BR': {'name': '🇧🇷 Brasil', 'min_wage': 7, 'max_daily': 70, 'currency': 'BRL',
           'methods': ['pix', 'paypal', 'mercadopago'], 'min_withdraw': 2.0},
    'AR': {'name': '🇦🇷 Argentina', 'min_wage': 5, 'max_daily': 50, 'currency': 'ARS',
           'methods': ['mercadopago', 'binance', 'airtm'], 'min_withdraw': 1.0},
    'CO': {'name': '🇨🇴 Colombia', 'min_wage': 5, 'max_daily': 50, 'currency': 'COP',
           'methods': ['nequi', 'daviplata', 'bancolombia'], 'min_withdraw': 2.0},
    'Global': {'name': '🌍 Global', 'min_wage': 8, 'max_daily': 80, 'currency': 'USD',
               'methods': ['paypal', 'binance', 'airtm'], 'min_withdraw': 2.0}
}

# === PLANES ===
PLANS = {
    'FREE': {'name': 'FREE 🆓', 'boost': 1.0, 'daily_tasks': 20},
    'PRO': {'name': 'PRO 💎', 'boost': 1.5, 'daily_tasks': 80},
    'ELITE': {'name': 'ELITE 👑', 'boost': 2.0, 'daily_tasks': 150}
}

# === BASE DE DATOS ===

def setup_db_pool():
    """Configura pool de BD."""
    global connection_pool
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL no configurada")
        return False
    try:
        url = urlparse(DATABASE_URL)
        conn_str = DATABASE_URL.replace('postgres://', 'postgresql://', 1) if url.scheme == 'postgres' else DATABASE_URL
        connection_pool = SimpleConnectionPool(1, 20, conn_str)
        logger.info("✅ Pool BD configurado")
        return True
    except Exception as e:
        logger.error(f"❌ Error pool: {e}")
        return False

def get_db_conn():
    if connection_pool:
        try:
            return connection_pool.getconn()
        except:
            pass
    return None

def put_db_conn(conn):
    if connection_pool and conn:
        connection_pool.putconn(conn)

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
            """)
        conn.commit()
        logger.info("✅ BD inicializada")
        return True
    except Exception as e:
        logger.error(f"❌ Error BD: {e}")
        return False
    finally:
        put_db_conn(conn)

# === FUNCIONES DE USUARIO ===

def get_or_create_user(user_id, first_name, username, country='Global'):
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
                referral_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
                
                cur.execute("""
                    INSERT INTO users (id, first_name, username, wallet_address, referral_code, country)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (user_id, first_name, username, wallet, referral_code, country))
                user = cur.fetchone()
                conn.commit()
                logger.info(f"✅ Usuario creado: {user_id}")
            
            return user
    except Exception as e:
        logger.error(f"Error get_or_create_user: {e}")
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
                    pending_payout = pending_payout + %s
                WHERE id = %s;
            """, (reward, reward, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error add_task: {e}")
        return False
    finally:
        put_db_conn(conn)

# === HANDLERS DE TELEGRAM ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start."""
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    username = user.username or "user"
    
    user_data = get_or_create_user(user_id, first_name, username)
    
    if not user_data:
        await update.message.reply_text("❌ Error al inicializar. Intenta /start de nuevo")
        return
    
    welcome_msg = f"""
🚀 *¡Bienvenido a GRIDDLED!*

Hola {first_name}, la plataforma #1 de ingresos extras.

💰 *Tu potencial:* hasta $80/día
🎯 *Plan actual:* FREE
🎁 *Tokens:* {user_data[5] or 100}

✅ Pagos automáticos cada 24h
✅ 10+ plataformas integradas
✅ Retiros desde $2

👇 Empezá ahora:
"""
    
    keyboard = [
        ['💼 Ver Tareas', '💰 Mi Dashboard'],
        ['🛒 Marketplace', '🎁 Referir Amigos'],
        ['⚙️ Configurar Pagos', '📊 Stats']
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra tareas disponibles."""
    user_id = update.effective_user.id
    
    # Tareas simuladas (integrar APIs reales después)
    tasks = [
        {'id': 1, 'title': '📝 Encuesta 2min', 'reward': 0.25, 'platform': 'pollfish'},
        {'id': 2, 'title': '📱 Instalar App', 'reward': 0.80, 'platform': 'cpalead'},
        {'id': 3, 'title': '🎬 Ver Video 30s', 'reward': 0.10, 'platform': 'admob'},
        {'id': 4, 'title': '✅ Review Producto', 'reward': 0.35, 'platform': 'generic'},
        {'id': 5, 'title': '🔍 Validar Dato', 'reward': 0.15, 'platform': 'generic'},
        {'id': 6, 'title': '📸 Etiquetar Imagen', 'reward': 0.08, 'platform': 'generic'},
        {'id': 7, 'title': '💬 Tarea Social', 'reward': 0.40, 'platform': 'generic'},
        {'id': 8, 'title': '📊 Research 5min', 'reward': 0.60, 'platform': 'generic'},
    ]
    
    tasks_msg = "📋 *Tareas Disponibles*\n\n"
    
    for task in tasks:
        tasks_msg += f"{task['id']}. *{task['title']}*\n"
        tasks_msg += f"   💵 ${task['reward']:.2f}\n\n"
    
    tasks_msg += "📱 Escribí el número (1-8) para empezar."
    
    context.user_data['available_tasks'] = tasks
    
    await update.message.reply_text(tasks_msg, parse_mode=ParseMode.MARKDOWN)

async def handle_task_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja selección de tarea."""
    text = update.message.text
    
    if not text.isdigit():
        return
    
    task_num = int(text)
    tasks = context.user_data.get('available_tasks', [])
    
    if task_num < 1 or task_num > len(tasks):
        return
    
    task = tasks[task_num - 1]
    
    task_msg = f"""
✅ *Tarea Seleccionada*

📋 {task['title']}
💰 Ganarás: *${task['reward']:.2f}*

🎯 *Instrucciones:*
1. Abre el link
2. Completa la tarea
3. Presiona "✅ Completé"

⚠️ No uses VPN
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Abrir Tarea", url="https://example.com/task")],
        [InlineKeyboardButton("✅ Completé la Tarea", callback_data=f"complete_{task_num}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel")]
    ]
    
    await update.message.reply_text(
        task_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_task_completion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cuando se completa tarea."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if not data.startswith('complete_'):
        return
    
    task_num = int(data.split('_')[1])
    tasks = context.user_data.get('available_tasks', [])
    
    if task_num < 1 or task_num > len(tasks):
        await query.edit_message_text("❌ Tarea no encontrada")
        return
    
    task = tasks[task_num - 1]
    user_id = query.from_user.id
    
    # Registrar tarea completada
    success = add_task_earning(user_id, task['platform'], task['reward'])
    
    if success:
        await query.edit_message_text(
            f"🎉 *¡Tarea Completada!*\n\n"
            f"💰 Ganaste: *${task['reward']:.2f}*\n"
            f"✅ Agregado a tu balance\n\n"
            f"👉 Usa /dashboard para ver tu progreso",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text("❌ Error al procesar. Intenta de nuevo.")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra dashboard del usuario."""
    user_id = update.effective_user.id
    
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("❌ Error de conexión")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT country, subscription, tokens, total_earned, pending_payout, wallet_address
                FROM users WHERE id = %s;
            """, (user_id,))
            user_data = cur.fetchone()
            
            if not user_data:
                await update.message.reply_text("❌ Usuario no encontrado")
                return
            
            country, plan, tokens, total, pending, wallet = user_data
            
            cur.execute("""
                SELECT COUNT(*) FROM tasks_completed 
                WHERE user_id = %s AND DATE(completed_at) = CURRENT_DATE;
            """, (user_id,))
            tasks_today = cur.fetchone()[0]
    finally:
        put_db_conn(conn)
    
    country_info = COUNTRY_DATA.get(country, COUNTRY_DATA['Global'])
    
    dashboard_msg = f"""
📊 *TU DASHBOARD*

🌍 País: {country_info['name']}
💎 Plan: {plan}
🎁 Tokens: {tokens}

💰 *Finanzas:*
💵 Total ganado: ${total:.2f}
⏳ Pendiente: ${pending:.2f}
💳 Mínimo retiro: ${country_info['min_withdraw']}

📋 Tareas hoy: {tasks_today}

💳 Wallet: `{wallet}`
"""
    
    keyboard = [
        [InlineKeyboardButton("💼 Ver Tareas", callback_data="show_tasks_btn")],
        [InlineKeyboardButton("💸 Retirar", callback_data="withdraw")]
    ]
    
    await update.message.reply_text(
        dashboard_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra marketplace."""
    marketplace_msg = """
🛒 *MARKETPLACE*

Cursos y servicios que generan ingresos:

📚 *Plataformas Disponibles:*
"""
    
    keyboard = [
        [InlineKeyboardButton("📘 Udemy Courses", url="https://udemy.com/?ref=griddled")],
        [InlineKeyboardButton("🎓 Coursera", url="https://coursera.org/?ref=griddled")],
        [InlineKeyboardButton("🎨 Skillshare", url="https://skillshare.com/?ref=griddled")],
        [InlineKeyboardButton("💼 Fiverr", url="https://fiverr.com/?ref=griddled")],
        [InlineKeyboardButton("👔 Upwork", url="https://upwork.com/?ref=griddled")]
    ]
    
    await update.message.reply_text(
        marketplace_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def refer_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sistema de referidos."""
    user_id = update.effective_user.id
    
    conn = get_db_conn()
    if not conn:
        await update.message.reply_text("❌ Error de conexión")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT referral_code FROM users WHERE id = %s;", (user_id,))
            result = cur.fetchone()
            ref_code = result[0] if result else "ERROR"
    finally:
        put_db_conn(conn)
    
    ref_link = f"https://t.me/{context.bot.username}?start={ref_code}"
    
    refer_msg = f"""
🎁 *PROGRAMA DE REFERIDOS*

Tu código: `{ref_code}`
Tu link: {ref_link}

💎 *Ganancias:*
• $1 por cada registro
• 15% de sus ganancias

🚀 5 amigos = $7.50/día extra
"""
    
    keyboard = [
        [InlineKeyboardButton("📱 Compartir WhatsApp", url=f"https://wa.me/?text=Gana dinero: {ref_link}")],
        [InlineKeyboardButton("✈️ Compartir Telegram", url=f"https://t.me/share/url?url={ref_link}")]
    ]
    
    await update.message.reply_text(
        refer_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def configure_payouts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configurar pagos."""
    config_msg = """
⚙️ *CONFIGURAR PAGOS*

Métodos disponibles:
💳 PayPal
🔶 Binance
💰 AirTM
🇧🇷 PIX

Usa los botones para configurar:
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 PayPal", callback_data="setup_paypal")],
        [InlineKeyboardButton("🔶 Binance", callback_data="setup_binance")],
        [InlineKeyboardButton("💰 AirTM", callback_data="setup_airtm")]
    ]
    
    await update.message.reply_text(
        config_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estadísticas generales."""
    stats_msg = """
📊 *ESTADÍSTICAS GRIDDLED*

🌍 Usuarios: 50,000+
💰 Pagado: $1,250,000
✅ Tareas completadas: 2.5M

🏆 Top País: Brasil
🔥 Racha más larga: 89 días
"""
    
    await update.message.reply_text(stats_msg, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja callbacks de botones inline."""
    query = update.callback_query
    data = query.data
    
    if data == "show_tasks_btn":
        await query.answer()
        # Simular mensaje de texto para reutilizar handler
        update.message = query.message
        await show_tasks(update, context)
    
    elif data == "withdraw":
        await query.answer()
        await query.edit_message_text(
            "💸 *Retiros*\n\n"
            "Primero configura tu método de pago con:\n"
            "⚙️ Configurar Pagos",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("setup_"):
        method = data.split('_')[1]
        await query.answer()
        await query.edit_message_text(
            f"✅ Configurando {method}\n\n"
            f"Envía tu email/ID de {method}:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "cancel":
        await query.answer()
        await query.edit_message_text("❌ Tarea cancelada")

# === CONFIGURACIÓN QUART ===

@app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
async def webhook_handler():
    """Maneja updates de Telegram."""
    try:
        json_data = await request.get_json()
        update = Update.de_json(json_data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error webhook: {e}")
    return "ok", HTTPStatus.OK

@app.route('/health', methods=['GET'])
async def health_check():
    """Health check."""
    return {"status": "ok"}, HTTPStatus.OK

async def startup_bot():
    """Inicializa el bot."""
    global application, http_session
    
    if not init_db():
        logger.error("❌ BD no inicializada")
        return
    
    http_session = aiohttp.ClientSession()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # AGREGAR TODOS LOS HANDLERS
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dashboard", dashboard))
    
    # Handlers para botones del teclado (texto exacto)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^💼 Ver Tareas$'), show_tasks))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^💰 Mi Dashboard$'), dashboard))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^🛒 Marketplace$'), marketplace))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^🎁 Referir Amigos$'), refer_friend))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^⚙️ Configurar Pagos$'), configure_payouts))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^📊 Stats$'), stats))
    
    # Handler para selección de tareas (números)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d+$'), handle_task_selection))
    
    # Callbacks de botones inline
    application.add_handler(CallbackQueryHandler(handle_task_completion, pattern=r'^complete_'))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook: {webhook_url}")
    
    await application.start()
    logger.info("✅ Bot iniciado")

async def shutdown_bot():
    """Cierra el bot."""
    global application, http_session
    
    if http_session:
        await http_session.close()
    
    if application:
        await application.stop()
        await application.shutdown()
    
    logger.info("🛑 Bot detenido")

app.before_serving(startup_bot)
app.after_serving(shutdown_bot)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
