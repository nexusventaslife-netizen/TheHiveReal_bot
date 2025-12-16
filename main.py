import os
import logging
import asyncio
import httpx 
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from telegram import Update 
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict

# Importamos la lógica COMPLETA
from bot_logic import start, help_command, general_text_handler, invite_command, reset_command, button_handler, broadcast_command
import database as db
from cache import init_cache 

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- CONFIGURACIÓN DE OFERTAS (GEO-LOCALIZACIÓN) ---
OFFERS_BY_COUNTRY = {
    "ES": "Https://www.bybit.com/invite?ref=BBJWAX4", 
    "MX": "Https://www.bybit.com/invite?ref=BBJWAX4",
    "AR": "Https://app.airtm.com/ivt/jos3vkujiyj",     
    "DEFAULT": "https://freecash.com/r/XYN98"          
}

app = FastAPI()
bot_app = None

# --- RUTAS WEB ---
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
    """Detecta país y redirige a la mejor oferta CPA"""
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
    
    # 1. Iniciar Base de Datos
    await db.init_db()
    
    # 2. Conectar Caché (CRÍTICO)
    if db.r:
        await init_cache(db.r)
        logger.info("✅ CACHÉ CONECTADO")
    else:
        logger.warning("⚠️ ERROR: Caché no conectado")
    
    if TOKEN:
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # 3. Registrar Handlers (NO BORRAMOS NADA)
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        bot_app.add_handler(CommandHandler("broadcast", broadcast_command)) 
        
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
        
        await bot_app.initialize()
        await bot_app.start()
        
        # 4. Anti-Crash
        logger.info("🔪 Matando sesiones viejas...")
        try:
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            asyncio.create_task(run_polling_safely())
        except Exception as e:
            logger.error(f"Error limpiando webhooks: {e}")
    else:
        logger.error("❌ FALTA TOKEN")

async def run_polling_safely():
    try:
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    except Conflict:
        logger.warning("⚠️ Conflicto detectado. Reintentando...")
        await asyncio.sleep(5)
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error polling: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if bot_app:
        if bot_app.updater.running: await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await db.close_db()
