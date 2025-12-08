import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import uvicorn

# --- IMPORTS PROPIOS ---
from database import init_db, close_db
# Importamos los handlers desde bot_logic
from bot_logic import (
    start, 
    process_email_input, 
    check_gate_callback, 
    menu_handler, 
    mine_tap_callback, 
    withdraw_callback,
    help_command
)

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- VARIABLES DE ENTORNO ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Ej: https://tu-app.onrender.com
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "supersecrettoken123") # Para seguridad del webhook

# Validaciones críticas
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ FALTAN VARIABLES DE ENTORNO: TELEGRAM_TOKEN o WEBHOOK_URL")

# --- LIFESPAN (INICIO Y CIERRE) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación: Inicio y Apagado."""
    
    # 1. INICIO: Conectar DB y Configurar Bot
    logger.info("🚀 Iniciando TheHiveReal Bot...")
    await init_db()
    
    # Construir la aplicación del bot
    application = Application.builder().token(TOKEN).build()
    
    # --- REGISTRO DE HANDLERS ---
    # Aquí conectamos la lógica de bot_logic.py
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_handler))
    
    # Flujo de Email (Captura cualquier texto si estamos esperando email)
    # Nota: En bot_logic debes manejar el estado usando user_data o conversation handler
    # Por simplicidad aquí capturamos texto general, filtraremos en la lógica
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_input))
    
    # Callbacks (Botones)
    application.add_handler(CallbackQueryHandler(check_gate_callback, pattern="^check_gate$"))
    application.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="^mine_tap$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    
    # Inicializar y configurar Webhook
    await application.initialize()
    await application.start()
    
    # Configurar el webhook en los servidores de Telegram
    webhook_endpoint = f"{WEBHOOK_URL}/telegram-webhook"
    logger.info(f"🔗 Configurando Webhook en: {webhook_endpoint}")
    await application.bot.set_webhook(
        url=webhook_endpoint, 
        secret_token=SECRET_TOKEN,
        allowed_updates=Update.ALL_TYPES
    )
    
    # Guardar la app del bot en el estado de FastAPI para usarla en las rutas
    app.state.telegram_app = application
    
    yield  # El servidor corre aquí
    
    # 2. APAGADO: Limpieza
    logger.info("🛑 Apagando Bot y Cerrando Conexiones...")
    await application.bot.delete_webhook()
    await application.stop()
    await application.shutdown()
    await close_db()

# --- INSTANCIA FASTAPI ---
app = FastAPI(lifespan=lifespan)

# --- RUTAS ---

@app.get("/", status_code=200)
@app.head("/", status_code=200)
async def health_check():
    """Ping simple para que Render sepa que estamos vivos."""
    return {"status": "online", "bot": "TheHiveReal"}

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """Recibe las actualizaciones de Telegram."""
    
    # Verificar Token Secreto (Seguridad)
    x_telegram_bot_api_secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if x_telegram_bot_api_secret_token != SECRET_TOKEN:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    # Procesar actualización
    try:
        data = await request.json()
        telegram_app = request.app.state.telegram_app
        
        update = Update.de_json(data, telegram_app.bot)
        
        # Enviar al procesador de PTB sin bloquear (fire-and-forget logic interna de PTB)
        await telegram_app.process_update(update)
        
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- RUTAS DE POSTBACK (CPA) ---
@app.get("/postback/secure")
async def postback_handler(request: Request):
    """
    Ruta para recibir confirmaciones de CPAGrip/OfferToro.
    Ejemplo: /postback/secure?subid={user_id}&payout={amount}&key={security_key}
    """
    params = request.query_params
    user_id = params.get("subid")
    payout = params.get("payout")
    
    # AQUÍ IMPLEMENTAREMOS LA VALIDACIÓN DE FIRMA MD5 MÁS ADELANTE
    # Por ahora solo loggeamos
    if user_id:
        logger.info(f"💰 POSTBACK RECIBIDO: User {user_id} ganó {payout}")
        # await add_balance(user_id, float(payout))
    
    return {"status": "success"}

# Para correr en local (si ejecutas python main.py)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
