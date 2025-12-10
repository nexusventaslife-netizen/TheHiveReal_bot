import os
import logging
import asyncio
from fastapi import FastAPI
# --- CORRECCIÓN AQUÍ: Agregamos 'Update' que faltaba ---
from telegram import Update 
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Importamos todo correctamente
from bot_logic import start, help_command, general_text_handler, invite_command, reset_command, button_handler
import database as db

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
app = FastAPI()
bot_app = None

@app.on_event("startup")
async def startup_event():
    global bot_app
    
    # 1. DB
    logger.info("🔌 Conectando DB...")
    await db.init_db()
    
    # 2. BOT
    if TOKEN:
        logger.info("🤖 Configurando Bot...")
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # Comandos
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
        
        # INICIALIZACIÓN
        await bot_app.initialize()
        await bot_app.start()
        
        # --- SOLUCIÓN DEL CONFLICTO ---
        # Borramos cualquier webhook viejo o instancias fantasmas
        logger.info("🧹 Limpiando conflictos de Telegram...")
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        
        # Arrancamos el polling
        # Ahora funcionará porque 'Update' ya está importado arriba
        asyncio.create_task(bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES))
        logger.info("✅ Bot escuchando (Conflictos resueltos).")
    else:
        logger.error("❌ FALTA TELEGRAM_TOKEN")

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
def health():
    return {"status": "ok"}
