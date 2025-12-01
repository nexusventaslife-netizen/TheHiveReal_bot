import os
import telegram
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# --- CONFIGURACIÓN DE SEGURIDAD ---
THROTTLE_LIMITS = {}
THROTTLE_TIME_SECONDS = 5

# --- CLAVES SECRETAS (ASUMIMOS QUE YA ESTÁN CONFIGURADAS) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
HONEYGAIN_CODE = os.environ.get('HONEYGAIN_CODE')
PAWNS_CODE = os.environ.get('PAWNS_CODE')
SWAGBUCKS_CODE = os.environ.get('SWAGBUCKS_CODE')

# --- LINKS Y DESCRIPCIONES ---
# El @nombre_de_tu_bot se puede obtener del contexto o si el usuario lo conoce,
# pero usaremos un texto estático para el mensaje de compartir:
BOT_USERNAME = "@" + context.bot.username if 'context' in locals() else "@TheHive2.0_bot" # Reemplazar con el nombre de tu bot

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

# Función de Seguridad (Throttling) y Contenido
async def send_links_menu(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
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
    
    # Crear los botones de Enlaces
    keyboard = [
        [InlineKeyboardButton("🍯 Honeygain", url=LINKS['Honeygain']),
         InlineKeyboardButton("🐾 Pawns App", url=LINKS['Pawns App'])],
        [InlineKeyboardButton("💵 Swagbucks", url=LINKS['Swagbucks']),
         InlineKeyboardButton("❓ Preguntas Frecuentes", callback_data='faq')], # Nuevo botón de Ayuda
        # Mitigación de Viralidad: Botón de compartir nativo de Telegram
        [InlineKeyboardButton("🔗 ¡Invita a la Colmena!", switch_inline_query=BOT_USERNAME)]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=telegram.constants.ParseMode.MARKDOWN
    )

async def faq_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Mitigación de Enganche: Función de Ayuda y Preguntas Frecuentes."""
    faq_message = (
        "📚 **PREGUNTAS FRECUENTES (FAQ)** 📚\n\n"
        "**1. ¿Qué hago si un enlace no funciona?**\n"
        "R: Simplemente cópialo completo, incluyendo 'https://'. A veces el navegador tiene problemas.\n\n"
        "**2. ¿Es seguro usar estas apps?**\n"
        "R: Sí. Todas las apps son revisadas y solo piden compartir ancho de banda.\n\n"
        "**3. ¿Cómo puedo apoyar más?**\n"
        f"R: Comparte este bot con un amigo usando el botón 'Invita a la Colmena!' en el menú principal ({BOT_USERNAME})."
    )
    
    # Botón para volver al menú principal
    keyboard = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # El comando /ayuda puede venir de un mensaje o de un botón de callback
    if update.callback_query:
        await update.callback_query.message.edit_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(faq_message, reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.MARKDOWN)


# Manejador de botones en línea (callback_query)
async def button_handler(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'faq':
        await faq_command(update, context) # Llama a FAQ para editar el mensaje
    elif query.data == 'menu':
        # Simula el comando /start para volver al menú principal
        await send_links_menu(update, context)
        
        
# Comandos
async def start_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    # Aquí puedes obtener el BOT_USERNAME real si lo necesitas
    global BOT_USERNAME
    BOT_USERNAME = "@" + context.bot.username
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

    if not TELEGRAM_TOKEN or not HONEYGAIN_CODE or not PAWNS_CODE or not SWAGBUCKS_CODE:
        print("🔴 ERROR DE SEGURIDAD/CLAVES: Una o más variables esenciales (TOKENS/CÓDIGOS) no están configuradas en Render. Terminando el servicio.")
        exit(1)

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("links", links_command))
    application.add_handler(CommandHandler("ayuda", help_command)) # Nuevo comando /ayuda
    application.add_handler(telegram.ext.CallbackQueryHandler(button_handler)) # Manejador de botones
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot iniciado, protegido con Throttling y optimizado para viralidad. Escuchando comandos...")
    application.run_polling(poll_interval=1.0)


if __name__ == '__main__':
    main()
