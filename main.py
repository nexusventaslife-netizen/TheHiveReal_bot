import os
import re
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import uvicorn

# --- IMPORTS PROPIOS ---
from database import init_db, close_db
from bot_logic import (
    start, 
    process_email_input, 
    check_gate_verify_callback, # OJO: Importamos el callback de verificar
    menu_handler, 
    mine_tap_callback, 
    withdraw_callback,
    help_command
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN Y SANITIZACIÓN DEL TOKEN ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# SOLUCIÓN AL ERROR DE "UNALLOWED CHARACTERS"
# Obtenemos el token raw, si no existe usamos uno por defecto seguro.
raw_secret = os.getenv("SECRET_TOKEN", "SuperSecretToken_123")
# Regex: Solo permite letras, números, guion bajo y guion medio. Elimina espacios u otros símbolos.
SECRET_TOKEN = re.sub(r'[^a-zA-Z0-9_-]', '', raw_secret)

# Si tras limpiar queda vacío, forzamos uno
if not SECRET_TOKEN:
    SECRET_TOKEN = "FallbackSecret_2025"

logger.info(f"🔑 Secret Token configurado (Saneado): {SECRET_TOKEN}")

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ FALTAN VARIABLES: TELEGRAM_TOKEN o WEBHOOK_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicio
    logger.info("🚀 Iniciando TheHiveReal...")
    await init_db()
    
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_handler))
    # Captura email (Texto sin comandos)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_input))
    # Callbacks
    application.add_handler(CallbackQueryHandler(check_gate_verify_callback, pattern="^check_gate_verify$"))
    application.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="^mine_tap$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    
    await application.initialize()
    await application.start()
    
    webhook_endpoint = f"{WEBHOOK_URL}/telegram-webhook"
    logger.info(f"🔗 Webhook URL: {webhook_endpoint}")
    
    # Aquí es donde fallaba antes si el token tenía caracteres raros
    await application.bot.set_webhook(
        url=webhook_endpoint, 
        secret_token=SECRET_TOKEN,
        allowed_updates=Update.ALL_TYPES
    )
    
    app.state.telegram_app = application
    yield
    
    # 2. Apagado
    logger.info("🛑 Apagando...")
    try:
        await application.bot.delete_webhook()
        await application.stop()
        await application.shutdown()
        await close_db() # Ahora sí existe esta función
    except Exception as e:
        logger.error(f"Error en shutdown: {e}")

app = FastAPI(lifespan=lifespan)

@app.get("/", status_code=200)
@app.head("/", status_code=200)
async def health_check():
    return {"status": "online"}

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    if token_header != SECRET_TOKEN:
        logger.warning("⚠️ Intento de acceso no autorizado al webhook")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        data = await request.json()
        telegram_app = request.app.state.telegram_app
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"❌ Error webhook: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
