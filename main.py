import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Importamos las funciones DESDE bot_logic.py
# AÑADIDO: invite_command
from bot_logic import start, help_command, code_handler, invite_command
import database as db

# Configuración básica de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
app = FastAPI()

if not TOKEN:
    logger.error("Error: No se encontró la variable TELEGRAM_TOKEN")
    exit(1)

# Ciclo de vida de FastAPI para conectar DB al arrancar
@app.on_event("startup")
async def startup():
    await db.init_db()

@app.on_event("shutdown")
async def shutdown():
    await db.close_db()

# Construimos la aplicación del bot
application = ApplicationBuilder().token(TOKEN).build()

# --- CONECTAMOS LAS FUNCIONES ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("invitar", invite_command)) # <--- NUEVO COMANDO
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), code_handler))

# --- RUTA WEBHOOK ---
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
        logger.error(f"Error en webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def index():
    return {"status": "Bot TheHive Activo 🐝"}
