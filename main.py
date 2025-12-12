import os
import logging
import asyncio
import httpx 
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from telegram import Update 
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict

# Importamos la lógica COMPLETA (incluyendo broadcast)
from bot_logic import start, help_command, general_text_handler, invite_command, reset_command, button_handler, broadcast_command
import database as db

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- CONFIGURACIÓN DE OFERTAS (LIMPIO Y SIN ERRORES) ---
# Hemos quitado USA y Binance. Solo usamos tus links 100% reales.
OFFERS_BY_COUNTRY = {
    # Si detecta España o México, manda a Bybit (Tu High Ticket)
    "ES": "Https://www.bybit.com/invite?ref=BBJWAX4", 
    "MX": "Https://www.bybit.com/invite?ref=BBJWAX4",
    
    # Si detecta Argentina, manda a AirTM (Tu link real)
    "AR": "Https://app.airtm.com/ivt/jos3vkujiyj",    
    
    # Para TODO el resto del mundo (incluido Uruguay, USA, etc), usa Freecash o Publicidad
    # He puesto Freecash como predeterminado porque paga bien en todos lados
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
    """
    Redirección inteligente:
    Detecta el país del usuario y lo manda a la mejor oferta (Bybit, AirTM o Freecash).
    """
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    if "," in str(client_ip): client_ip = str(client_ip).split(",")[0]
    
    target_url = OFFERS_BY_COUNTRY["DEFAULT"] # Por defecto Freecash
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{client_ip}", timeout=2.0)
            data = resp.json()
            if data.get('status') == 'success':
                country = data.get('countryCode')
                # Si el país está en nuestra lista (ES, MX, AR), cambia el link. Si no, usa Default.
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
        
        # 2. Handlers
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        bot_app.add_handler(CommandHandler("broadcast", broadcast_command)) 
        
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
        
        await bot_app.initialize()
        await bot_app.start()
        
        # 3. EL FIX DE LA MUERTE (Anti-Crash)
        logger.info("🔪 Matando sesiones viejas de Telegram...")
        try:
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhooks eliminados. Iniciando Polling limpio.")
            asyncio.create_task(run_polling_safely())
        except Exception as e:
            logger.error(f"Error limpiando webhooks: {e}")
    else:
        logger.error("❌ FALTA TOKEN")

async def run_polling_safely():
    """Reinicia el polling si Telegram da error de conflicto"""
    try:
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    except Conflict:
        logger.warning("⚠️ Conflicto detectado. Reintentando en 5s...")
        await asyncio.sleep(5)
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
