import os
import asyncio
import logging
from fastapi import FastAPI, Request
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram import Update

# Importamos nuestros módulos locales
# Asegúrate de que database.py y bot_logic.py existan en la misma carpeta
from database import init_db
from bot_logic import (
    start_command, save_email, menu_handler, mine_callback, 
    request_proof, process_proof, WAIT_EMAIL, WAIT_PROOF
)

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("Hive.Main")

# LEEMOS LAS VARIABLES DE RENDER
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Ejemplo: https://tu-app.onrender.com
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "super-secret-token") # Token de seguridad para webhook

if not TELEGRAM_TOKEN:
    logger.error("❌ ERROR: No se encontró TELEGRAM_TOKEN en las variables de entorno.")

app = FastAPI(title="TheOneHive Titan Node")
telegram_app = None

@app.on_event("startup")
async def startup():
    global telegram_app
    logger.info("🚀 INICIANDO SISTEMA HIVE TITAN...")
    
    # 1. Iniciar Base de Datos
    await init_db(DATABASE_URL)
    
    # 2. Construir el Bot
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 3. Registrar Cerebros (Handlers)
    telegram_app.add_handler(CommandHandler("start", start_command))
    
    # Manejador del Menú Principal
    telegram_app.add_handler(MessageHandler(filters.Regex("^(ACADEMIA|MINAR|VIP|CPA|RETIRAR|PERFIL|ADS|P2P)"), menu_handler))
    
    # Callbacks de botones
    telegram_app.add_handler(CallbackQueryHandler(mine_callback, pattern="mine_manual"))
    telegram_app.add_handler(CallbackQueryHandler(mine_callback, pattern="watch_ad"))
    
    # Flujo de Registro (Email)
    telegram_app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Hola"), start_command)],
        states={WAIT_EMAIL: [MessageHandler(filters.TEXT, save_email)]},
        fallbacks=[CommandHandler("start", start_command)]
    ))
    
    # Flujo de Pruebas de Pago
    telegram_app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(request_proof, pattern="req_proof")],
        states={WAIT_PROOF: [MessageHandler(filters.PHOTO, process_proof)]},
        fallbacks=[CommandHandler("start", start_command)]
    ))

    # 4. Inicializar Bot
    await telegram_app.initialize()
    await telegram_app.start()
    
    # 5. DECISIÓN CRÍTICA: WEBHOOK VS POLLING (Aquí estaba tu error)
    if WEBHOOK_URL:
        logger.info(f"🌐 MODO PRODUCCIÓN DETECTADO: Configurando Webhook en {WEBHOOK_URL}")
        # Primero borramos cualquier webhook previo para evitar conflictos
        await telegram_app.bot.delete_webhook()
        # Configuramos el nuevo webhook
        webhook_path = f"{WEBHOOK_URL}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_path, secret_token=SECRET_TOKEN)
        logger.info(f"✅ Webhook establecido exitosamente en: {webhook_path}")
    else:
        logger.warning("🔌 MODO LOCAL DETECTADO: Usando Polling")
        # Borramos webhook por si había uno pegado de antes
        await telegram_app.bot.delete_webhook()
        asyncio.create_task(telegram_app.updater.start_polling(drop_pending_updates=True))

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Endpoint para recibir actualizaciones de Telegram vía Webhook
    """
    try:
        # Verificación de seguridad (Opcional pero recomendado)
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if SECRET_TOKEN and header_secret != SECRET_TOKEN:
            logger.warning("⚠️ Intento de acceso al webhook con token inválido")
            return {"ok": False, "reason": "Invalid Token"}

        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        
        # Procesar update de forma asíncrona para no bloquear
        asyncio.create_task(telegram_app.process_update(update))
    except Exception as e:
        logger.error(f"❌ Error en Webhook: {e}")
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status": "ONLINE", "mode": "WEBHOOK" if WEBHOOK_URL else "POLLING"}

@app.head("/health")
async def health_head():
    return {"status": "ONLINE"}
