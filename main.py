import os
import telegram
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
    """Responde al comando /start y presenta el bot."""
    message = (
        "🤖 **¡Hola! Soy The Hive Real Bot.**\n\n"
        "Estoy aquí para darte acceso a los enlaces de referido de nuestra comunidad "
        "para que puedas empezar a ganar ingresos pasivos.\n\n"
        "🔗 **Nuestros Enlaces:**\n"
    )
    for name, link in LINKS.items():
        message += f"▪️ **{name}:** `{link}`\n"
    message += "\n*Copia el enlace completo (incluyendo https://) para que funcione correctamente.*"
    await update.message.reply_text(message, parse_mode=telegram.constants.ParseMode.MARKDOWN)

async def handle_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando."""
    pass

def main():
    """Inicia el bot y lo mantiene escuchando (Polling) en el Worker."""
    if not TELEGRAM_TOKEN:
        print("ERROR: La variable TELEGRAM_TOKEN no está configurada. El bot no puede iniciar.")
        return

    # *** ¡CORRECCIÓN FINAL! (Elimina el método get_updates_handler que falló) ***
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .ipv6_attachment_mode(False) # <- Mantiene la corrección de IPv4
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot iniciado. Escuchando comandos...")
    application.run_polling(poll_interval=1.0)


if __name__ == '__main__':
    main()
