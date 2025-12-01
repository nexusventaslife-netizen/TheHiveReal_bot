import os
import telegram
import time
import json
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# --- DEPENDENCIAS DE FIREBASE ---
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_IMPORTED = True
except ImportError:
    FIREBASE_IMPORTED = False
    print("🔴 ADVERTENCIA: La librería 'firebase-admin' no está instalada. La persistencia estará DESHABILITADA.")


# Configuración global
THROTTLE_LIMITS = {}
THROTTLE_TIME_SECONDS = 5 
BOT_USERNAME = None 
db = None # Instancia de Firestore
DB_ENABLED = False 

# --- CLAVES SECRETAS ---
# Carga de variables de entorno (Render)
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
    
    if not FIREBASE_IMPORTED or not FIREBASE_CREDENTIALS:
        if not FIREBASE_CREDENTIALS:
            print("🟡 ADVERTENCIA: La variable 'FIREBASE_CREDENTIALS' no está configurada. Persistencia deshabilitada.")
        return

    try:
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        DB_ENABLED = True
        print("🟢 Firestore inicializado correctamente. Persistencia habilitada.")
    except Exception as e:
        print(f"🔴 ERROR al inicializar Firestore. Verifica el JSON: {e}")
        DB_ENABLED = False

async def get_user_data(user_id: int):
    """Obtiene los datos del usuario de Firestore o crea un nuevo registro."""
    if not DB_ENABLED:
        return {'referrals': 0, 'points': 0, 'level': 'N/A', 'streak': 0}

    try:
        doc_ref = db.collection('users').document(str(user_id))
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict()
        else:
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
        return {'referrals': 0, 'points': 0, 'level': 'N/A', 'streak': 0} 


# --- HANDLERS Y LÓGICA DE INTERFAZ ---

async def send_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el menú de enlaces con Throttling y datos de usuario."""
    
    # Obtener el origen y user_id
    if update.callback_query:
        message_source = update.callback_query.message
        user_id = update.callback_query.from_user.id
    elif update.message:
        message_source = update.message
        user_id = update.effective_user.id
    else:
        return

    current_time = time.time()

    # Throttling (Seguridad contra spam) - Aplica antes de la lógica pesada
    if user_id in THROTTLE_LIMITS and (current_time - THROTTLE_LIMITS[user_id] < THROTTLE_TIME_SECONDS):
        return
    THROTTLE_LIMITS[user_id] = current_time

    # Lógica de Gamificación (Integración con DB)
    user_data = await get_user_data(user_id) # Esta llamada es la más lenta
    
    gamification_text = ""
    if DB_ENABLED:
        gamification_text = (
            f"\n🔥 **Tu Colmena Stats** 🔥\n"
            f"▪️ Referidos: {user_data.get('referrals', 0)}\n"
            f"▪️ Puntos: {user_data.get('points', 0)}\n"
            f"▪️ Nivel: {user_data.get('level', 'Bronze')}\n"
        )
    else:
        gamification_text = "\n⚠️ *La persistencia (puntos/niveles) está deshabilitada. ¡Configura Firestore!*"


    # Contenido del mensaje (Texto actualizado)
    message = (
        "👑 **BIENVENIDO A ONEHIVE (THE HIVE)!** 👑\n\n" # Nombre del bot actualizado
        "Usa los enlaces de referido de nuestra comunidad para empezar a generar "
        "ingresos pasivos. ¡La forma más fácil de ganar dinero durmiendo!\n"
        
        f"{gamification_text}\n"
        
        "**— Servicios de Ingreso Pasivo —**\n"
        "▪️ *Honeygain:* {desc_hg}\n"
        "▪️ *Pawns App:* {desc_p}\n"
        "▪️ *Swagbucks:* {desc_s}\n"
    ).format(
        desc_hg=SERVICE_DESCRIPTIONS['Honeygain'],
        desc_p=SERVICE_DESCRIPTIONS['Pawns App'],
        desc_s=SERVICE_DESCRIPTIONS['Swagbucks']
    )
    
    # Crear los botones. Se usa BOT_USERNAME que es global.
    keyboard = [
        [InlineKeyboardButton("🍯 Honeygain", url=LINKS['Honeygain']),
         InlineKeyboardButton("🐾 Pawns App", url=LINKS['Pawns App'])],
        [InlineKeyboardButton("💵 Swagbucks", url=LINKS['Swagbucks']),
         InlineKeyboardButton("❓ Preguntas Frecuentes", callback_data='faq')],
        # Este botón usa el BOT_USERNAME obtenido asíncronamente
        [InlineKeyboardButton("🔗 ¡Invita a la Colmena!", switch_inline_query=BOT_USERNAME)] 
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await message_source.edit_text(
            message,
            reply_markup=reply_markup,
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )
    else:
        await message_source.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == 'faq':
        await faq_command(update, context)
    elif query.data == 'menu':
        # Al volver al menú se llama a send_links_menu para refrescar las estadísticas del usuario
        await send_links_menu(update, context)
        
        
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await faq_command(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando o un callback."""
    pass

# La función principal ahora es asíncrona para manejar correctamente el bot de Telegram
async def main():
    """Inicia el bot y lo mantiene escuchando (Polling)."""
    global BOT_USERNAME
    
    # 1. Verificación de claves esenciales
    if not all([TELEGRAM_TOKEN, HONEYGAIN_CODE, PAWNS_CODE, SWAGBUCKS_CODE]):
        print("🔴 ERROR DE CLAVES: Una o más variables esenciales (TOKENS/CÓDIGOS) no están configuradas en Render.")
        exit(1)

    # 2. Inicializar Firestore 
    if FIREBASE_IMPORTED:
        initialize_firebase()
    
    # 3. Iniciar la aplicación de Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 4. Obtener el username del bot de forma ASÍNCRONA y segura
    try:
        # get_me() inicializa el bot y obtiene sus datos
        bot_info = await application.bot.get_me() 
        BOT_USERNAME = bot_info.username
        print(f"🟢 Bot Username detectado: @{BOT_USERNAME}")
    except telegram.error.InvalidToken:
        print("🔴 ERROR CRÍTICO: El TELEGRAM_TOKEN no es válido. La instancia fallará.")
        exit(1)
    except Exception as e:
        print(f"🔴 ERROR: No se pudo obtener el nombre de usuario del bot. Error: {e}")
        BOT_USERNAME = "TheOneHive_bot" # Fallback, usando el nombre que proporcionaste

    # 5. Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("links", links_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    # Mensajes de texto sin comandos
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot listo. Iniciando Polling...")
    await application.run_polling(poll_interval=5.0)


if __name__ == '__main__':
    # Esta línea ejecuta la función asíncrona 'main'
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido manualmente.")
    except Exception as e:
        print(f"Ocurrió un error inesperado al ejecutar main: {e}")
