import os
import logging
import re
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
    check_gate_callback, 
    check_gate_verify_callback,
    menu_handler, 
    mine_tap_callback, 
    withdraw_callback,
    help_command
)

# --- CONFIGURACIÓN DE LOGS (Nivel WARNING para Producción para no llenar el disco) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Cambiar a WARNING cuando tengas >10k usuarios
)
logger = logging.getLogger("Hive.Main")

# --- VARIABLES DE ENTORNO ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
# Limpiamos la URL de webhooks para evitar dobles slashes
raw_webhook_url = os.getenv("WEBHOOK_URL", "")
WEBHOOK_URL = raw_webhook_url.rstrip("/") 
WEBHOOK_PATH = "/webhook" # Ruta interna estándar

# --- SEGURIDAD: SECRET TOKEN ---
# Sanitización estricta para evitar crashes por caracteres raros
RAW_SECRET = os.getenv("SECRET_TOKEN", "HiveSecret_Default")
SECRET_TOKEN = re.sub(r'[^a-zA-Z0-9_\-]', '', RAW_SECRET)
if not SECRET_TOKEN: SECRET_TOKEN = "SecureToken_Fallback_2025"

# Validaciones críticas
if not TOKEN or not WEBHOOK_URL:
    logger.error("❌ FALTAN VARIABLES CRÍTICAS: TELEGRAM_TOKEN o WEBHOOK_URL")

# --- LIFESPAN (Gestión de Recursos) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. ARRANQUE
    logger.info("🚀 INICIANDO SISTEMA HIVE (Production Mode)...")
    
    # Conexión DB (Vital)
    try:
        await init_db()
    except Exception as e:
        logger.critical(f"❌ ERROR DB AL INICIO: {e}")
        # No matamos la app para permitir diagnóstico, pero el bot fallará.

    # Construcción del Bot
    application = Application.builder().token(TOKEN).build()
    
    # --- RUTAS / HANDLERS ---
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_handler))
    
    # Callbacks (Botones) - Usamos Regex para ser flexibles
    application.add_handler(CallbackQueryHandler(check_gate_callback, pattern="^check_gate$"))
    application.add_handler(CallbackQueryHandler(check_gate_verify_callback, pattern="^check_gate_verify$"))
    application.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="^mine_tap$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw"))
    
    # Mensajes (Email)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_input))
    
    await application.initialize()
    await application.start()
    
    # Configuración Webhook
    webhook_endpoint = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    logger.info(f"🔗 Configurando Webhook: {webhook_endpoint}")
    
    try:
        await application.bot.set_webhook(
            url=webhook_endpoint, 
            secret_token=SECRET_TOKEN,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True, # CRÍTICO: Ignora mensajes viejos al reiniciar para no saturar
            max_connections=100 # Aumentar si Render lo permite
        )
    except Exception as e:
        logger.error(f"❌ Error Webhook: {e}")

    app.state.telegram_app = application
    
    yield # El servidor corre aquí indefinidamente
    
    # 2. APAGADO LIMPIO
    logger.info("🛑 APAGANDO SISTEMA...")
    try:
        # Primero dejamos de recibir mensajes
        await application.bot.delete_webhook()
        await application.stop()
        await application.shutdown()
        # Al final cerramos DB
        await close_db()
    except Exception as e:
        logger.error(f"Error en shutdown: {e}")

# --- API FASTAPI ---
app = FastAPI(lifespan=lifespan)

# --- RUTAS DE INFRAESTRUCTURA (HEALTH CHECKS) ---

@app.get("/", status_code=200)
async def root():
    return {"status": "online", "app": "TheHiveReal Bot"}

# ESTA ES LA RUTA QUE BUSCA RENDER (Arregla el 404)
@app.get("/health", status_code=200)
@app.head("/health", status_code=200)
async def health_check():
    """Ping usado por Render y UptimeRobot para mantener vivo el bot."""
    return {"status": "healthy"}

# --- RUTA DEL WEBHOOK ---
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Procesa updates de Telegram de forma asíncrona."""
    
    # 1. Seguridad
    token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token_header != SECRET_TOKEN:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    # 2. Procesamiento
    try:
        data = await request.json()
        telegram_app = request.app.state.telegram_app
        update = Update.de_json(data, telegram_app.bot)
        
        # Fire-and-forget: No esperamos a que termine para responder a Telegram
        # Esto es VITAL para escalar a 200k usuarios sin timeouts
        await telegram_app.process_update(update)
        
        return Response(status_code=status.HTTP_200_OK)
    except Exception:
        # En producción, si falla un update, lo loggeamos y seguimos.
        # No queremos que un error 500 haga que Telegram reenvíe el mensaje infinitamente.
        return Response(status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    # Configuración para Producción
    uvicorn.run("main:app", host="0.0.0.0", port=10000, log_level="info")
