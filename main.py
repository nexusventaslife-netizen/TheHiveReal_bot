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
FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS') 

# Variables de Plataformas (Se utiliza un fallback si no están configuradas)
HONEYGAIN_CODE = os.environ.get('HONEYGAIN_CODE', 'YOUR_HG_CODE')
PAWNS_CODE = os.environ.get('PAWNS_CODE', 'YOUR_PAWNS_CODE')
SWAGBUCKS_CODE = os.environ.get('SWAGBUCKS_CODE', 'YOUR_SB_CODE')
SURVEYJUNKIE_LINK = os.environ.get('SURVEYJUNKIE_LINK', 'https://surveyjunkie.link/example')
CLICKWORKER_LINK = os.environ.get('CLICKWORKER_LINK', 'https://clickworker.link/example')
ADMIN_CONTACT_URL = os.environ.get('ADMIN_CONTACT_URL', 'https://t.me/TheHiveAdmin') # Nuevo link para el admin

# --- LINKS Y DESCRIPCIONES (5 VÍAS DE INGRESO) ---
LINKS = {
    # 1. Ingreso Pasivo
    'Honeygain': f'https://r.honeygain.me/THEHIVE{HONEYGAIN_CODE}',
    'Pawns App': f'https://pawns.app/?r={PAWNS_CODE}',
    # 3. Encuestas de Alta Paga
    'Survey Junkie': SURVEYJUNKIE_LINK,
    # 4. Microtareas de Reputación
    'Clickworker': CLICKWORKER_LINK,
    # 5. Recompensas/Vídeos
    'Swagbucks': f'https://www.swagbucks.com/?r={SWAGBUCKS_CODE}'
}

SERVICE_DESCRIPTIONS = {
    'Honeygain': "Ganancia pasiva compartiendo ancho de banda. Ideal para empezar.",
    'Pawns App': "Alternativa robusta a Honeygain. Más ancho de banda = más ingreso.",
    'Survey Junkie': "Encuestas con alta tasa de pago y reputación. Enfocado en rentabilidad.",
    'Clickworker': "Microtareas (traducción, clasificación, QA) con pago constante.",
    'Swagbucks': "Gana por compras, ver videos y búsquedas. Un ingreso extra fácil."
}

# --- FUNCIONES DE BASE DE DATOS (FASE 1: PERSISTENCIA) ---

def initialize_firebase():
    """Inicializa Firebase usando las credenciales secretas."""
    global db, DB_ENABLED
    
    if not FIREBASE_IMPORTED:
        return
        
    if not FIREBASE_CREDENTIALS:
        print("🟡 ADVERTENCIA: La variable 'FIREBASE_CREDENTIALS' no está configurada. Persistencia deshabilitada.")
        return

    try:
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_dict)
        
        # Prevenir la inicialización múltiple
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            
        db = firestore.client()
        DB_ENABLED = True
        print("🟢 Firestore inicializado correctamente. Persistencia habilitada.")
    except Exception as e:
        print(f"🔴 ERROR al inicializar Firestore. Verifica el JSON: {e}")
        DB_ENABLED = False

async def get_user_data(user_id: int):
    """Obtiene los datos del usuario o crea un nuevo registro con valores iniciales."""
    # Retorna un fallback si la DB no está activa
    if not DB_ENABLED:
        return {'referrals': 0, 'points': 0, 'level': 'N/A', 'is_premium': False}

    try:
        doc_ref = db.collection('users').document(str(user_id))
        doc = doc_ref.get()

        if doc.exists:
            # Usuario existente
            return doc.to_dict()
        else:
            # Nuevo usuario: crea el registro inicial para gamificación
            initial_data = {
                'id': user_id,
                'referrals': 0,
                'points': 0, 
                'level': 'Bronze Bee', # Nombre más temático
                'is_premium': False, # Nuevo campo para la suscripción
                'last_active': time.time()
            }
            doc_ref.set(initial_data)
            return initial_data
            
    except Exception as e:
        print(f"🔴 ERROR de Firestore al obtener/crear usuario {user_id}: {e}")
        return {'referrals': 0, 'points': 0, 'level': 'N/A', 'is_premium': False} 


# --- FUNCIONES CENTRALES ---

async def send_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el menú de enlaces con Throttling y datos de usuario."""
    
    # Manejar el origen del mensaje (callback o comando)
    if update.callback_query:
        message_source = update.callback_query.message
        user_id = update.callback_query.from_user.id
    elif update.message:
        message_source = update.message
        user_id = update.effective_user.id
    else:
        return

    current_time = time.time()

    # Throttling
    if user_id in THROTTLE_LIMITS and (current_time - THROTTLE_LIMITS[user_id] < THROTTLE_TIME_SECONDS):
        return
    THROTTLE_LIMITS[user_id] = current_time

    # Obtener los datos del usuario (Lectura inicial)
    user_data = await get_user_data(user_id)
    
    premium_status = "✅ ACTIVO" if user_data.get('is_premium') else "❌ INACTIVO"
    
    gamification_text = ""
    if DB_ENABLED:
        gamification_text = (
            f"\n🔥 **Tu Colmena Stats** 🔥\n"
            f"▪️ Referidos: {user_data.get('referrals', 0)}\n"
            f"▪️ Puntos: {user_data.get('points', 0)}\n"
            f"▪️ Nivel: {user_data.get('level', 'Bronze Bee')} (Premium: {premium_status})\n"
        )
    else:
        gamification_text = "\n⚠️ *La persistencia (puntos/niveles) está deshabilitada. ¡Configura Firestore!*"


    # Contenido del mensaje: ¡Aumento de Enganche!
    message = (
        "👑 **BIENVENIDO A THE ONE HIVE!** 👑\n\n"
        "¡Tu misión es generar ingresos pasivos y dominar la colmena! "
        "Usa los enlaces de la comunidad para empezar a ganar hoy mismo.\n"
        
        f"{gamification_text}\n" 
        
        "**— Las 5 Vías de Ingreso de Alta Rentabilidad —**\n"
        f"▪️ *{list(SERVICE_DESCRIPTIONS.keys())[0]}:* {SERVICE_DESCRIPTIONS['Honeygain']}\n"
        f"▪️ *{list(SERVICE_DESCRIPTIONS.keys())[1]}:* {SERVICE_DESCRIPTIONS['Pawns App']}\n"
        f"▪️ *{list(SERVICE_DESCRIPTIONS.keys())[2]}:* {SERVICE_DESCRIPTIONS['Survey Junkie']}\n"
        f"▪️ *{list(SERVICE_DESCRIPTIONS.keys())[3]}:* {SERVICE_DESCRIPTIONS['Clickworker']}\n"
        f"▪️ *{list(SERVICE_DESCRIPTIONS.keys())[4]}:* {SERVICE_DESCRIPTIONS['Swagbucks']}\n"
        
        "\n🚀 **¿QUIERES GANAR $25-$50 DIARIOS?** Presiona 'Acceso Premium' para desbloquear tareas de MÁXIMA PAGA."
    )
    
    # Crear los botones para las 5 vías de ingreso + Premium
    keyboard = [
        # Fila 1: Pasivo
        [InlineKeyboardButton("🍯 Honeygain", url=LINKS['Honeygain']),
         InlineKeyboardButton("🐾 Pawns App", url=LINKS['Pawns App'])],
        # Fila 2: Tareas y Encuestas
        [InlineKeyboardButton("📊 Survey Junkie", url=LINKS['Survey Junkie']),
         InlineKeyboardButton("🏗️ Clickworker", url=LINKS['Clickworker'])],
        # Fila 3: Recompensas y Premium
        [InlineKeyboardButton("💵 Swagbucks", url=LINKS['Swagbucks']),
         InlineKeyboardButton("🚀 ¡Acceso Premium!", callback_data='premium')],
        # Fila 4: Ayuda y Viralidad
        [InlineKeyboardButton("❓ Ayuda/FAQ", callback_data='faq'),
         InlineKeyboardButton("🔗 ¡Invita a la Colmena!", switch_inline_query=BOT_USERNAME)] 
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


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de marketing para la suscripción Premium."""
    
    premium_message = (
        "👑 **NIVEL GOLD (PREMIUM ACCESS)** 👑\n\n"
        "¡Deja de buscar tareas! Con Gold, garantizamos acceso a tareas exclusivas "
        "con una rentabilidad de **$25 a $50 diarios** o más para usuarios avanzados.\n\n"
        
        "**Incluye:**\n"
        "🔹 Acceso a listas de tareas de alta remuneración (MT, QA, Análisis).\n"
        "🔹 Soporte 1:1 para optimizar tu tiempo.\n"
        "🔹 Estrategias probadas para maximizar el ingreso pasivo.\n\n"
        
        "Para adquirir la suscripción y empezar a ganar más, contacta al administrador."
    )
    
    # El botón usa la variable de entorno ADMIN_CONTACT_URL
    keyboard = [[InlineKeyboardButton("💰 Contactar Admin para Gold", url=ADMIN_CONTACT_URL)]]
    keyboard.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data='menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.answer()
    await update.callback_query.message.edit_text(premium_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función de Ayuda y Preguntas Frecuentes."""
    faq_message = (
        "📚 **PREGUNTAS FRECUENTES (FAQ)** 📚\n\n"
        "**1. ¿Cómo funciona la Colmena (The Hive)?**\n"
        "R: Te proporcionamos los enlaces de referido a las mejores apps para generar ingreso pasivo (compartir ancho de banda) y activo (encuestas, microtareas).\n\n"
        "**2. ¿Es seguro usar estas apps?**\n"
        "R: Sí. Todas son plataformas verificadas y solo piden compartir ancho de banda o completar tareas.\n\n"
        "**3. ¿Cómo subo de Nivel?**\n"
        f"R: Ganando puntos por referir nuevos usuarios. ¡Usa el botón 'Invita a la Colmena!'."
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
    elif query.data == 'premium':
        await premium_command(update, context)
    elif query.data == 'menu':
        # Volver al menú refresca las estadísticas del usuario
        await send_links_menu(update, context)
        
        
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Llama a faq_command que tiene la lógica de respuesta para comandos
    await faq_command(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando o un callback."""
    pass

async def main():
    """Inicia el bot y lo mantiene escuchando (Polling)."""
    global BOT_USERNAME
    
    # 1. Verificar el Token de Telegram
    if not TELEGRAM_TOKEN:
        print("🔴 ERROR CRÍTICO: La variable TELEGRAM_TOKEN no está configurada. El bot no puede iniciar.")
        return

    # 2. Inicializar Firestore (La inicialización es robusta y no detiene el bot)
    if FIREBASE_IMPORTED:
        initialize_firebase()
    
    # 3. Iniciar la aplicación de Telegram
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # 4. Obtener el username del bot de forma asíncrona (NECESARIO)
        bot_info = await application.bot.get_me()
        BOT_USERNAME = "@" + bot_info.username
        print(f"🟢 CONEXIÓN EXITOSA. Bot Username: {BOT_USERNAME}")
    except telegram.error.InvalidToken:
        print("🔴 ERROR CRÍTICO: El TELEGRAM_TOKEN no es válido. ¡DEBE SER CAMBIADO!")
        return
    except Exception as e:
        print(f"🔴 ERROR INESPERADO al conectar con Telegram: {e}")
        return

    # 5. Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("links", links_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot TheOneHive listo. Iniciando Polling...")
    await application.run_polling(poll_interval=5.0)


if __name__ == '__main__':
    try:
        # Ejecutar la función main asíncrona
        asyncio.run(main())
    except Exception as e:
        print(f"Ocurrió un error inesperado al ejecutar main (ASÍNC.): {e}")
