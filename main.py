import os
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# --- CLAVES SECRETAS ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
HONEYGAIN_CODE = os.environ.get('HONEYGAIN_CODE')
PAWNS_CODE = os.environ.get('PAWNS_CODE')
SWAGBUCKS_CODE = os.environ.get('SWAGBUCKS_CODE')

# --- LINKS DE REFERIDOS ---
LINKS = {
    'Honeygain': f'https://r.honeygain.me/THEHIVE{HONEYGAIN_CODE}',
    'Pawns App': f'https://pawns.app/?r={PAWNS_CODE}',
    'Swagbucks': f'https://www.swagbucks.com/?r={SWAGBUCKS_CODE}'
}

# --- FUNCIONES DEL BOT ---
async def start_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start con un menú de botones."""
    
    message = (
        "🤖 **¡Hola! Soy The Hive Real Bot.**\n\n"
        "Usa los botones de abajo para acceder a nuestros enlaces de referido "
        "y empezar a ganar ingresos pasivos. ¡Gracias por unirte a la colmena! 🍯\n"
    )
    
    # 1. CREAR LOS BOTONES (InlineKeyboardButton)
    keyboard = [
        [InlineKeyboardButton("🍯 Honeygain", url=LINKS['Honeygain'])],
        [InlineKeyboardButton("🐾 Pawns App", url=LINKS['Pawns App'])],
        [InlineKeyboardButton("💵 Swagbucks", url=LINKS['Swagbucks'])],
    ]

    # 2. AGRUPAR LOS BOTONES EN UN TECLADO (InlineKeyboardMarkup)
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 3. ENVIAR EL MENSAJE CON LOS BOTONES
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=telegram.constants.ParseMode.MARKDOWN
    )

async def handle_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando."""
    pass

def main():
    """Inicia el bot y lo mantiene escuchando (Polling)."""
    if not TELEGRAM_TOKEN:
        print("ERROR: La variable TELEGRAM_TOKEN no está configurada. El bot no puede iniciar.")
        return

    # Usamos la configuración limpia que ya funciona:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot iniciado. Escuchando comandos...")
    application.run_polling(poll_interval=1.0)


if __name__ == '__main__':
    main()
