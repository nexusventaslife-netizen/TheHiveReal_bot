import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, filters
import os
import json
import logging
from firebase_admin import credentials, initialize_app, firestore

# --- Configuración de Logging ---
# Se configura el logging para ver mensajes de error en la consola de Render.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 1. Carga de Variables de Entorno ---
# Estas variables deben estar configuradas en Render.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS")

# --- 2. Validación de Credenciales Críticas ---
if not TELEGRAM_TOKEN or not FIREBASE_CREDENTIALS_JSON:
    logger.error("ERROR CRÍTICO: FIREBASE_CREDENTIALS no está configurada o falta TELEGRAM_TOKEN. El bot NO SE INICIARÁ.")
    # El bot debe fallar aquí para que Render sepa que hay un problema de configuración.
    exit(1)

# --- 3. Inicialización de Firebase (El Cofre del Tesoro) ---
db = None
try:
    # 1. Intenta convertir la llave JSON (que debe estar en una sola línea)
    creds_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
    cred = credentials.Certificate(creds_dict)
    
    # 2. Inicializa la conexión
    initialize_app(cred)
    db = firestore.client()
    logger.info("CONEXIÓN A FIRESTORE EXITOSA. Los datos de usuarios se guardarán correctamente.")
    
except Exception as e:
    logger.error(f"ERROR DE CONEXIÓN: Falló la conexión a Firebase. Verifica que el JSON esté en una SOLA LÍNEA en Render. Detalle: {e}")
    # El bot sigue, pero sin poder guardar datos (es decir, NO FUNCIONARÁ el negocio).
    pass

# --- 4. Funciones de Ayuda y Administración ---

# Convierte el ID de administrador a entero para comparaciones seguras.
try:
    ADMIN_USER_ID = int(ADMIN_USER_ID)
except (TypeError, ValueError):
    # Si la variable no está seteada o no es un número, usamos 0 para evitar errores.
    ADMIN_USER_ID = 0
    logger.warning("ADMIN_USER_ID no es un número válido o está ausente. La función de administrador no funcionará.")


def is_admin(user_id):
    """Verifica si el ID de usuario actual coincide con el ID del administrador."""
    return user_id == ADMIN_USER_ID

# --- 5. Funciones de Teclado (Menús) ---

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


# --- 6. Funciones de Manejadores (Handkers) ---

def start_command(update, context):
    """Maneja el comando /start e inicializa el teclado."""
    
    user = update.effective_user
    user_id = user.id
    
    # Mensaje de bienvenida, incluyendo el estado de Tokens
    message_text = (
        f"Somos el 'Booster' global para que ganes ingresos pasivos y activos. Tu misión es simple: "
        f"maximiza tu actividad y sube tu Racha Diaria.\n\n"
        f"Tu Status Actual: FREE\n"
        f"Tokens HVE: 5"  # Valor por defecto. Se conectaría a Firestore para el valor real.
    )
    
    # Enviamos el mensaje con el teclado generado (que incluye o no el botón ADMIN)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message_text,
        reply_markup=get_keyboard(user_id)
    )

def handle_message(update, context):
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
        context.bot.send_message(chat_id=chat_id, text=message)
        
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
            # Si un usuario normal intenta enviar el texto del admin
            message = "Opción no disponible. Por favor, selecciona una de las opciones del menú."

        context.bot.send_message(chat_id=chat_id, text=message)
        
    # Respuestas para otros botones (Lógica pendiente de implementación)
    elif any(keyword in text for keyword in ["Mis Estadísticas", "Marketplace GOLD", "GOLD Premium", "Privacidad y Datos"]):
        message = f"Opción seleccionada: {text}. Esta función se implementará con la base de datos activa."
        context.bot.send_message(chat_id=chat_id, text=message)
        
    else:
        # Respuesta para mensajes de texto no reconocidos
        context.bot.send_message(chat_id=chat_id, text="¡Hola! Por favor, selecciona una de las opciones del menú para interactuar.")


# --- 7. Función Principal de Arranque ---

def main():
    """Función de inicio del bot."""
    
    if not TELEGRAM_TOKEN:
        logger.error("Token de Telegram no encontrado. Saliendo.")
        return

    # Inicializa el Updater y el Dispatcher
    try:
        updater = Updater(TELEGRAM_TOKEN, use_context=True)
    except telegram.error.InvalidToken:
        logger.error("ERROR - El TELEGRAM_TOKEN no es válido. Saliendo.")
        return

    dp = updater.dispatcher

    # Registro de Handlers
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(MessageHandler(filters.Filters.text & ~filters.Filters.command, handle_message))

    # Inicia el bot (Polling es el método de conexión usado en Render)
    logger.info("Bot TheOneHive listo. Iniciando Polling...")
    updater.start_polling()
    # Mantiene el bot corriendo
    updater.idle()

if __name__ == '__main__':
    main()
