import os
import logging
import asyncio
import httpx 
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from telegram import Update 
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict

# Importamos la lógica (AGREGUÉ broadcast_command AQUÍ)
from bot_logic import start, help_command, general_text_handler, invite_command, reset_command, button_handler, broadcast_command
import database as db

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- CONFIGURACIÓN DE OFERTAS (TU CONFIGURACIÓN ORIGINAL) ---
OFFERS_BY_COUNTRY = {
    "US": "LINK_FREECASH_USA",    
    "ES": "LINK_BYBIT_SPAIN",     
    "MX": "LINK_BYBIT_MEXICO",    
    "AR": "LINK_BINANCE_ARG",     
    "DEFAULT": "https://otieu.com/4/10302294" 
}

app = FastAPI()
bot_app = None

# --- RUTAS WEB (INTACTAS) ---
@app.get("/ingreso")
async def entry_detect(request: Request):
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    if "," in str(client_ip): client_ip = str(client_ip).split(",")[0]
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"http://ip-api.com/json/{client_ip}", timeout=2.0)
    except: pass
    return RedirectResponse(url="/")

@app.get("/go")
async def redirect_tasks(request: Request):
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    if "," in str(client_ip): client_ip = str(client_ip).split(",")[0]
    target_url = OFFERS_BY_COUNTRY["DEFAULT"]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{client_ip}", timeout=2.0)
            data = resp.json()
            if data.get('status') == 'success':
                country = data.get('countryCode')
                target_url = OFFERS_BY_COUNTRY.get(country, OFFERS_BY_COUNTRY["DEFAULT"])
    except: pass
    return RedirectResponse(url=target_url)

@app.get("/")
async def read_index():
    try:
        with open("index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return {"status": "Falta index.html"}

# --- INICIO DEL BOT ---
@app.on_event("startup")
async def startup_event():
    global bot_app
    await db.init_db()
    
    if TOKEN:
        # 1. Configuración del Bot
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # 2. Handlers (AQUÍ AGREGUÉ EL BROADCAST SOLAMENTE)
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        
        # NUEVA LÍNEA AGREGADA (Solo esto cambié)
        bot_app.add_handler(CommandHandler("broadcast", broadcast_command)) 
        
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
        
        await bot_app.initialize()
        await bot_app.start()
        
        # 3. EL FIX DE LA MUERTE (INTACTO)
        logger.info("🔪 Matando sesiones viejas de Telegram...")
        try:
            # Esto borra cualquier conexión zombie que haya quedado en Render
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhooks eliminados. Iniciando Polling limpio.")
            
            # Iniciamos polling con manejo de errores específicos
            asyncio.create_task(run_polling_safely())
            
        except Exception as e:
            logger.error(f"Error limpiando webhooks: {e}")
    else:
        logger.error("❌ FALTA TOKEN")

async def run_polling_safely():
    """Función para reiniciar el polling si choca"""
    try:
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    except Conflict:
        logger.warning("⚠️ Conflicto detectado. Esperando 5 segundos para reintentar...")
        await asyncio.sleep(5)
        # Reintento agresivo
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error fatal en polling: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if bot_app:
        if bot_app.updater.running: await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await db.close_db()
