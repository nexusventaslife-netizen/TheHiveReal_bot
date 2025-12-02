import os 
import logging
import asyncio
from http import HTTPStatus
from quart import Quart, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
import psycopg2.pool
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_fixed
from web3 import Web3

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Variables Globales ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
DATABASE_URL = os.environ.get('DATABASE_URL') 
RPC_URL = os.environ.get('RPC_URL') 
NUMBEO_API_KEY = os.environ.get('NUMBEO_API_KEY') 
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://the-hivereal-bot.onrender.com')

# --- Instancias Globales ---
W3 = None 
connection_pool = None
application = None 
app = Quart(__name__) 

# --- Funciones de Conexión y Setup ---

def setup_db_pool():
    """Configura el pool de conexiones a PostgreSQL."""
    global connection_pool
    if not DATABASE_URL:
        logger.error("ERROR FATAL: DATABASE_URL no está configurada.")
        return False
    try:
        # Corregir el scheme si es necesario
        url = urlparse(DATABASE_URL)
        if url.scheme == 'postgres':
            # PostgreSQL moderno usa 'postgresql'
            connection_string = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            connection_string = DATABASE_URL
            
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            connection_string
        )
        logger.info("✅ Pool de Conexiones a PostgreSQL configurado exitosamente.")
        return True
    except Exception as e:
        logger.error(f"❌ ERROR FATAL DE CONEXIÓN DB: {e}")
        return False

def get_db_conn():
    """Obtiene una conexión del pool."""
    if connection_pool:
        try:
            return connection_pool.getconn()
        except Exception as e:
            logger.error(f"Error al obtener conexión del pool: {e}")
            return None
    return None

def put_db_conn(conn):
    """Devuelve una conexión al pool."""
    if connection_pool and conn:
        connection_pool.putconn(conn)

def init_db():
    """Inicializa la base de datos y crea el esquema."""
    if not setup_db_pool():
        return False
    
    conn = get_db_conn()
    if conn is None:
        logger.error("ERROR DB: No se pudo obtener conexión para crear esquema.")
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    first_name VARCHAR(255),
                    username VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'FREE',
                    tokens_hve INTEGER DEFAULT 5,
                    wallet_address VARCHAR(42),
                    country VARCHAR(50) DEFAULT 'Global', 
                    effort_hours FLOAT DEFAULT 0,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        logger.info("✅ Base de datos PostgreSQL inicializada correctamente.")
        return True
    except Exception as e:
        logger.error(f"❌ ERROR al inicializar DB: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

def setup_web3():
    """Configura Web3 (opcional)."""
    global W3
    if not RPC_URL:
        logger.warning("⚠️ RPC_URL no configurada. Funcionalidad Web3 deshabilitada.")
        W3 = None
        return False
    
    try:
        W3 = Web3(Web3.HTTPProvider(RPC_URL))
        if W3.is_connected():
            logger.info(f"✅ Conexión Web3 exitosa: {RPC_URL}")
            return True
        else:
            logger.error("❌ Web3 no pudo conectarse.")
            return False
    except Exception as e:
        logger.error(f"❌ Error Web3: {e}")
        W3 = None
        return False

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_econ_data(country):
    """Simula obtención de datos económicos."""
    return 5.0, 50.0 

def calc_max_earnings(min_wage, effort_hours, cost_living):
    """Calcula proyección de ingresos."""
    base = min_wage * effort_hours
    adjusted = base - (cost_living / 100 * base * 0.2)
    return max(0, round(adjusted, 2))

def get_eth_balance(address: str):
    """Obtiene saldo nativo de una wallet."""
    if not W3 or not W3.is_connected():
        return "N/A"
    
    try:
        if address == "N/A" or not address:
            return "0.0000"
        checksum_address = W3.to_checksum_address(address)
        balance_wei = W3.eth.get_balance(checksum_address)
        balance_eth = W3.from_wei(balance_wei, 'ether')
        return f"{balance_eth:.4f}"
    except Exception as e:
        logger.error(f"Error obteniendo balance: {e}")
        return "Error"

# --- Handlers de Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler del comando /start."""
    user = update.effective_user
    user_id = user.id
    is_admin = str(user_id) == ADMIN_USER_ID
    conn = get_db_conn()
    wallet = "N/A"
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tokens_hve, is_admin, country, effort_hours, wallet_address FROM users WHERE id = %s;",
                    (user_id,)
                )
                user_data = cur.fetchone()
                
                if user_data is None:
                    # Crear nuevo usuario
                    wallet = "0x" + os.urandom(20).hex()
                    cur.execute("""
                        INSERT INTO users (id, first_name, username, is_admin, wallet_address) 
                        VALUES (%s, %s, %s, %s, %s);
                    """, (user_id, user.first_name, user.username, is_admin, wallet))
                    conn.commit()
                    tokens, hours, country = 5, 0, 'Global'
                else:
                    tokens, is_admin_db, country, hours, wallet = user_data
                    cur.execute(
                        "UPDATE users SET first_name = %s, username = %s WHERE id = %s;",
                        (user.first_name, user.username, user_id)
                    )
                    conn.commit()
                    
            min_wage, cost_living = get_econ_data(country)
            max_daily = calc_max_earnings(min_wage, hours if hours > 0 else 4, cost_living)
        except Exception as e:
            logger.error(f"Error SQL en /start: {e}")
            max_daily = 5.00
        finally:
            put_db_conn(conn)
    else:
        max_daily = 5.00
        
    welcome_text = (
        f"¡Hola, {user.first_name}! ¡Bienvenido a The Hive Real!\n\n"
        f"🔑 Tu Wallet (HVE/BSC): `{wallet}`\n"
        f"💰 Proyección Máx Diaria ({country}): **${max_daily}**\n\n"
        "📈 Maximiza tu actividad y aumenta tus ganancias."
    )
    
    keyboard = [
        ["5 Vías de Ingreso", "Mis Estadísticas"],
        ["Reto Viral", "Marketplace GOLD"],
        ["GOLD Premium", "Privacidad y Datos"],
        ["/proyeccion", "/cashout", "/balance"]
    ]
    
    if is_admin:
        keyboard.append(["🛠️ Panel Admin"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def proyeccion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /proyeccion."""
    response = (
        "📊 **PROYECCIÓN DIARIA**\n\n"
        "Tu ingreso potencial se basa en:\n"
        "• **Horas de Esfuerzo:** 4h (actual)\n"
        "• **Salario Mínimo Regional:** $5.00/h\n"
        "• **Índice de Costo de Vida:** 50%\n\n"
        "Próximamente podrás configurar tu país."
    )
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /cashout."""
    response = (
        "💰 **RETIRO DE HVE TOKENS**\n\n"
        "Función en desarrollo.\n"
        "Pronto podrás retirar tus HVE Tokens a tu wallet."
    )
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /balance."""
    user_id = update.effective_user.id
    conn = get_db_conn()
    response = "❌ Error: Conexión DB fallida."
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT wallet_address, tokens_hve FROM users WHERE id = %s;",
                    (user_id,)
                )
                data = cur.fetchone()
                
                if data and data[0]:
                    wallet_address = data[0]
                    hve_tokens = data[1]
                    eth_balance_str = get_eth_balance(wallet_address)
                    
                    response = (
                        f"💳 **SALDOS DE BILLETERA**\n\n"
                        f"Dirección: `{wallet_address}`\n\n"
                        f"**BNB/ETH:** {eth_balance_str}\n"
                        f"**HVE Tokens:** {hve_tokens} HVE\n"
                    )
                else:
                    response = "Tu billetera no está registrada. Usa /start primero."
        except Exception as e:
            logger.error(f"Error en /balance: {e}")
            response = "Error interno al consultar datos."
        finally:
            put_db_conn(conn)
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para mensajes de texto."""
    text = update.message.text
    
    responses = {
        "5 Vías de Ingreso": "🚀 Estas son las 5 vías de ingreso en HVE...",
        "Mis Estadísticas": "📊 Aquí verás tu racha diaria y puntos.",
        "Reto Viral": "🎯 Participa en el reto viral y gana tokens.",
        "Marketplace GOLD": "🏪 Accede al marketplace de cursos premium.",
        "GOLD Premium": "💎 Suscripción premium por $15 USD/mes.",
        "Privacidad y Datos": "🔒 Información sobre privacidad y uso de datos."
    }
    
    response = responses.get(text, f"Mensaje recibido: **{text}**")
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

# --- Configuración Quart (Web Server) ---

@app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
async def webhook_handler():
    """Procesa updates de Telegram vía webhook."""
    if request.method == "POST":
        try:
            json_data = await request.get_json()
            update = Update.de_json(json_data, application.bot)
            await application.process_update(update)
        except Exception as e:
            logger.error(f"❌ Error procesando update: {e}")
    return "ok", HTTPStatus.OK

@app.route('/health', methods=['GET'])
async def health_check():
    """Endpoint de health check."""
    return {"status": "ok", "service": "telegram-bot"}, HTTPStatus.OK

async def startup_bot():
    """Inicializa bot, DB, Web3 y configura webhook."""
    global application
    
    # 1. Inicializar DB
    db_ok = init_db()
    
    # 2. Inicializar Web3 (opcional)
    setup_web3()
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN no configurado.")
        return
    
    if not db_ok:
        logger.error("❌ DB no inicializada correctamente.")
        return
    
    # 3. Construir aplicación de Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 4. Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proyeccion", proyeccion))
    application.add_handler(CommandHandler("cashout", cashout))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 5. Inicializar la aplicación primero
    await application.initialize()
    
    # 6. Configurar webhook
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    
    try:
        # Eliminar webhook anterior si existe
        await application.bot.delete_webhook(drop_pending_updates=True)
        
        # Configurar nuevo webhook
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ WebHook configurado: {webhook_url}")
        
        # 7. Iniciar el motor de la aplicación
        await application.start()
        logger.info("✅ Bot iniciado correctamente en modo webhook.")
        
    except Exception as e:
        logger.error(f"❌ ERROR CONFIGURANDO WEBHOOK: {e}")
        raise

async def shutdown_bot():
    """Cierra conexiones al detener el servicio."""
    global application
    if application:
        await application.stop()
        await application.shutdown()
    logger.info("🛑 Bot detenido correctamente.")

# Registrar funciones de inicio y cierre
app.before_serving(startup_bot)
app.after_serving(shutdown_bot)

if __name__ == "__main__":
    # Para desarrollo local
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
