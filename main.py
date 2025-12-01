Import os
import telegram
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Diccionario global para el Throttling (Seguridad)
THROTTLE_LIMITS = {}
THROTTLE_TIME_SECONDS = 5 

# Variable para almacenar el nombre de usuario del bot (inicializada a None)
BOT_USERNAME = None 

# --- CLAVES SECRETAS ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
HONEYGAIN_CODE = os.environ.get('HONEYGAIN_CODE')
PAWNS_CODE = os.environ.get('PAWNS_CODE')
SWAGBUCKS_CODE = os.environ.get('SWAGBUCKS_CODE')

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


# --- FUNCIONES CENTRALES ---

async def send_links_menu(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Envía el menú de enlaces con Throttling."""
    
    user_id = update.effective_user.id
    current_time = time.time()

    # Throttling
    if user_id in THROTTLE_LIMITS and (current_time - THROTTLE_LIMITS[user_id] < THROTTLE_TIME_SECONDS):
        return
    THROTTLE_LIMITS[user_id] = current_time

    # Contenido del mensaje (Mejora de diseño y enganche)
    message = (
        "👑 **BIENVENIDO A LA COLMENA REAL (THE HIVE)!** 👑\n\n"
        "Usa los enlaces de referido de nuestra comunidad para empezar a generar "
        "ingresos pasivos. ¡La forma más fácil de ganar dinero durmiendo!\n\n"
        
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

    await update.message.reply_text(
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

    if update.callback_query:
        await update.callback_query.message.edit_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def button_handler(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'faq':
        await faq_command(update, context)
    elif query.data == 'menu':
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
    
    # Blue Team: Verificación de claves esenciales
    if not all([TELEGRAM_TOKEN, HONEYGAIN_CODE, PAWNS_CODE, SWAGBUCKS_CODE]):
        print("🔴 ERROR DE CLAVES: Una o más variables esenciales (TOKENS/CÓDIGOS) no están configuradas en Render.")
        exit(1)

    # Iniciar la aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Blue Team: Obtener el username del bot para el botón de compartir (Viralidad)
    BOT_USERNAME = "@" + application.bot.username


    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("links", links_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot optimizado, seguro y listo para la viralidad.")
    # OPTIMIZACIÓN DE RENDIMIENTO: Polling reducido de 1.0s a 5.0s
    application.run_polling(poll_interval=5.0)


if __name__ == '__main__':
    main()
