import os
import hashlib
import logging
from fastapi import FastAPI, Request, Response
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram import Update

# Importamos módulo completo para acceder a variables globales actualizadas
import database 
from database import init_db, process_secure_postback

# Importamos lógica del bot
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
    
    # 1. Base de Datos y Redis
    await init_db(DATABASE_URL)
    
    # 2. Conectar Caché (Usando la conexión creada en database.py)
    if database.redis_client:
        await init_cache(database.redis_client)
        logger.info("✅ Cache system linked to Redis successfully.")
    else:
        logger.warning("⚠️ Cache system running in MEMORY ONLY (Check REDIS_URL).")

    # 3. Iniciar Bot
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # --- MANEJADORES Y FILTROS ---
    
    # Comando Reset (Solo admin/dev)
    telegram_app.add_handler(CommandHandler("reset", reset_me))

    # Flujo de Entrada Obligatorio (Start -> Email -> API Check)
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
    
    # Menú Principal (Solo accesible tras pasar filtros)
    telegram_app.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="mine_tap"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_callback, pattern="try_withdraw"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    
    await telegram_app.initialize()
    await telegram_app.start()
    
    if WEBHOOK_URL:
        webhook_path = f"{WEBHOOK_URL}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_path)
        logger.info(f"webhook set to: {webhook_path}")

@app.on_event("shutdown")
async def shutdown():
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    if database.db_pool:
        await database.db_pool.close()
    if database.redis_client:
        await database.redis_client.close()
    logger.info("🛑 System Shutdown Complete")

# --- ENDPOINTS CRÍTICOS (Health Checks & Webhooks) ---

# SOLUCIÓN AL ERROR 405: Permitimos HEAD en todas las rutas de salud
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Titan Node Online", "system": "Active"}

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Render usa esto para verificar vida. Debe devolver 200 OK siempre."""
    return {
        "status": "healthy",
        "database": "connected" if database.db_pool else "disconnected"
    }

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}

# --- MONETIZACIÓN: POSTBACK CPA ---
@app.get("/postback/secure")
async def secure_postback(uid: int, amount: float, network: str, sig: str):
    """
    Endpoint para redes de CPA (OfferToro, CPAGrip).
    Estructura esperada: ?uid={user_id}&amount={payout}&network={source}&sig={md5_hash}
    """
    # Verificación de firma para seguridad
    base_str = f"{uid}{amount}{CPA_SECRET_KEY}"
    local_sig = hashlib.md5(base_str.encode()).hexdigest()
    
    if local_sig != sig:
        logger.warning(f"🚨 HACK ATTEMPT: User {uid} fake postback.")
        return {"error": "Invalid Signature"}
    
    # Procesar pago
    result = await process_secure_postback(uid, amount, network)
    
    # Notificar al usuario (Fidelización)
    try:
        msg = f"💰 **¡DINERO RECIBIDO!**\nHas ganado: `${amount}`\nFuente: {network}"
        if result['status'] == 'ON_HOLD':
            msg += "\n⚠️ Saldo en retención por seguridad (Anti-Fraude)."
        await telegram_app.bot.send_message(chat_id=uid, text=msg)
    except: pass
    
    return {"status": "OK"}
