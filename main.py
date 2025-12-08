import os
import hashlib
import logging
from fastapi import FastAPI, Request
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram import Update

# Importamos utilidades de base de datos
from database import init_db, process_secure_postback, redis_client as db_redis_client
# Importamos la lógica del bot. Asumo que las funciones importadas existen en bot_logic.py
from bot_logic import (
    start_command, 
    process_email_input, 
    check_gate_callback, 
    menu_handler, 
    mine_tap_callback, 
    withdraw_callback, 
    reset_me, 
    WAIT_EMAIL, 
    WAIT_API_CHECK
)
# Importamos utilidades de caché
from cache import init_cache

# CONFIGURACIÓN
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
CPA_SECRET_KEY = os.environ.get("CPA_SECRET", "mi_secreto_super_seguro_123")

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("Hive.Main")

app = FastAPI()
telegram_app = None

@app.on_event("startup")
async def startup():
    global telegram_app
    # 1. Iniciar Base de Datos y Redis
    await init_db(DATABASE_URL)
    
    # 2. Conectar el sistema de Caché con el cliente Redis de database.py
    # Esto soluciona el problema de que cache.py no tenía cliente
    if db_redis_client:
        await init_cache(db_redis_client)
        logger.info("✅ Cache system linked to Redis.")
    else:
        logger.warning("⚠️ Cache system initialized WITHOUT Redis.")

    # 3. Iniciar Bot
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # --- MANEJADORES ---
    
    # 1. Comando de Reinicio (Para tus pruebas)
    telegram_app.add_handler(CommandHandler("reset", reset_me))

    # 2. Flujo de Conversación (Registro: Start -> Email -> API)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WAIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_input)],
            WAIT_API_CHECK: [CallbackQueryHandler(check_gate_callback, pattern="check_gate")]
        },
        fallbacks=[CommandHandler("start", start_command)],
        allow_reentry=True
    )
    telegram_app.add_handler(conv_handler)
    
    # 3. Callbacks y Menús
    telegram_app.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="mine_tap"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_callback, pattern="try_withdraw"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    
    # Inicializar aplicación
    await telegram_app.initialize()
    await telegram_app.start()
    
    # Configurar Webhook
    if WEBHOOK_URL:
        webhook_path = f"{WEBHOOK_URL}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_path)
        logger.info(f"webhook set to: {webhook_path}")

@app.on_event("shutdown")
async def shutdown():
    """Cierre limpio de conexiones"""
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    
    from database import db_pool, redis_client
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()
    logger.info("🛑 System Shutdown Complete")

# --- ENDPOINTS API ---

@app.get("/")
async def root():
    """Endpoint raíz para que Render sepa que estamos vivos (Health Check)"""
    return {"status": "Titan Node Online", "system": "Active"}

@app.post("/webhook")
async def webhook(request: Request):
    """Recibe actualizaciones de Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}

@app.get("/postback/secure")
async def secure_postback(uid: int, amount: float, network: str, sig: str):
    """Recibe pagos seguros de OfferToro/CPAGrip"""
    base_str = f"{uid}{amount}{CPA_SECRET_KEY}"
    local_sig = hashlib.md5(base_str.encode()).hexdigest()
    
    if local_sig != sig:
        logger.warning(f"🚨 HACK ATTEMPT: User {uid} fake postback.")
        return {"error": "Invalid Signature"}
    
    result = await process_secure_postback(uid, amount, network)
    
    # Notificar al usuario si es posible
    try:
        msg = f"💰 **PAGO RECIBIDO: ${amount}**\n"
        if result['status'] == 'ON_HOLD':
            msg += "⚠️ En revisión de seguridad (7 días)."
        else:
            msg += f"✅ Acreditado: ${result['user_share']:.2f}"
        await telegram_app.bot.send_message(chat_id=uid, text=msg)
    except: pass
    
    return {"status": "OK", "details": result}
