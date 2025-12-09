import os
import logging
import asyncio
from fastapi import FastAPI
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Importamos tus archivos locales
from bot_logic import start, help_command, code_handler, invite_command, reset_command, button_handler
import database as db

# Configuración de Logs (Para ver errores en Render)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token de Telegram desde las Variables de Entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Inicializamos la App de FastAPI (Esto mantiene vivo a Render)
app = FastAPI()

# Variable global para la aplicación del bot
bot_app = None

@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor."""
    global bot_app
    
    # 1. Conectar Base de Datos
    logger.info("🔌 Conectando a la Base de Datos...")
    await db.init_db()
    
    # 2. Configurar el Bot
    if TOKEN:
        logger.info("🤖 Iniciando Bot de Telegram...")
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # --- REGISTRO DE COMANDOS Y HANDLERS ---
        
        # Comandos básicos
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command)) # Comando secreto para resetear
        
        # Manejo de botones (Para el "Acepto Publicidad")
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        
        # Manejo de texto (Para recibir el Código y el Email)
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), code_handler))
        
        # 3. Arrancar el Bot en modo Polling (Segundo plano)
        await bot_app.initialize()
        await bot_app.start()
        
        # Creamos una tarea asíncrona para que el bot escuche mensajes siempre
        asyncio.create_task(bot_app.updater.start_polling())
        logger.info("✅ Bot escuchando mensajes.")
    else:
        logger.error("❌ NO SE ENCONTRÓ EL TOKEN DE TELEGRAM")

@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al apagar el servidor."""
    logger.info("🛑 Apagando sistemas...")
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await db.close_db()

@app.get("/")
def index():
    """Ruta para que Render sepa que estamos vivos (Health Check)."""
    return {"status": "online", "bot": "TheHive Running"}
