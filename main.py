
import os
import requests
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask # Nueva linea para abrir el puerto
app = Flask(__name__) # Nueva linea para abrir el puerto

# --- CLAVES SECRETAS ---
# Las claves están en las Variables de Entorno de Render.
# Asegúrate de que los nombres sean EXACTOS: TELEGRAM_TOKEN, HONEYGAIN_CODE, etc.

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

# --- COMANDOS DEL BOT ---

async def start_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start y presenta el bot."""
    
    # Construir el mensaje de bienvenida con los enlaces
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

async def help_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Responde al comando /help con una guía."""
    await update.message.reply_text(
        "📝 **Guía de Uso:**\n"
        "Simplemente usa el comando /start para ver todos los enlaces de referido. "
        "Si necesitas más ayuda, contacta al administrador del canal."
    )

async def handle_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Ignora cualquier mensaje que no sea un comando."""
    # Opcional: Podrías responder aquí si quieres que el bot hable con usuarios.
    pass

# --- INICIO DEL BOT ---

def main():
    """Inicia el bot y lo mantiene escuchando."""
    if not TELEGRAM_TOKEN:
        print("ERROR: La variable TELEGRAM_TOKEN no está configurada. El bot no puede iniciar.")
        return

    # 1. Crear la aplicación del bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. Asignar los comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # 3. Asignar el manejo de mensajes (Ignorar texto plano)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 4. Iniciar el bot (modo polling)
    # Esto es más simple y funciona bien con Render/Uptime Robot.
    print("Bot iniciado. Escuchando comandos...")
    application.run_polling(poll_interval=1.0)

# --- PUNTO DE ENTRADA PRINCIPAL ---

if __name__ == '__main__':
    main()
