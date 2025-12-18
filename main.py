import os
import logging
import asyncio
import httpx 
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from telegram import Update 
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict, NetworkError

# Importamos la lógica masiva
try:
    from bot_logic import (
        start, help_command, general_text_handler, invite_command, 
        button_handler
    )
except ImportError as e:
    print(f"⚠️ CRÍTICO: Error importando bot_logic: {e}")
    # Fallback para evitar crash en deploy
    async def start(u,c): pass
    async def help_command(u,c): pass
    async def general_text_handler(u,c): pass
    async def invite_command(u,c): pass
    async def button_handler(u,c): pass

import database as db

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger("HiveMain")

# TOKEN
TOKEN = os.getenv("TELEGRAM_TOKEN")

# SISTEMA DE GEO-DIRECCIONAMIENTO (CPA INTELIGENTE)
OFFERS_BY_COUNTRY = {
    "ES": "https://www.bybit.com/invite?ref=BBJWAX4", 
    "MX": "https://www.bybit.com/invite?ref=BBJWAX4",
    "AR": "https://app.airtm.com/ivt/jos3vkujiyj",      
    "CO": "https://www.bybit.com/invite?ref=BBJWAX4",
    "VE": "https://app.airtm.com/ivt/jos3vkujiyj",
    "UY": "https://wise.com/invite/ahpc/josealejandrop73",
    "DEFAULT": "https://freecash.com/r/XYN98"          
}

app = FastAPI()
bot_app = None

# ==============================================================================
# RUTAS WEB (FASTAPI)
# ==============================================================================

@app.get("/ingreso")
async def entry_detect(request: Request):
    """Punto de entrada para analytics futuros."""
    return RedirectResponse(url="/")

@app.get("/go")
async def redirect_tasks(request: Request):
    """
    Ruta inteligente para ofertas CPA.
    Detecta la IP del usuario, consulta una API de GeoIP y redirige
    a la oferta que mejor paga para ese país.
    """
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    # Limpieza de IP si hay proxys
    if "," in str(client_ip): client_ip = str(client_ip).split(",")[0]
    
    target_url = OFFERS_BY_COUNTRY["DEFAULT"]
    
    try:
        # Usamos httpx asíncrono para no bloquear el bot
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{client_ip}", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    country = data.get('countryCode')
                    target_url = OFFERS_BY_COUNTRY.get(country, OFFERS_BY_COUNTRY["DEFAULT"])
                    logger.info(f"🌍 GEO-REDIRECT: {client_ip} ({country}) -> {target_url}")
    except Exception as e:
        logger.warning(f"⚠️ Fallo GeoIP: {e}")
        
    return RedirectResponse(url=target_url)

@app.get("/")
async def read_index():
    return HTMLResponse(content="""
    <html>
        <body style="background: black; color: #00ff00; font-family: monospace; text-align: center; padding-top: 20%;">
            <h1>PANDORA HIVE V200.0</h1>
            <p>SYSTEM STATUS: <span style="color: cyan;">OPTIMAL</span></p>
            <p>HIVE MIND: CONNECTED</p>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check para que Render no mate el servicio."""
    return {"status": "ok", "hive": "genesis", "version": "200.0"}

# ==============================================================================
# LIFECYCLE DE TELEGRAM
# ==============================================================================

@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor."""
    global bot_app
    
    logger.info("🚀 INICIANDO PROTOCOLO PANDORA V200.0 (ELITE BUILD)...")
    
    # 1. Iniciar Base de Datos
    await db.init_db()
    
    # 2. Iniciar Bot
    if TOKEN:
        try:
            bot_app = ApplicationBuilder().token(TOKEN).build()
            
            # Registrar Comandos
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("help", help_command))
            bot_app.add_handler(CommandHandler("invitar", invite_command))
            
            # Registrar Handlers Interactivos
            bot_app.add_handler(CallbackQueryHandler(button_handler))
            bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
            
            await bot_app.initialize()
            await bot_app.start()
            
            # Limpieza y arranque de Polling
            logger.info("🔪 Limpiando webhooks residuales...")
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            
            # Ejecutar polling en background task
            asyncio.create_task(run_polling_safely())
            
        except Exception as e:
            logger.critical(f"🔥 ERROR FATAL INICIANDO TELEGRAM: {e}")
    else:
        logger.error("❌ FALTA TELEGRAM_TOKEN EN VARIABLES DE ENTORNO")

async def run_polling_safely():
    """Mantiene el bot vivo y reinicia en caso de errores de red."""
    retry_delay = 5
    while True:
        try:
            logger.info("📡 Conectando a la Matriz de Telegram...")
            await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            break 
        except Conflict:
            logger.warning("⚠️ Conflicto de Webhook (Otra instancia activa). Esperando...")
            await asyncio.sleep(retry_delay)
            try: await bot_app.bot.delete_webhook() 
            except: pass
        except NetworkError:
            logger.error(f"⚠️ Error de Red. Reintentando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)
        except Exception as e:
            logger.error(f"🔥 Error desconocido en Polling: {e}")
            await asyncio.sleep(5)

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al apagar."""
    logger.info("🛑 APAGANDO SISTEMA...")
    if bot_app:
        if bot_app.updater.running:
            await bot_app.updater.stop()
        if bot_app.running:
            await bot_app.stop()
            await bot_app.shutdown()
    await db.close_db()
