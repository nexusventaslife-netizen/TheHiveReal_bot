import telegram
# Importamos las clases necesarias para el manejo asíncrono
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, error
import os
import json
import logging
from firebase_admin import credentials, initialize_app, firestore

# --- Configuración de Logging ---
# Configuración que permite ver todos los mensajes de diagnóstico en Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 1. Carga de Variables de Entorno ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS")

# --- 2. Validación de Credenciales Críticas ---
if not TELEGRAM_TOKEN:
    logger.critical("ERROR CRÍTICO: Falta TELEGRAM_TOKEN. El bot NO SE INICIARÁ.")
    exit(1)
if not FIREBASE_CREDENTIALS_JSON:
    logger.critical("ERROR CRÍTICO: FIREBASE_CREDENTIALS no está configurada. La base de datos no funcionará.")
    exit(1)


# --- 3. Inicialización de Firebase (Estabilización de Conexión) ---
db = None
try:
    creds_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
    cred = credentials.Certificate(creds_dict)
    
    # Usamos un nombre de aplicación para asegurar la inicialización correcta en ambientes como Render
    initialize_app(cred, name='TheOneHiveApp') 
    db = firestore.client()
    logger.info("CONEXIÓN A FIRESTORE EXITOSA.")
    
except Exception as e:
    # Capturamos errores de JSON o credenciales malformadas
    logger.error(f"ERROR DE CONEXIÓN A FIREBASE: Falló la inicialización. Detalle: {e}")
    # Permitimos que el bot inicie, pero con funcionalidad limitada (sin guardar datos)
    pass

# --- 4. Funciones de Ayuda y Administración ---

try:
    ADMIN_USER_ID = int(ADMIN_USER_ID)
except (TypeError, ValueError):
    ADMIN_USER_ID = 0
    logger.warning("ADMIN_USER_ID no es un número válido. La función de administrador no funcionará.")


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


# --- 6. Funciones de Manejadores (Handlers) ---

# CRUCIAL: Las funciones deben ser asíncronas (async) y usar await
async def start_command(update: Update, context):
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
    try:
        await update.message.reply_text( # Uso reply_text en lugar de send_message para simplificar
            text=message_text,
            reply_markup=get_keyboard(user_id)
        )
    except error.TelegramError as e:
        logger.error(f"Error al enviar /start: {e}")


# CRUCIAL: La función debe ser asíncrona (async) y usar await
async def handle_message(update: Update, context):
    """Maneja todos los mensajes de texto del usuario."""
    
    # Comprobación de seguridad: Si no hay mensaje de texto, salimos.
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    user_id = update.effective_user.id
    
    response_text = "Opción no reconocida. Por favor, selecciona un botón del menú."

    # Lógica de 5 Vías de Ingreso (Solo para el Admin)
    if "5 Vías de Ingreso" in text and is_admin(user_id):
        response_text = (
            "ADMIN: Este es el menú de 5 Vías de Ingreso para administrar el negocio.\n\n"
            "Aquí puedes gestionar:\n"
            "- Vía 1: Venta de Licencias (GOLD Premium)\n"
            "- Vía 2: Venta de Cursos/Ebooks (Marketplace)\n"
            "- Vía 3: Recompensa por Actividad (Tokens HVE)\n"
            "- Vía 4: Bono por Privacidad\n"
            "- Vía 5: Reto Viral (Marketing)\n\n"
            "Este mensaje es de uso interno."
        )
    elif "5 Vías de Ingreso" in text and not is_admin(user_id):
        response_text = "Opción no disponible. Por favor, selecciona una de las opciones del menú."
        
    # Lógica de Reto Viral
    elif "Reto Viral" in text:
        response_text = (
            "🚀 RETO VIRAL (GANANCIA GRATUITA DE TOKENS)\n\n"
            "Queremos ser la plataforma más grande. Ayúdanos a crecer y gana HVE Tokens extra!\n\n"
            "¿CÓMO FUNCIONA?\n"
            "1. Crea un video en TikTok, Instagram Reels o YouTube Shorts mostrando tu Racha Diaria o tu Proyección de Ganancia en el bot.\n"
            "2. Usa el hashtag #TheOneHiveApp.\n"
            "3. Envíanos el enlace por mensaje privado a este bot.\n\n"
            "🎁 Recompensa: 200 HVE Tokens por video aprobado. (Solo 1 video por usuario)"
        )
        
    # Respuestas para otros botones (Lógica pendiente de implementación)
    elif any(keyword in text for keyword in ["Mis Estadísticas", "Marketplace GOLD", "GOLD Premium", "Privacidad y Datos"]):
        response_text = f"Opción seleccionada: {text}. Esta función se implementará con la base de datos activa."
    
    # Enviar la respuesta
    try:
        await update.message.reply_text(response_text)
    except error.TelegramError as e:
        logger.error(f"Error al enviar mensaje: {e}")


# --- 7. Función Principal de Arranque ---

def main():
    """Función de inicio del bot."""
    
    if not TELEGRAM_TOKEN:
        logger.error("Token de Telegram no encontrado. Saliendo.")
        return

    # 1. Creamos la Aplicación con la sintaxis moderna (Application)
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
    except error.InvalidToken:
        logger.critical("ERROR - El TELEGRAM_TOKEN no es válido. Saliendo.")
        return

    # 2. Registramos Handlers (Con sintaxis de filtros corregida)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. Inicia el bot (Polling)
    logger.info("Bot TheOneHive listo. Iniciando Polling...")
    application.run_polling(poll_interval=0.5) # Usamos poll_interval para mejor respuesta
    
    logger.info("El bot se ha detenido.")

if __name__ == '__main__':
    main()
