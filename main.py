import os
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Importamos TODO correctamente
from bot_logic import start, help_command, general_text_handler, invite_command, reset_command, button_handler
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
    """Inicia DB y Bot."""
    global bot_app
    
    # 1. Base de Datos
    logger.info("🔌 Conectando a DB...")
    await db.init_db()
    
    # 2. Bot
    if TOKEN:
        logger.info("🤖 Iniciando Bot...")
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # Handlers
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        
        # Botones
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        
        # Texto (Email y Código)
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
        
        await bot_app.initialize()
        await bot_app.start()
        
        # Polling en segundo plano
        asyncio.create_task(bot_app.updater.start_polling(drop_pending_updates=True)) 
        # drop_pending_updates=True ayuda a limpiar conflictos viejos
        
        logger.info("✅ Bot Activo.")
    else:
        logger.error("❌ FALTA TOKEN")

@app.on_event("shutdown")
async def shutdown_event():
    """Apaga todo limpiamente para evitar conflictos."""
    logger.info("🛑 Apagando...")
    if bot_app:
        if bot_app.updater.running:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await db.close_db()

@app.get("/")
def index():
    return {"status": "TheHive Online"}
