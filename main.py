import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Importamos tus módulos
import bot_logic
import database as db

# --- CONFIGURACIÓN ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Ej: https://tu-app.onrender.com/webhook
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "hive_secret_123")  # Seguridad extra de Telegram

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("Hive.Main")

# --- LIFESPAN (ARRANQUE Y CIERRE) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    1. Conecta la Base de Datos.
    2. Inicia la App de Telegram.
    3. Configura el Webhook.
    """
    # 1. INICIAR DB
    await db.init_db()
    
    # 2. CONSTRUIR BOT (Aquí está lo que pedías)
    global application
    application = ApplicationBuilder().token(TOKEN).build()

    # --- REGISTRO DE COMANDOS (HANDLERS) ---
    # Comandos Básicos
    application.add_handler(CommandHandler("start", bot_logic.start))
    application.add_handler(CommandHandler("help", bot_logic.help_command))
    
    # Nuevos Comandos (Sistema de Referidos)
    application.add_handler(CommandHandler("invitar", bot_logic.invitar_menu))
    application.add_handler(CommandHandler("perfil", bot_logic.perfil_menu))
    
    # Comando Dev (Reset para pruebas)
    application.add_handler(CommandHandler("reset", bot_logic.reset_me))
    
    # Handler de Texto (Para el código HIVE-777)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_logic.code_handler))
    
    # Handler de Botones (Si usas callbacks en el futuro)
    # application.add_handler(CallbackQueryHandler(bot_logic.button_handler))

    # 3. INICIAR BOT
    await application.initialize()
    await application.start()
    
    # 4. SET WEBHOOK
    # Le decimos a Telegram dónde enviar los mensajes
    webhook_endpoint = f"{WEBHOOK_URL}/webhook"
    await application.bot.set_webhook(url=webhook_endpoint, secret_token=SECRET_TOKEN)
    logger.info(f"✅ Webhook configurado en: {webhook_endpoint}")

    yield  # La app corre aquí...

    # --- CIERRE ---
    logger.info("🛑 Apagando aplicación...")
    await application.stop()
    await application.shutdown()
    await db.close_db()

# --- FASTAPI APP ---
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def index():
    return {"status": "The Hive Bot is Running 🐝"}

@app.get("/health")
async def health_check():
    """Endpoint para que Render sepa que estamos vivos"""
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Recibe las actualizaciones de Telegram"""
    
    # 1. Verificar Token de Seguridad (Anti-Hack)
    telegram_token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if telegram_token_header != SECRET_TOKEN:
        return Response(content="Unauthorized", status_code=403)

    # 2. Procesar Update
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # Enviar al ApplicationBuilder para que decida qué handler usar
        await application.process_update(update)
        
        return Response(content="OK", status_code=200)
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        return Response(content="Error", status_code=500)
