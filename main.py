import os
import asyncio
import logging
from fastapi import FastAPI, Request
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram import Update

# Importamos nuestros módulos locales
from database import init_db
from bot_logic import (
    start_command, save_email, menu_handler, mine_callback, 
    request_proof, process_proof, WAIT_EMAIL, WAIT_PROOF
)

# Configuración Básica
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("Hive.Main")

# LEEMOS LAS VARIABLES DE RENDER (NO PONER CLAVES AQUÍ)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # Ejemplo: https://tu-app.onrender.com

app = FastAPI(title="TheOneHive Titan Node")
telegram_app = None

@app.on_event("startup")
async def startup():
    global telegram_app
    logger.info("🚀 INICIANDO SISTEMA HIVE TITAN...")
    
    # 1. Iniciar Base de Datos (Pool de conexiones)
    await init_db(DATABASE_URL)
    
    # 2. Construir el Bot
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 3. Registrar Cerebros (Handlers)
    telegram_app.add_handler(CommandHandler("start", start_command))
    
    # Manejador del Menú Principal (Regex atrapa todas las opciones)
    telegram_app.add_handler(MessageHandler(filters.Regex("^(ACADEMIA|MINAR|VIP|CPA|RETIRAR|PERFIL|ADS|P2P)"), menu_handler))
    
    # Callbacks de botones
    telegram_app.add_handler(CallbackQueryHandler(mine_callback, pattern="mine_manual"))
    telegram_app.add_handler(CallbackQueryHandler(mine_callback, pattern="watch_ad")) # Simplificado para MVP
    
    # Flujo de Registro (Email)
    telegram_app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Hola"), start_command)], # Trigger de seguridad
        states={WAIT_EMAIL: [MessageHandler(filters.TEXT, save_email)]},
        fallbacks=[CommandHandler("start", start_command)]
    ))
    
    # Flujo de Pruebas de Pago
    telegram_app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(request_proof, pattern="req_proof")],
        states={WAIT_PROOF: [MessageHandler(filters.PHOTO, process_proof)]},
        fallbacks=[CommandHandler("start", start_command)]
    ))

    # 4. Arrancar Bot
    await telegram_app.initialize()
    await telegram_app.start()
    
    # 5. Configuración INTELIGENTE de Webhook vs Polling
    if WEBHOOK_URL:
        logger.info(f"🌐 MODO PRODUCCIÓN DETECTADO: Usando Webhook en {WEBHOOK_URL}")
        # Le decimos a Telegram: "Envía los mensajes a esta URL"
        await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    else:
        logger.warning("🔌 MODO LOCAL DETECTADO: Usando Polling (No apto para 200k usuarios)")
        asyncio.create_task(telegram_app.updater.start_polling(drop_pending_updates=True))

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Esta es la puerta de entrada para millones de mensajes.
    FastAPI recibe el mensaje y se lo pasa al Bot de forma asíncrona.
    """
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Error en Webhook: {e}")
    return {"ok": True}

@app.get("/health")
async def health():
    """Para que Render sepa que estamos vivos."""
    return {"status": "ONLINE", "mode": "TITAN"}

@app.head("/health")
async def health_head():
    return {"status": "ONLINE"}
