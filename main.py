import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Importamos solo las funciones que SI existen en tu nuevo bot_logic
from bot_logic import start, help_command, code_handler

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Inicializar FastAPI
app = FastAPI()

# Inicializar Bot de Telegram
if not TOKEN:
    logger.error("Error: No se encontró la variable TELEGRAM_TOKEN")
    exit(1)

application = ApplicationBuilder().token(TOKEN).build()

# --- REGISTRAR LOS HANDLERS (Las funciones del bot) ---
# Comando /start
application.add_handler(CommandHandler("start", start))

# Comando /help
application.add_handler(CommandHandler("help", help_command))

# Mensajes de texto (Para detectar el código HIVE-777)
# Filtramos para que NO sea un comando (como /start)
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), code_handler))

# --- RUTA WEBHOOK (Para conectar con Telegram) ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.initialize()
        await application.process_update(update)
        await application.shutdown()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error procesando update: {e}")
        return {"status": "error", "message": str(e)}

# Ruta simple para verificar que el servidor está vivo
@app.get("/")
async def index():
    return {"status": "The Hive Bot is Running 🐝"}
