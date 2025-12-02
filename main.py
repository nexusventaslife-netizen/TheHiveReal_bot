import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from telegram.error import Conflict
import os
import json
import logging
import signal
from firebase_admin import credentials, initialize_app, firestore

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 1. Carga de Variables de Entorno ---
# Render proporciona el puerto automáticamente
PORT = int(os.environ.get('PORT', 8080))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- 2. Validación y Conversión de IDs ---
try:
    ADMIN_USER_ID = int(ADMIN_USER_ID)
except (TypeError, ValueError):
    ADMIN_USER_ID = 0
    logger.warning("ADMIN_USER_ID no es un número válido o está ausente. La función de administrador no funcionará.")

def is_admin(user_id):
    """Verifica si el ID de usuario actual coincide con el ID del administrador."""
    return user_id == ADMIN_USER_ID

# --- 3. Inicialización de Firebase (Blindado contra fallos de JSON) ---
db = None
def initialize_firebase():
    global db
    if not FIREBASE_CREDENTIALS_JSON:
        logger.error("ERROR - FIREBASE_CREDENTIALS no está configurada. Operaciones de guardado fallarán.")
        return

    try:
        # Intenta cargar el JSON directamente (mitiga problemas de formato)
        creds_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(creds_dict)
        
        # El nombre del app debe ser único o no especificarlo para evitar el ValueError: "The default Firebase app does not exist."
        initialize_app(cred, name="theonehive_bot_app") 
        db = firestore.client()
        logger.info("CONEXIÓN A FIRESTORE EXITOSA. Los datos de usuarios se guardarán correctamente.")
        
    except ValueError as ve:
        logger.error(f"ERROR DE INICIALIZACIÓN DE FIREBASE: ValueError: {ve}. Verifique si el JSON ya se inicializó.")
    except Exception as e:
        logger.error(f"ERROR DE CONEXIÓN CRÍTICO: Falló la conexión a Firebase. Detalle: {e}")

initialize_firebase()

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

# --- 5. Funciones de Manejadores (Handlers) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Enviamos el mensaje con el teclado generado (que incluye o no el botón ADMIN)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message_text,
        reply_markup=get_keyboard(user_id)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los mensajes de texto del usuario."""
    
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

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
        await context.bot.send_message(chat_id=chat_id, text=message)
        
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

        await context.bot.send_message(chat_id=chat_id, text=message)
        
    # Respuestas para otros botones (Lógica pendiente de implementación)
    elif any(keyword in text for keyword in ["Mis Estadísticas", "Marketplace GOLD", "GOLD Premium", "Privacidad y Datos"]):
        # Aquí se implementaría la lógica de la base de datos (db.collection...)
        message = f"Opción seleccionada: {text}. Esta función se implementará con la base de datos activa."
        await context.bot.send_message(chat_id=chat_id, text=message)
        
    else:
        # Respuesta para mensajes de texto no reconocidos
        await context.bot.send_message(chat_id=chat_id, text="¡Hola! Por favor, selecciona una de las opciones del menú para interactuar.")

# --- 6. Función Principal de Arranque (WebHook) ---

def main():
    """Configura y ejecuta el bot en modo WebHook para Render."""
    
    if not TELEGRAM_TOKEN or not RENDER_EXTERNAL_URL:
        logger.error("ERROR CRÍTICO: Falta TELEGRAM_TOKEN o RENDER_EXTERNAL_URL. Saliendo.")
        return

    # 1. Creamos la Aplicación con el token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. Registramos Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. Configuración del WebHook
    webhook_url = RENDER_EXTERNAL_URL
    
    try:
        # Se necesita la URL para que Telegram sepa dónde enviar los mensajes
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN, # La URL pública de Render termina en el token
            webhook_url=f"{webhook_url}/{TELEGRAM_TOKEN}",
            # Este es el manejo crítico para Render: detiene el bot limpiamente
            stop_signals=[signal.SIGINT, signal.SIGTERM]
        )
        logger.info(f"Bot TheOneHive iniciado en modo WebHook. Escuchando en el puerto {PORT}.")
        
    except Conflict as c:
        logger.error(f"ERROR DE CONFLICTO (esperado): El bot ya estaba corriendo. Detalle: {c}")
    except Exception as e:
        logger.error(f"ERROR FATAL DE WEBHOOK: {e}")

if __name__ == '__main__':
    main()
