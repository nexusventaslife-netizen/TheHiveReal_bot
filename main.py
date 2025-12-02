# --- Importaciones ---
import os
import json
import logging
from http import HTTPStatus
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import telegram # Necesario para ReplyKeyboardMarkup

# Para Firebase
import firebase_admin
from firebase_admin import credentials, firestore

# --- Configuración de Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Variables Globales y Configuración CRÍTICA ---
# ESTAS VARIABLES SON REQUERIDAS POR RENDER
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS")

# ************** URL DE RENDER FORZADA EN EL CÓDIGO **************
# Ya que Render te muestra el nombre 'TheHiveReal_bot', la URL externa sigue la convención.
# NO CAMBIES ESTA LÍNEA A MENOS QUE HAYAS PUESTO OTRO NOMBRE AL SERVICIO WEB.
RENDER_EXTERNAL_URL_FORZADA = "https://the-hivereal-bot.onrender.com"
# ****************************************************************

# --- Funciones de Utilidad ---
def initialize_firebase():
    """Inicializa Firebase y Firestore, manejando el error de credenciales."""
    try:
        if not FIREBASE_CREDENTIALS_JSON:
            logger.error("FIREBASE_CREDENTIALS no está configurada. El bot no podrá guardar datos.")
            return None

        # Intenta cargar el JSON. Si falla, es un problema de formato.
        try:
            creds_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
        except json.JSONDecodeError as e:
            logger.error(f"ERROR DE FORMATO DE FIREBASE_CREDENTIALS: El JSON no es válido. {e}")
            return None

        # Inicialización segura
        cred = credentials.Certificate(creds_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            logger.info("CONEXIÓN A FIRESTORE EXITOSA. Los datos de usuarios se guardarán correctamente.")
        return firestore.client()

    except Exception as e:
        logger.error(f"ERROR FATAL DE INICIALIZACIÓN DE FIREBASE: {e}")
        return None

db = initialize_firebase()

# --- Handlers de Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start y muestra el menú."""
    user = update.effective_user
    is_admin = str(user.id) == ADMIN_USER_ID
    
    # Intenta obtener o crear el documento del usuario en Firestore
    if db:
        try:
            user_doc_ref = db.collection('users').document(str(user.id))
            user_data = user_doc_ref.get()
            
            if not user_data.exists:
                user_doc_ref.set({'first_name': user.first_name, 'username': user.username, 'status': 'FREE', 'tokens_hve': 5, 'admin': is_admin, 'created_at': firestore.SERVER_TIMESTAMP})
                logger.info(f"Nuevo usuario registrado: {user.id}")
            else:
                user_doc_ref.update({'first_name': user.first_name, 'username': user.username})

        except Exception as e:
            logger.error(f"Error al acceder a Firestore para el usuario {user.id}: {e}")

    # Respuesta del bot
    welcome_text = (
        f"¡Hola, {user.first_name}!\n\n"
        "Somos el 'Booster' global para que ganes ingresos pasivos y activos. Tu misión es simple: "
        "maximiza tu actividad y sube tu Racha Diaria."
    )
    
    keyboard = [
        ["5 Vías de Ingreso", "Mis Estadísticas (APD V2)"],
        ["Reto Viral (Gana HVE Tokens)", "Marketplace GOLD (Cursos/Libros)"],
        ["GOLD Premium ($15 USD)", "Privacidad y Datos (Bono HVE)"]
    ]
    
    if is_admin:
        keyboard.append(["🛠️ Panel Admin"])
        
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando del panel de administrador (solo visible para admin)."""
    user_id_str = str(update.effective_user.id)
    if user_id_str == ADMIN_USER_ID:
        await update.message.reply_text("👋 ¡Bienvenido al Panel de Administrador! ¿Qué acción deseas realizar hoy?",
                                        reply_markup=telegram.ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Acceso denegado. Este comando es solo para administradores.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto que no son comandos."""
    text = update.message.text
    response = "Has enviado: " + text
    
    # Aquí puedes añadir la lógica para responder a los botones del menú
    if text == "5 Vías de Ingreso":
        response = "Aquí están las 5 vías principales para generar ingresos..."
    elif text == "Reto Viral (Gana HVE Tokens)":
        response = (
            "🚀 RETO VIRAL (GANANCIA GRATUITA DE TOKENS)\n\n"
            "Queremos ser la plataforma más grande. Ayúdanos a crecer y gana HVE Tokens extra!\n\n"
            "¿CÓMO FUNCIONA?\n"
            "1. Crea un video en TikTok, Instagram Reels o YouTube Shorts mostrando tu Racha Diaria o tu Proyección de Ganancia en el bot.\n"
            "2. Usa el hashtag #TheOneHiveApp.\n"
            "3. Envíanos el enlace por mensaje privado a un administrador para que verifique tu video y acredite tus tokens."
        )
    elif text == "🛠️ Panel Admin" and str(update.effective_user.id) == ADMIN_USER_ID:
        response = "Acceso al Panel Admin confirmado."
    
    await update.message.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loggea los errores causados por las actualizaciones."""
    logger.warning('La actualización "%s" causó el error "%s"', update, context.error)

# --- Función Principal (Configuración de WebHook) ---

def main() -> None:
    """Inicia el bot con el modo WebHook, ideal para Render."""
    if not TELEGRAM_TOKEN:
        logger.error("ERROR - No se puede iniciar el bot. Falta TELEGRAM_TOKEN.")
        return

    # 1. Crear la aplicación (el bot)
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. Agregar Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # 3. Configuración del Servidor Web (Flask)
    app = Flask(__name__)

    # 4. Manejar la URL de Telegram (el WebHook)
    @app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
    def webhook_handler():
        """Recibe y procesa las actualizaciones enviadas por Telegram."""
        if request.method == "POST":
            update = Update.de_json(request.get_json(force=True), application.bot)
            application.process_update(update)
        return "ok", HTTPStatus.OK

    # 5. Configurar el WebHook en Telegram
    # NOTA: Usamos la variable forzada RENDER_EXTERNAL_URL_FORZADA
    webhook_url = f"{RENDER_EXTERNAL_URL_FORZADA}/{TELEGRAM_TOKEN}"
    
    try:
        application.bot.set_webhook(url=webhook_url)
        logger.info(f"WebHook configurado exitosamente: {webhook_url}")
    except Exception as e:
        logger.error(f"ERROR al configurar el WebHook. Telegram no está aceptando la URL ({webhook_url}). Asegúrate que el servicio de Render sea 'Web Service' y esté operativo. Error: {e}")
        return # Fallo al configurar el webhook

    # 6. Iniciar el Servidor Flask
    # Render usa la variable PORT. Si no existe, usa 8080.
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Servicio WebHook iniciado en el puerto {port}")
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()
