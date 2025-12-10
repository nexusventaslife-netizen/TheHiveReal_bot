import os
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Importaciones verificadas
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

async def start_bot_safely():
    """Inicia el bot intentando evitar conflictos."""
    global bot_app
    if not TOKEN:
        logger.error("❌ TOKEN NO ENCONTRADO")
        return

    logger.info("🤖 Construyendo Bot...")
    bot_app = ApplicationBuilder().token(TOKEN).build()
    
    # Comandos
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("invitar", invite_command))
    bot_app.add_handler(CommandHandler("reset", reset_command))
    
    # Callbacks y Texto
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))

    # Inicialización
    await bot_app.initialize()
    await bot_app.start()
    
    # Usamos drop_pending_updates=True para ignorar updates viejos que causen conflicto
    logger.info("📡 Iniciando Polling (Limpiando updates pendientes)...")
    asyncio.create_task(bot_app.updater.start_polling(drop_pending_updates=True))

@app.on_event("startup")
async def startup_event():
    logger.info("🔌 Iniciando DB...")
    await db.init_db()
    
    # Pequeña pausa de seguridad para permitir que procesos viejos mueran
    await asyncio.sleep(2) 
    await start_bot_safely()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Apagando...")
    if bot_app:
        if bot_app.updater.running:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await db.close_db()

@app.get("/")
def index():
    return {"status": "TheHive Active", "version": "Final_Fixed"}
