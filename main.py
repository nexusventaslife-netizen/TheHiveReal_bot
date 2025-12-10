import os
import logging
import asyncio
from fastapi import FastAPI
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# CORRECCIÓN AQUÍ: Importamos los nombres EXACTOS que existen en bot_logic.py
from bot_logic import start, help_command, code_handler, invite_command, reset_command, button_handler
import database as db

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
app = FastAPI()
bot_app = None

@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor."""
    global bot_app
    
    logger.info("🔌 Conectando a la Base de Datos...")
    await db.init_db()
    
    if TOKEN:
        logger.info("🤖 Iniciando Bot de Telegram...")
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # --- REGISTRO DE COMANDOS ---
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        
        # --- HANDLERS ---
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        
        # IMPORTANTE: Usamos code_handler para manejar el texto
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), code_handler))
        
        await bot_app.initialize()
        await bot_app.start()
        
        asyncio.create_task(bot_app.updater.start_polling())
        logger.info("✅ Bot escuchando mensajes.")
    else:
        logger.error("❌ NO SE ENCONTRÓ EL TOKEN DE TELEGRAM")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Apagando sistemas...")
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await db.close_db()

@app.get("/")
def index():
    return {"status": "online", "bot": "TheHive Running"}
