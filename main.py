import os
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Importamos la lógica y la base de datos
from bot_logic import start, help_command, general_text_handler, reset_command, invite_command
import database as db

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("main")

# Inicializar FastAPI
app = FastAPI()

# Inicializar Bot de Telegram (Variable global)
application = None

async def setup_bot():
    """Configura y construye la aplicación del bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.critical("❌ NO SE ENCONTRÓ EL TOKEN DE TELEGRAM")
        return None

    app_bot = ApplicationBuilder().token(token).build()

    # --- REGISTRO DE COMANDOS ---
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(CommandHandler("reset", reset_command))
    app_bot.add_handler(CommandHandler("invitar", invite_command))
    
    # Manejador de Texto (Emails y Códigos)
    app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))

    await app_bot.initialize()
    await app_bot.start()
    logger.info("🤖 Bot iniciado correctamente.")
    return app_bot

# --- EVENTOS DE ARRANQUE Y APAGADO ---

@app.on_event("startup")
async def startup_event():
    global application
    logger.info("🔌 Conectando a la Base de Datos...")
    await db.init_db()  # <--- AQUI ES DONDE DABA EL ERROR ANTES
    
    logger.info("🚀 Iniciando Bot...")
    application = await setup_bot()

@app.on_event("shutdown")
async def shutdown_event():
    global application
    logger.info("🛑 Apagando sistema...")
    
    if application:
        await application.stop()
        await application.shutdown()
    
    await db.close_db()

# --- WEBHOOK PARA TELEGRAM ---

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Recibe las actualizaciones de Telegram."""
    if application:
        try:
            data = await request.json()
            update = Update.de_json(data, application.bot)
            await application.process_update(update)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error en webhook: {e}")
            return {"status": "error"}
    return {"status": "bot not initialized"}

@app.get("/")
def health_check():
    return {"status": "active", "system": "TheHive Bot"}
