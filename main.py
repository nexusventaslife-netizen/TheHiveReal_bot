import os
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request, jsonify 
import threading 

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

# --- CONFIGURACIÓN DEL BOT (Telegram Polling) ---
def run_bot():
    """Inicia el bot de Telegram en modo Polling."""
    if not TELEGRAM_TOKEN:
        print("ERROR: La variable TELEGRAM_TOKEN no está configurada. El bot no puede iniciar.")
        return

    # *** ¡CORRECCIÓN FINAL! (Soluciona el error de conexión por red - IPv4) ***
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .get_updates_handler(None)
        .ipv6_attachment_mode(False) # <--- FUERZA IPv4 para la conexión
        .build()
    )
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot iniciado. Escuchando comandos...")
    application.run_polling(poll_interval=1.0)


# --- CONFIGURACIÓN DEL WEB SERVER (FLASK/RENDER) ---

# 1. Creamos la aplicación Flask (el nombre 'app' es requerido por gunicorn)
app = Flask(__name__)

# 2. Ruta para que Render/Gunicorn sepa que el puerto está abierto.
@app.route('/', methods=['GET', 'POST'])
def webhook():
    return jsonify({'status': 'ok', 'message': 'Bot is running via Telegram Polling'}), 200

# 3. Iniciamos el bot de Telegram en un Hilo separado, para no bloquear el Web Server.
bot_thread = threading.Thread(target=run_bot)
bot_thread.start()
