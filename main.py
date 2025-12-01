import os
import telegram
import time
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# --- DEPENDENCIAS DE FIREBASE ---
# Se verifica la instalación de la librería 'firebase-admin'.
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_IMPORTED = True
except ImportError:
    # Este error ocurre si 'firebase-admin' no está en requirements.txt
    FIREBASE_IMPORTED = False
    print("🔴 ADVERTENCIA: La librería 'firebase-admin' no está instalada. La persistencia estará DESHABILITADA.")


# Diccionario global para el Throttling (Seguridad)
THROTTLE_LIMITS = {}
THROTTLE_TIME_SECONDS = 5 

# Variable para almacenar el nombre de usuario del bot (inicializada a None)
BOT_USERNAME = None 

# Variables de Base de Datos
db = None # Instancia de Firestore
DB_ENABLED = False # Flag para saber si la DB está activa

# --- CLAVES SECRETAS ---
# Estas claves se cargan desde las variables de entorno de Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
HONEYGAIN_CODE = os.environ.get('HONEYGAIN_CODE')
PAWNS_CODE = os.environ.get('PAWNS_CODE')
SWAGBUCKS_CODE = os.environ.get('SWAGBUCKS_CODE')
FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS') 

# --- LINKS Y DESCRIPCIONES ---
LINKS = {
    'Honeygain': f'https://r.honeygain.me/THEHIVE{HONEYGAIN_CODE}',
    'Pawns App': f'https://pawns.app/?r={PAWNS_CODE}',
    'Swagbucks': f'https://www.swagbucks.com/?r={SWAGBUCKS_CODE}'
}

SERVICE_DESCRIPTIONS = {
    'Honeygain': "Te permite ganar ingresos pasivos compartiendo tu conexión a internet.",
    'Pawns App': "Similar a Honeygain, te paga por compartir ancho de banda y completar encuestas.",
    'Swagbucks': "Gana recompensas y dinero en efectivo por comprar, ver videos y responder encuestas."
}

# --- FUNCIONES DE BASE DE DATOS (FASE 1: PERSISTENCIA) ---

def initialize_firebase():
    """Inicializa Firebase usando las credenciales secretas."""
    global db, DB_ENABLED
    
    # 1. Verificar la importación y la clave
    if not FIREBASE_IMPORTED:
        return
        
    if not FIREBASE_CREDENTIALS:
        print("🟡 ADVERTENCIA: La variable 'FIREBASE_CREDENTIALS' no está configurada. Persistencia deshabilitada.")
        return

    try:
        # 2. Cargar las credenciales del JSON (requerido para la autenticación en Render)
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        
        # 3. Inicializar la aplicación de Firebase
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        
        # 4. Obtener el cliente de Firestore
        db = firestore.client()
        DB_ENABLED = True
        print("🟢 Firestore inicializado correctamente. Persistencia habilitada.")
    except Exception as e:
        print(f"🔴 ERROR al inicializar Firestore. Verifica el JSON: {e}")
        DB_ENABLED = False

async def get_user_data(user_id):
    """
    Obtiene los datos del usuario de Firestore o crea un nuevo registro con valores iniciales.
    Retorna los datos del usuario (dict) o un fallback dict si hay error.
    """
    # Retorna un fallback si la DB no está activa
    if not DB_ENABLED:
        return {'referrals': 0, 'points': 0, 'level': 'N/A', 'streak': 0}

    try:
        # Usar el ID del usuario como el ID del documento
        doc_ref = db.collection('users').document(str(user_id))
        doc = doc_ref.get()

        if doc.exists:
            # Usuario existente: retorna sus datos
            return doc.to_dict()
        else:
            # Nuevo usuario: crea el registro inicial para gamificación
            initial_data = {
                'id': user_id,
                'referrals': 0,
                'points': 0, 
                'level': 'Bronze',
                'streak': 0,
                'last_active': time.time()
            }
            doc_ref.set(initial_data)
            return initial_data
            
    except Exception as e:
        print(f"🔴 ERROR de Firestore al obtener/crear usuario {user_id}: {e}")
        # Fallback en caso de fallo de DB durante la ejecución
        return {'referrals': 0, 'points': 0, 'level': 'N/A', 'streak': 0} 


# --- FUNCIONES CENTRALES ---

async def send_links_menu(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Envía el menú de enlaces con Throttling y datos de usuario."""
    
    # Determinar el origen de la actualización (mensaje o callback)
    if update.callback_query:
        message_source = update.callback_query.message
        user_id = update.callback_query.from_user.id
    elif update.message:
        message_source = update.message
        user_id = update.effective_user.id
    else:
        # Ignorar si no es ni mensaje ni callback
        return

    current_time = time.time()

    # Throttling
    if user_id in THROTTLE_LIMITS and (current_time - THROTTLE_LIMITS[user_id] < THROTTLE_TIME_SECONDS):
        return
    THROTTLE_LIMITS[user_id] = current_time

    # Lógica de Gamificación (Integración con DB)
    user_data = await get_user_data(user_id)
    
    gamification_text = ""
    if DB_ENABLED:
        gamification_text = (
            f"\n🔥 **Tu Colmena Stats** 🔥\n"
            f"▪️ Referidos: {user_data.get('referrals', 0)}\n"
            f"▪️ Puntos: {user_data.get('points', 0)}\n"
            f"▪️ Nivel: {user_data.get('level', 'Bronze')}\n"
        )
    else:
        # Advertencia si la DB no está activa
        gamification_text = "\n⚠️ *La persistencia (puntos/niveles) está deshabilitada. ¡Configura Firestore!*"


    # Contenido del mensaje (Mejora de diseño y enganche)
    message = (
        "👑 **BIENVENIDO A LA COLMENA REAL (THE HIVE)!** 👑\n\n"
        "Usa los enlaces de referido de nuestra comunidad para empezar a generar "
        "ingresos pasivos. ¡La forma más fácil de ganar dinero durmiendo!\n"
        
        f"{gamification_text}\n" # Insertar la información de gamificación
        
        "**— Servicios de Ingreso Pasivo —**\n"
        "▪️ *Honeygain:* {desc_hg}\n"
        "▪️ *Pawns App:* {desc_p}\n"
        "▪️ *Swagbucks:* {desc_s}\n"
    ).format(
        desc_hg=SERVICE_DESCRIPTIONS['Honeygain'],
        desc_p=SERVICE_DESCRIPTIONS['Pawns App'],
        desc_s=SERVICE_DESCRIPTIONS['Swagbucks']
    )
    
    # Crear los botones
    keyboard = [
        [InlineKeyboardButton("🍯 Honeygain", url=LINKS['Honeygain']),
         InlineKeyboardButton("🐾 Pawns App", url=LINKS['Pawns App'])],
        [InlineKeyboardButton("💵 Swagbucks", url=LINKS['Swagbucks']),
         InlineKeyboardButton("❓ Preguntas Frecuentes", callback_data='faq')],
        # Botón de Compartir: Usa el nombre de usuario global (BOT_USERNAME)
        [InlineKeyboardButton("🔗 ¡Invita a la Colmena!", switch_inline_query=BOT_USERNAME)] 
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        # Editar el mensaje si viene de un botón (para volver al menú)
        await message_source.edit_text(
            message,
            reply_markup=reply_markup,
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )
    else:
        # Responder con un nuevo mensaje si viene de un comando (/start, /links)
        await message_source.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )

async def faq_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Función de Ayuda y Preguntas Frecuentes."""
    faq_message = (
        "📚 **PREGUNTAS FRECUENTES (FAQ)** 📚\n\n"
        "**1. ¿Qué hago si un enlace no funciona?**\n"
        "R: Simplemente cópialo completo, incluyendo 'https://'.\n\n"
        "**2. ¿Es seguro usar estas apps?**\n"
        "R: Sí. Todas las apps son seguras y solo piden compartir ancho de banda.\n\n"
        "**3. ¿Cómo puedo apoyar más?**\n"
        f"R: Comparte este bot con un amigo usando el botón 'Invita a la Colmena!'."
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Determinar si la llamada viene de un callback o un comando
    if update.callback_query:
        # Si es callback (botón "Preguntas Frecuentes")
        await update.callback_query.message.edit_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    else:
        # Si es un comando (/ayuda)
        await update.message.reply_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def button_handler(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'faq':
        await faq_command(update, context)
    elif query.data == 'menu':
        # Volver al menú llama a send_links_menu para refrescar las estadísticas
        await send_links_menu(update, context)
        
        
async def start_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def links_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def help_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    await faq_command(update, context)


async def handle_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando o un callback."""
    pass

def main():
    """Inicia el bot y lo mantiene escuchando (Polling)."""
    global BOT_USERNAME
    
    # 1. Verificación de claves esenciales
    if not all([TELEGRAM_TOKEN, HONEYGAIN_CODE, PAWNS_CODE, SWAGBUCKS_CODE]):
        print("🔴 ERROR DE CLAVES: Una o más variables esenciales no están configuradas en Render.")
        exit(1)

    # 2. Inicializar Firestore 
    if FIREBASE_IMPORTED:
        initialize_firebase()
    
    # 3. Iniciar la aplicación de Telegram (Usando el patrón correcto para PTB 20.0)
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 4. Obtener el username del bot para la viralidad
    BOT_USERNAME = "@" + application.bot.username


    # 5. Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("links", links_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    # Mensajes de texto sin comandos
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot listo para iniciar la persistencia con Firestore.")
    application.run_polling(poll_interval=5.0)


if __name__ == '__main__':
    main()
