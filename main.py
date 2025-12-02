import telegram
import signal
import sys
import os
import json
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from firebase_admin import credentials, initialize_app, firestore
from firebase_admin.exceptions import InvalidArgumentError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout  # Aseguramos que los logs vayan a la consola de Render
)
logger = logging.getLogger(__name__)

# --- 1. Carga de Variables de Entorno ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS")

# --- 2. Inicialización de Firebase (Blindado contra fallos de JSON) ---
db = None
try:
    if not FIREBASE_CREDENTIALS_JSON:
        logger.error("ERROR CRÍTICO: FIREBASE_CREDENTIALS no está configurada. La funcionalidad de DB está deshabilitada.")
    else:
        # Intentamos cargar el JSON, que es el punto de fallo más común
        creds_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(creds_dict)
        
        # Intentamos inicializar la app. Usamos un nombre específico para evitar
        # el ValueError: The default Firebase app does not exist si ya se inicializó antes.
        try:
            initialize_app(cred, name="theonehive_app")
            db = firestore.client()
            logger.info("CONEXIÓN A FIRESTORE EXITOSA. Los datos de usuarios se guardarán correctamente.")
        except ValueError:
            # Si el valor de inicialización falla, podría ser porque ya se inicializó
            # o hay un problema más profundo con el formato.
            logger.error("ERROR DE INICIALIZACIÓN DE FIREBASE: Posiblemente el JSON es incorrecto o la app ya existe.")
            
except (json.JSONDecodeError, InvalidArgumentError, TypeError) as e:
    logger.error(f"ERROR DE JSON EN FIREBASE_CREDENTIALS. Por favor, minifica el JSON. Detalle: {e}")
except Exception as e:
    logger.error(f"ERROR DE CONEXIÓN A FIRESTORE INESPERADO: {e}")
    pass


# --- 3. Funciones de Ayuda y Administración ---

try:
    ADMIN_USER_ID = int(ADMIN_USER_ID)
except (TypeError, ValueError):
    ADMIN_USER_ID = 0
    logger.warning("ADMIN_USER_ID no es un número válido o está ausente. La función de administrador no funcionará.")


def is_admin(user_id):
    """Verifica si el ID de usuario actual coincide con el ID del administrador."""
    return user_id == ADMIN_USER_ID

# --- 4. Funciones de Teclado (Menús) ---

def get_keyboard(user_id):
    """Genera el teclado dinámicamente basado en el rol del usuario."""
    
    # Teclado BÁSICO (Para todos los usuarios)
    keyboard = [
        [telegram.KeyboardButton("💰 Mis Estadísticas (APD V2)")],
        [telegram.KeyboardButton("🚀 Reto Viral (Gana HVE Tokens)")],
        [telegram.KeyboardButton("🛒 Marketplace GOLD (Cursos/Libros)")],
        [telegram.KeyboardButton("👑 GOLD Premium ($15 USD)")],
        [telegram.KeyboardButton("🔒 Privacidad y Datos (Bono HVE)")],
    ]

    # Lógica para insertar el botón de Administración (SOLO si es el Admin)
    if is_admin(user_id):
        # Insertamos el botón de 5 Vías de Ingreso al principio solo para el Admin
        keyboard.insert(0, [telegram.KeyboardButton("📊 5 Vías de Ingreso (ADMIN)")])

    # El teclado del bot
    return telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# --- 5. Funciones de Manejadores (Handlers) - AHORA ASÍNCRONAS ---

async def start_command(update, context):
    """Maneja el comando /start e inicializa el teclado."""
    
    user = update.effective_user
    user_id = user.id
    
    # Mensaje de bienvenida, incluyendo el estado de Tokens
    message_text = (
        f"Somos el 'Booster' global para que ganes ingresos pasivos y activos. Tu misión es simple: "
        f"maximiza tu actividad y sube tu Racha Diaria.\n\n"
        f"Tu Status Actual: FREE\n"
        f"Tokens HVE: 5"
    )
    
    # Usamos await para la llamada de la API
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message_text,
        reply_markup=get_keyboard(user_id)
    )

async def handle_message(update, context):
    """Maneja todos los mensajes de texto del usuario."""
    
    # Usamos update.message.text de forma segura
    text = update.message.text if update.message else ""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    message = "¡Hola! Por favor, selecciona una de las opciones del menú para interactuar."

    # Lógica de Reto Viral
    if "Reto Viral" in text:
        message = (
            "🚀 RETO VIRAL (GANANCIA GRATUITA DE TOKENS)\n\n"
            "Queremos ser la plataforma más grande. Ayúdanos a crecer y gana HVE Tokens extra!\n\n"
            "¿CÓMO FUNCIONA?\n"
            "1. Crea un video en TikTok, Instagram Reels o YouTube Shorts mostrando tu Racha Diaria o tu Proyección de Ganancia en el bot.\n"
            "2. Usa el hashtag #TheOneHiveApp.\n"
            "3. Envíanos el enlace por mensaje privado a este bot.\n\n"
            "🎁 Recompensa: 200 HVE Tokens por video aprobado. (Solo 1 video por usuario)"
        )
        
    # Lógica de 5 Vías de Ingreso (Solo para el Admin)
    elif "5 Vías de Ingreso" in text:
        if is_admin(user_id):
            message = (
                "ADMIN: Este es el menú de 5 Vías de Ingreso para administrar el negocio.\n\n"
                "Aquí puedes gestionar:\n"
                "- Vía 1: Venta de Licencias (GOLD Premium)\n"
                "- Vía 2: Venta de Cursos/Ebooks (Marketplace)\n"
                "- Vía 3: Recompensa por Actividad (Tokens HVE)\n"
                "- Vía 4: Bono por Privacidad\n"
                "- Vía 5: Reto Viral (Marketing)\n\n"
                "Este mensaje es de uso interno."
            )
        else:
            message = "Opción no disponible. Por favor, selecciona una de las opciones del menú."
        
    # Respuestas para otros botones (Lógica pendiente de implementación)
    elif any(keyword in text for keyword in ["Mis Estadísticas", "Marketplace GOLD", "GOLD Premium", "Privacidad y Datos"]):
        message = f"Opción seleccionada: {text}. Esta función se implementará con la base de datos activa."
        
    # Usamos await para la llamada de la API
    await context.bot.send_message(chat_id=chat_id, text=message)


# --- 6. Función Principal de Arranque ---

def main():
    """Función de inicio del bot y manejo de señales para Render."""
    
    if not TELEGRAM_TOKEN:
        logger.error("Token de Telegram no encontrado. Saliendo.")
        return

    # Usamos la sintaxis moderna (Application)
    try:
        # 1. Creamos la Aplicación con el token
        application = Application.builder().token(TELEGRAM_TOKEN).build()
    except telegram.error.InvalidToken:
        logger.error("ERROR - El TELEGRAM_TOKEN no es válido. Saliendo.")
        return

    # 2. Registramos Handlers
    application.add_handler(CommandHandler("start", start_command))
    # Filtros modernos: filters.TEXT y filters.COMMAND
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. Inicia el bot (Polling)
    logger.info("Bot TheOneHive listo. Iniciando Polling...")
    
    # Esta línea es la mitigación crítica para el ConflictError en Render, 
    # ya que maneja las señales de cierre de forma limpia.
    application.run_polling(stop_signals=[signal.SIGINT, signal.SIGTERM])
    
    logger.info("El bot se ha detenido.")

if __name__ == '__main__':
    main()
