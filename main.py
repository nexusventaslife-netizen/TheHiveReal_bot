import os
import telegram
import time
import json
# Importación correcta de clases para Python Telegram Bot 20.0
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# --- DEPENDENCIAS DE FIREBASE ---
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_IMPORTED = True
except ImportError:
    # Si falta firebase-admin en requirements.txt, esta variable será False
    FIREBASE_IMPORTED = False

# Diccionario global para el Throttling (Seguridad)
THROTTLE_LIMITS = {}
THROTTLE_TIME_SECONDS = 5 

# Variables globales
BOT_USERNAME = None 
db = None 
DB_ENABLED = False 

# --- CLAVES SECRETAS ---
# Las variables de entorno de Render se cargan aquí
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
HONEYGAIN_CODE = os.environ.get('HONEYGAIN_CODE')
PAWNS_CODE = os.environ.get('PAWNS_CODE')
SWAGBUCKS_CODE = os.environ.get('SWAGBUCKS_CODE')
FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS') 
ADMIN_CONTACT_URL = os.environ.get('ADMIN_CONTACT_URL', 'https://t.me/admin_example') # URL del admin para Premium
SURVEYJUNKIE_LINK = os.environ.get('SURVEYJUNKIE_LINK')
CLICKWORKER_LINK = os.environ.get('CLICKWORKER_LINK')

# --- LINKS Y DESCRIPCIONES (FALLBACK SEGURO) ---
# Se usan fallbacks si las variables no están configuradas (evita que el bot falle al iniciar)
LINKS = {
    'Honeygain': f'https://r.honeygain.me/THEHIVE{HONEYGAIN_CODE or "CODE_HG"}',
    'Pawns App': f'https://pawns.app/?r={PAWNS_CODE or "CODE_PAWNS"}',
    'Swagbucks': f'https://www.swagbucks.com/?r={SWAGBUCKS_CODE or "CODE_SB"}',
    'Survey Junkie': SURVEYJUNKIE_LINK or 'https://example.com/surveyjunkie',
    'Clickworker': CLICKWORKER_LINK or 'https://example.com/clickworker',
}

SERVICE_DESCRIPTIONS = {
    'Honeygain': "Ingreso Pasivo (Datos).",
    'Pawns App': "Ingreso Pasivo (Datos + Encuestas).",
    'Swagbucks': "Recompensas (Compras, Vídeos y Búsqueda).",
    'Survey Junkie': "Encuestas de Alta Paga ($).",
    'Clickworker': "Microtareas y Traducción (Alto Pago por Tarea).",
}

# --- FUNCIONES DE BASE DE DATOS (FASE 1: PERSISTENCIA) ---

def initialize_firebase():
    """Inicializa Firebase usando las credenciales secretas."""
    global db, DB_ENABLED
    
    if not FIREBASE_IMPORTED:
        return
        
    if not FIREBASE_CREDENTIALS:
        print("🟡 ADVERTENCIA: La variable 'FIREBASE_CREDENTIALS' no está configurada.")
        return

    try:
        # Intenta parsear el JSON de credenciales
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_dict)
        
        # Solo inicializar si no está ya inicializado
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        DB_ENABLED = True
        print("🟢 Firestore inicializado correctamente.")
    except Exception as e:
        print(f"🔴 ERROR al inicializar Firestore. Verifica el JSON: {e}")
        DB_ENABLED = False

async def get_user_data(user_id: int):
    """Obtiene los datos del usuario o crea un nuevo registro."""
    if not DB_ENABLED:
        # Fallback si la DB está deshabilitada
        return {'referrals': 0, 'points': 0, 'level': 'Bronze', 'is_premium': False}

    try:
        doc_ref = db.collection('users').document(str(user_id))
        doc = doc_ref.get()

        if doc.exists:
            # Usuario existente
            data = doc.to_dict()
            # Asegurar que tiene la clave is_premium 
            if 'is_premium' not in data:
                 data['is_premium'] = False
                 doc_ref.update({'is_premium': False})
            return data
        else:
            # Nuevo usuario
            initial_data = {
                'id': user_id,
                'referrals': 0,
                'points': 0, 
                'level': 'Bronze',
                'is_premium': False, # Nueva clave Premium
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
    
    # Determinar el origen del mensaje
    message_source = update.callback_query.message if update.callback_query else update.message
    if not message_source: return

    user_id = update.effective_user.id
    current_time = time.time()

    # Throttling (Seguridad)
    if user_id in THROTTLE_LIMITS and (current_time - THROTTLE_LIMITS[user_id] < THROTTLE_TIME_SECONDS):
        return
    THROTTLE_LIMITS[user_id] = current_time

    # Lógica de Gamificación (Integración con DB)
    user_data = await get_user_data(user_id)
    
    # Determinar el estado y el nivel para el mensaje
    premium_status = "GOLD" if user_data.get('is_premium') else "Bronze"
    premium_emoji = "⭐️" if user_data.get('is_premium') else "🟡"
    
    gamification_text = ""
    if DB_ENABLED:
        gamification_text = (
            f"\n🔥 **Tu Colmena Stats** 🔥\n"
            f"▪️ Referidos: {user_data.get('referrals', 0)}\n"
            f"▪️ Puntos: {user_data.get('points', 0)}\n"
            f"▪️ Nivel: {premium_emoji} **{premium_status}**\n"
        )
    else:
        gamification_text = "\n⚠️ *La persistencia (puntos/niveles) está deshabilitada. ¡Configura Firebase!*"


    # Contenido del mensaje
    message = (
        "👑 **BIENVENIDO A THE ONEHIVE!** 👑\n\n"
        "Genera ingresos pasivos y activos con nuestras **5 Vías de Ingreso** probadas.\n"
        
        f"{gamification_text}\n" 
        
        "**— 5 VÍAS DE INGRESO —**\n"
        f"▪️ *Honeygain:* {SERVICE_DESCRIPTIONS['Honeygain']}\n"
        f"▪️ *Pawns App:* {SERVICE_DESCRIPTIONS['Pawns App']}\n"
        f"▪️ *Swagbucks:* {SERVICE_DESCRIPTIONS['Swagbucks']}\n"
        f"▪️ *Survey Junkie:* {SERVICE_DESCRIPTIONS['Survey Junkie']}\n"
        f"▪️ *Clickworker:* {SERVICE_DESCRIPTIONS['Clickworker']}\n\n"
        
        "**— MONETIZACIÓN PREMIUM —**\n"
        "¿Quieres ganar $25-$50 diarios? Nuestro canal GOLD te da acceso a tareas mucho más rentables."
    )
    
    # Crear los botones
    keyboard = [
        [InlineKeyboardButton("🍯 Honeygain", url=LINKS['Honeygain']),
         InlineKeyboardButton("🐾 Pawns App", url=LINKS['Pawns App'])],
        [InlineKeyboardButton("💵 Swagbucks", url=LINKS['Swagbucks']),
         InlineKeyboardButton("📈 Survey Junkie", url=LINKS['Survey Junkie'])],
        [InlineKeyboardButton("✍️ Clickworker", url=LINKS['Clickworker']),
         InlineKeyboardButton("❓ Preguntas Frecuentes", callback_data='faq')],
        # Botón Premium/Viralidad
        [InlineKeyboardButton("🚀 ¡Acceso GOLD Tareas Altas!", callback_data='premium')],
        [InlineKeyboardButton("🔗 ¡Invita a la Colmena!", switch_inline_query=BOT_USERNAME or "")] 
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de respuesta (maneja /start, /links y 'menu' callback)
    if update.callback_query:
        await update.callback_query.answer()
        await message_source.edit_text(message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    else:
        await message_source.reply_text(message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de marketing para el servicio premium."""
    premium_message = (
        "👑 **ACCESO GOLD EXCLUSIVO** 👑\n\n"
        "¡Deja de perder el tiempo con micro-centavos! Nuestro canal GOLD te ofrece:\n"
        "✅ **Tareas Rentables:** Tareas exclusivas con pagos de $25 a $50 diarios.\n"
        "✅ **Asistencia 1:1:** Soporte directo con nuestro equipo de expertos.\n"
        "✅ **Potencial Ilimitado:** Si eres experto, ¡puedes ganar mucho más!\n\n"
        "**El futuro es ahora.** ¡Únete al GOLD y escala tus ingresos!\n\n"
        "🔗 **Para acceder, contacta al administrador ahora mismo:**"
    )
    
    # El enlace usa la variable de entorno ADMIN_CONTACT_URL
    keyboard = [[InlineKeyboardButton("💰 Contactar Admin para GOLD", url=ADMIN_CONTACT_URL)]] 
    keyboard.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data='menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(premium_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(premium_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función de Ayuda y Preguntas Frecuentes."""
    faq_message = (
        "📚 **PREGUNTAS FRECUENTES (FAQ)** 📚\n\n"
        "**1. ¿Qué hago si un enlace no funciona?**\n"
        "R: Simplemente cópialo completo, incluyendo 'https://'.\n\n"
        "**2. ¿Cómo gano puntos?**\n"
        "R: Por cada amigo que invites (referido) y por completar retos diarios que anunciamos.\n\n"
        "**3. ¿Es seguro usar estas apps?**\n"
        "R: Sí. Todas las apps son seguras y solo piden compartir ancho de banda o completar tareas."
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
        await send_links_menu(update, context)
    elif query.data == 'premium':
        await premium_command(update, context)
        
        
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await faq_command(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando o un callback."""
    pass

async def post_init(application: Application):
    """Se ejecuta después de que el bot se conecta correctamente a Telegram."""
    global BOT_USERNAME
    try:
        me = await application.bot.get_me()
        BOT_USERNAME = me.username
        print(f"Bot Username detectado: @{BOT_USERNAME}")
    except Exception as e:
        print(f"🔴 ERROR: No se pudo obtener el nombre de usuario del bot. Verifica TELEGRAM_TOKEN. Error: {e}")
        BOT_USERNAME = "TheOneHive_bot" # Fallback

def main():
    """Inicia el bot y lo mantiene escuchando (Polling)."""
    
    # 1. Verificación de claves esenciales
    if not TELEGRAM_TOKEN:
        print("🔴 ERROR CRÍTICO: La variable 'TELEGRAM_TOKEN' no está configurada.")
        exit(1)
    
    # 2. Inicializar Firestore (si las dependencias están)
    if FIREBASE_IMPORTED:
        initialize_firebase()
    
    # 3. Iniciar la aplicación de Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # 4. Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("links", links_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot listo. Iniciando Polling...")
    
    # 5. Corrección de Indentación: el try debe tener un bloque indentado
    try:
        application.run_polling(poll_interval=5.0)
    except telegram.error.Conflict:
        print("🔴 ERROR DE CONFLICTO: Ya hay otra instancia del bot ejecutándose. ¡Debes generar un nuevo TOKEN!")
    except Exception as e:
        print(f"🔴 ERROR FATAL EN EL POLLING: {e}")


if __name__ == '__main__':
    main()
