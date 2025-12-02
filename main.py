import os
import logging
import json
from http import HTTPStatus
from quart import Quart, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import telegram
import psycopg2.pool
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_fixed
import requests
from web3 import Web3
# ESTA LÍNEA DE IMPORTACIÓN FUE COMENTADA PARA EVITAR EL CRASH DE 'ImportError' EN RENDER:
# from web3.middleware import geth_poa_middleware 

# --- Configuración de Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Variables Globales (Configuradas en Render) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
DATABASE_URL = os.environ.get('DATABASE_URL') 
RPC_URL = os.environ.get('RPC_URL') # URL del nodo RPC (ej: Infura/Alchemy/BSC)
NUMBEO_API_KEY = os.environ.get('NUMBEO_API_KEY') 
# Reemplaza con la URL pública de tu servicio en Render
RENDER_EXTERNAL_URL_FORZADA = "https://the-hivereal-bot.onrender.com" 

# --- Instancias Globales ---
W3 = None # Instancia global de Web3
connection_pool = None
db_initialized = False # Inicialmente False

# --- Configuración de Pool de Conexiones a PostgreSQL ---
def setup_db_pool():
    """Configura el pool de conexiones a la DB."""
    global connection_pool
    if not DATABASE_URL:
        logger.error("ERROR FATAL: DATABASE_URL no está configurada. EL BOT NO PUEDE FUNCIONAR.")
        return False
    try:
        url = urlparse(DATABASE_URL)
        # Ajuste para psycopg2 si la URL tiene un esquema 'postgresql' en lugar de 'postgres'
        if url.scheme in ('postgresql', 'postgresqls'):
            url = url._replace(scheme='postgres') 
            
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20, # Min 1 conexión, Max 20 conexiones
            user=url.username, 
            password=url.password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:]
        )
        logger.info("Pool de Conexiones a PostgreSQL configurado exitosamente.")
        return True
    except Exception as e:
        # LOGGING EXPLÍCITO DE FALLO DE CONEXIÓN
        logger.error(f"ERROR FATAL DE CONEXIÓN DB: Falló al configurar el Pool. Revise DATABASE_URL. Detalles: {e}")
        return False

def get_db_conn():
    """Obtiene una conexión del pool."""
    if connection_pool:
        try:
            return connection_pool.getconn()
        except Exception as e:
            logger.error(f"Error al obtener conexión del pool (runtime): {e}")
            return None
    return None

def put_db_conn(conn):
    """Devuelve una conexión al pool."""
    if connection_pool and conn:
        connection_pool.putconn(conn)

def init_db():
    """Inicializa el esquema de la base de datos (crea la tabla 'users')."""
    if not setup_db_pool():
        return False

    conn = get_db_conn()
    if conn is None:
        logger.error("ERROR DB: No se pudo obtener la conexión inicial para crear el esquema.")
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
        logger.info("Base de datos PostgreSQL inicializada y esquema verificado.")
        return True
    except Exception as e:
        # LOGGING EXPLÍCITO DE FALLO DE ESQUEMA
        logger.error(f"ERROR FATAL DE ESQUEMA DB: Falló al inicializar o crear la tabla 'users'. Detalles: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

# --- Inicialización de Web3 ---

def setup_web3():
    """Inicializa la conexión de Web3 usando la RPC_URL del entorno."""
    global W3
    if not RPC_URL:
        logger.error("ERROR WEB3: RPC_URL no está configurada. La funcionalidad cripto está deshabilitada.")
        W3 = None
        return False
    try:
        W3 = Web3(Web3.HTTPProvider(RPC_URL))
        # Se ha comentado la siguiente línea para evitar el error de ImportError:
        # W3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if W3.is_connected():
            logger.info(f"Conexión Web3 exitosa a: {RPC_URL}")
            return True
        else:
            # LOGGING EXPLÍCITO DE FALLO DE WEB3
            logger.error("ERROR FATAL DE WEB3: Conexión Web3 fallida. La RPC está rechazada o es inválida.")
            return False
    except Exception as e:
        # LOGGING EXPLÍCITO DE ERROR GENÉRICO WEB3
        logger.error(f"ERROR WEB3 GENÉRICO: Error al inicializar Web3. Detalles: {e}")
        W3 = None
        return False

# --- Resto del código (sin cambios) ---
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_econ_data(country):
    """Obtiene datos económicos (ejemplo con Numbeo)."""
    if not NUMBEO_API_KEY:
        return 5.0, 50.0 # Fallback global USD/h y Costo de vida index
    # Lógica de API de Numbeo...
    return 5.0, 50.0 # Fallback

def calc_max_earnings(min_wage, effort_hours, cost_living):
    """Calcula la proyección de ingresos diarios."""
    base = min_wage * effort_hours
    adjusted = base - (cost_living / 100 * base * 0.2) 
    return max(0, round(adjusted, 2))

def get_eth_balance(address: str):
    """Obtiene el saldo de la moneda nativa (ETH/BNB) de una dirección."""
    if not W3 or not W3.is_connected():
        return "ERROR: Conexión Web3 no disponible."
    
    try:
        # Generar una dirección de prueba si es "N/A"
        if address == "N/A":
            return "0.0000"

        checksum_address = W3.to_checksum_address(address)
        balance_wei = W3.eth.get_balance(checksum_address)
        balance_eth = W3.from_wei(balance_wei, 'ether')
        return f"{balance_eth:.4f}"
    except Exception as e:
        logger.error(f"Error al obtener el saldo para {address}: {e}")
        return "Error al consultar la cadena."


# --- Handlers de Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start e interactúa con la DB."""
    user = update.effective_user
    user_id = user.id
    is_admin = str(user_id) == ADMIN_USER_ID
    
    conn = get_db_conn()
    wallet = "N/A"
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT tokens_hve, is_admin, country, effort_hours, wallet_address FROM users WHERE id = %s;", (user_id,))
                user_data = cur.fetchone()

                if user_data is None:
                    # Generar wallet de prueba (se reemplazará por la wallet real de Hive)
                    wallet = "0x" + os.urandom(20).hex() 
                    cur.execute("""
                        INSERT INTO users (id, first_name, username, is_admin, wallet_address) 
                        VALUES (%s, %s, %s, %s, %s);
                    """, (user_id, user.first_name, user.username, is_admin, wallet))
                    conn.commit()
                    tokens, hours, country = 5, 0, 'Global'
                else:
                    tokens, is_admin_db, country, hours, wallet = user_data
                    cur.execute("""
                        UPDATE users SET first_name = %s, username = %s WHERE id = %s;
                    """, (user.first_name, user.username, user_id))
                    conn.commit()

            min_wage, cost_living = get_econ_data(country)
            max_daily = calc_max_earnings(min_wage, hours if hours > 0 else 4, cost_living)
            
        except Exception as e:
            logger.error(f"Error de SQL al procesar /start: {e}")
            max_daily = "5.00 (Default)"
        finally:
            put_db_conn(conn)
    else:
        max_daily = "Error (DB Fallback)"
        
    # Texto final de bienvenida
    welcome_text = (
        f"¡Hola, {user.first_name}! ¡Bienvenido a The Hive Real!\n"
        f"Tu Wallet (HVE/BSC): `{wallet}`\n"
        f"Proyección Máx Diaria ({country}): **${max_daily}**\n\n"
        "📈 Maximiza tu actividad y sube tu Racha Diaria."
    )
    
    keyboard = [
        ["5 Vías de Ingreso", "Mis Estadísticas (APD V2)"],
        ["Reto Viral (Gana HVE Tokens)", "Marketplace GOLD (Cursos/Libros)"],
        ["GOLD Premium ($15 USD)", "Privacidad y Datos (Bono HVE)"],
        ["/proyeccion", "/cashout", "/balance"]
    ]
    if is_admin:
        keyboard.append(["🛠️ Panel Admin"])
        
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)

async def proyeccion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la proyección detallada de ingresos."""
    response = (
        "📊 **PROYECCIÓN DIARIA**\n"
        "Tu ingreso potencial se basa en:\n"
        "- **Horas de Esfuerzo:** 4h (actual)\n"
        "- **Salario Mínimo Regional:** $5.00/h (Default)\n"
        "- **Índice de Costo de Vida:** 50%\n\n"
        "Próximamente: podrás configurar tu país para una proyección más precisa."
    )
    await update.message.reply_text(response, parse_mode=telegram.constants.ParseMode.MARKDOWN)

async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Proceso de retiro (Cashout)."""
    response = (
        "💰 **RETIRO (CASHOUT) DE HVE TOKENS**\n"
        "Actualmente, la función de Cashout está en desarrollo.\n"
        "Pronto podrás retirar tus HVE Tokens directamente a tu Wallet BSC/ETH."
    )
    await update.message.reply_text(response, parse_mode=telegram.constants.ParseMode.MARKDOWN)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el saldo de la moneda nativa (BNB/ETH) y HVE del usuario."""
    user_id = update.effective_user.id
    conn = get_db_conn()
    response = "Error: Conexión a DB fallida."

    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT wallet_address, tokens_hve FROM users WHERE id = %s;", (user_id,))
                data = cur.fetchone()
                
                if data and data[0]:
                    wallet_address = data[0]
                    hve_tokens = data[1]

                    # 1. Obtener saldo nativo (BNB/ETH) usando Web3
                    eth_balance_str = get_eth_balance(wallet_address)
                    
                    response = (
                        f"💳 **SALDOS DE BILLETERA** 💳\n"
                        f"Dirección (BSC/ETH): `{wallet_address}`\n\n"
                        f"**Saldo BNB/ETH (Nativo):** **{eth_balance_str}**\n"
                        f"**Saldo HVE Tokens:** **{hve_tokens} HVE**\n"
                        f"\n_El saldo nativo (BNB/ETH) es usado para pagar gas._"
                    )
                else:
                    response = "Tu billetera aún no está registrada. Usa /start para inicializarla."
        except Exception as e:
            logger.error(f"Error en el handler /balance: {e}")
            response = "Error interno al consultar la base de datos o la cadena."
        finally:
            put_db_conn(conn)

    await update.message.reply_text(response, parse_mode=telegram.constants.ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto que no son comandos."""
    text = update.message.text
    # Lógica simplificada del menú principal (ejemplo)
    if text == "5 Vías de Ingreso":
        response = "Estas son las 5 vías que te permiten obtener ingresos en HVE..."
    elif text == "Mis Estadísticas (APD V2)":
        response = "Aquí verás tu Racha Diaria, Puntos de Esfuerzo y más."
    else:
        response = f"Has enviado el mensaje: **{text}**. Por favor, usa el teclado o los comandos para interactuar."
        
    await update.message.reply_text(response, parse_mode=telegram.constants.ParseMode.MARKDOWN)

# --- Configuración del Servidor Web (Quart) ---
app = Quart(__name__)
application = None 

@app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
async def webhook_handler():
    """Recibe y procesa las actualizaciones enviadas por Telegram."""
    if request.method == "POST":
        # Asegúrate de que request.get_json() se use con await ya que Quart es asíncrono
        try:
            update = Update.de_json(await request.get_json(), application.bot)
            await application.process_update(update) 
        except Exception as e:
            logger.error(f"Error al procesar el Update de Telegram: {e}")
            # Retornamos OK para evitar que Telegram reenvíe el mensaje
    return "ok", HTTPStatus.OK

def main() -> None:
    """Inicia el bot con el modo WebHook."""
    global application, db_initialized

    # 1. Configurar la DB y Web3
    db_initialized = init_db() 
    setup_web3() 
    
    if not TELEGRAM_TOKEN or not db_initialized:
        logger.error("El bot no puede iniciar. Revisa TELEGRAM_TOKEN o DATABASE_URL.")
        return

    # 2. Crear la aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 3. Agregar Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proyeccion", proyeccion))
    application.add_handler(CommandHandler("cashout", cashout))
    application.add_handler(CommandHandler("balance", balance)) 
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 4. Configurar el WebHook en Telegram
    webhook_url = f"{RENDER_EXTERNAL_URL_FORZADA}/{TELEGRAM_TOKEN}"
    try:
        application.bot.set_webhook(url=webhook_url)
        logger.info(f"WebHook configurado exitosamente: {webhook_url}")
    except Exception as e:
        logger.error(f"ERROR al configurar el WebHook. Error: {e}")
        return

    # 5. Iniciar el Servidor Quart (Quart escucha por HTTP/HTTPS)
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Servicio WebHook (Quart) iniciado en el puerto {port}")
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()
