Import os
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
# from web3.middleware import geth_poa_middleware # Descomentar si usas PoA/sidechains

# --- Configuración de Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Variables Globales ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
DATABASE_URL = os.environ.get('DATABASE_URL') 
RPC_URL = os.environ.get('RPC_URL') # URL del nodo RPC (ej: Infura/Alchemy)
NUMBEO_API_KEY = os.environ.get('NUMBEO_API_KEY') 
RENDER_EXTERNAL_URL_FORZADA = "https://the-hivereal-bot.onrender.com" 

# --- Web3 Global Instance ---
W3 = None # Instancia global de Web3

# ... (El código de setup_db_pool, get_db_conn, put_db_conn, init_db es igual) ...
connection_pool = None
db_initialized = False # Inicialmente False

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
        # Si usas una red PoA (ej: Polygon, Binance Smart Chain), descomenta la siguiente línea:
        # W3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if W3.is_connected():
            logger.info(f"Conexión Web3 exitosa a: {RPC_URL}")
            return True
        else:
            logger.error("Conexión Web3 fallida. Revisa la RPC_URL y la red.")
            return False
    except Exception as e:
        logger.error(f"Error al inicializar Web3: {e}")
        W3 = None
        return False

# --- Funciones de Datos Económicos (Iguales) ---
# ...

# --- Funciones de Web3 ---

def get_eth_balance(address: str):
    """Obtiene el saldo de ETH (o la moneda nativa) de una dirección."""
    if not W3 or not W3.is_connected():
        return "ERROR: Conexión Web3 no disponible."
    
    try:
        # 1. Obtener el saldo en Wei
        checksum_address = W3.to_checksum_address(address)
        balance_wei = W3.eth.get_balance(checksum_address)
        
        # 2. Convertir de Wei a Ether
        balance_eth = W3.from_wei(balance_wei, 'ether')
        
        return f"{balance_eth:.4f}"
    except Exception as e:
        logger.error(f"Error al obtener el saldo para {address}: {e}")
        return "Error al consultar la cadena."


# --- Handlers de Telegram ---

# ... (El handler 'start' es igual, pero ahora usa la wallet_address) ...

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el saldo de ETH/HVE del usuario."""
    user_id = update.effective_user.id
    conn = get_db_conn()
    response = "Error: Conexión a DB fallida."

    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT wallet_address FROM users WHERE id = %s;", (user_id,))
                data = cur.fetchone()
                
                if data and data[0]:
                    wallet_address = data[0]
                    # 1. Obtener saldo nativo (ETH)
                    eth_balance_str = get_eth_balance(wallet_address)
                    
                    # 2. Obtener saldo HVE (Requiere contrato, aquí solo placeholder)
                    hve_tokens = "5" # Placeholder DB o Contrato
                    
                    response = (
                        f"💳 **SALDOS DE BILLETERA** 💳\n"
                        f"Dirección: `{wallet_address}`\n\n"
                        f"**Saldo ETH/BNB (Nativo):** **{eth_balance_str}**\n"
                        f"**Saldo HVE Tokens:** **{hve_tokens} HVE**\n"
                        f"\n_Nota: El saldo de HVE requiere la integración del contrato inteligente._"
                    )
                else:
                    response = "Tu billetera aún no está registrada. Usa /start para inicializarla."
        except Exception as e:
            logger.error(f"Error en el handler /balance: {e}")
            response = "Error interno al consultar la base de datos."
        finally:
            put_db_conn(conn)

    await update.message.reply_text(response, parse_mode=telegram.constants.ParseMode.MARKDOWN)

# ... (Los handlers 'proyeccion', 'cashout', 'handle_message' son iguales) ...

# --- Función Principal (Inicia todo) ---

def main() -> None:
    """Inicia el bot con el modo WebHook, optimizado para Render/Quart."""
    global application, db_initialized

    # 1. Configurar la DB y Web3
    db_initialized = init_db() # Inicializa DB Pool y la tabla
    setup_web3() # Inicializa Web3
    
    if not TELEGRAM_TOKEN or not db_initialized:
        logger.error("El bot no puede iniciar. Revisa TOKEN, DATABASE_URL y logs de inicialización.")
        return

    # 2. Crear la aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 3. Agregar Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proyeccion", proyeccion))
    application.add_handler(CommandHandler("cashout", cashout))
    application.add_handler(CommandHandler("balance", balance)) # NUEVO HANDLER
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 4. Configurar el WebHook en Telegram (Usa la URL forzada)
    webhook_url = f"{RENDER_EXTERNAL_URL_FORZADA}/{TELEGRAM_TOKEN}"
    
    try:
        application.bot.set_webhook(url=webhook_url)
        logger.info(f"WebHook configurado exitosamente: {webhook_url}")
    except Exception as e:
        logger.error(f"ERROR al configurar el WebHook. Error: {e}")
        return

    # 5. Iniciar el Servidor Quart
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Servicio WebHook (Quart) iniciado en el puerto {port}")
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()
