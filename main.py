import os
import re
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import uvicorn

# Imports
from database import init_db, close_db
from bot_logic import (
    start, 
    process_email_input, 
    check_gate_verify_callback, 
    menu_handler, 
    mine_tap_callback, 
    withdraw_callback,
    help_command
)

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("Hive.Main")

# --- CONFIGURACIÓN CRÍTICA ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
# Limpieza de URL: Quitamos slash final y espacios
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
# Token Secreto Sanitizado
SECRET_TOKEN = re.sub(r'[^a-zA-Z0-9_-]', '', os.getenv("SECRET_TOKEN", "Secret123"))

if not TOKEN or not WEBHOOK_URL:
    logger.critical("❌ ERROR: Faltan variables TELEGRAM_TOKEN o WEBHOOK_URL.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("🚀 Arrancando TheHiveReal (Modo Persistente)...")
    await init_db()
    
    application = Application.builder().token(TOKEN).build()
    
    # Registrar Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_input))
    application.add_handler(CallbackQueryHandler(check_gate_verify_callback, pattern="^check_gate_verify$"))
    application.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="^mine_tap$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    
    await application.initialize()
    await application.start()
    
    # Configurar Webhook
    webhook_path = "/webhook"
    full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"
    
    logger.info(f"🔗 Configurando Webhook en Telegram hacia: {full_webhook_url}")
    
    try:
        await application.bot.set_webhook(
            url=full_webhook_url, 
            secret_token=SECRET_TOKEN,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            max_connections=100
        )
        logger.info("✅ Webhook establecido y persistente.")
    except Exception as e:
        logger.error(f"❌ Falló set_webhook: {e}")

    app.state.telegram_app = application
    yield
    
    # --- SHUTDOWN ---
    logger.info("🛑 Apagando servicios...")
    try:
        # 🔥 CAMBIO IMPORTANTE: Comentamos delete_webhook
        # Esto evita que el bot se desconecte de Telegram si Render reinicia.
        # await application.bot.delete_webhook() 
        
        await application.stop()
        await application.shutdown()
        await close_db()
    except Exception as e:
        logger.error(f"Error en cierre: {e}")

app = FastAPI(lifespan=lifespan)

# --- RUTAS ---

@app.get("/")
@app.head("/")
async def root():
    return {"status": "TheHiveReal Online"}

# ✅ Endpoint para Render (Evita reinicios constantes)
@app.get("/healthz", status_code=200)
@app.head("/healthz", status_code=200)
async def health_check_render():
    return {"status": "ok"}

# ✅ Ruta del Webhook
@app.post("/webhook")
async def telegram_webhook(request: Request):
    # Seguridad
    token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token_header != SECRET_TOKEN:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        data = await request.json()
        telegram_app = request.app.state.telegram_app
        update = Update.de_json(data, telegram_app.bot)
        
        # Procesar sin bloquear (Fire-and-forget)
        await telegram_app.process_update(update)
        
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error procesando update: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
