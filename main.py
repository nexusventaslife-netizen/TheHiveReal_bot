import os
import logging
import asyncio
import httpx 
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from telegram import Update 
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict, NetworkError

# --- IMPORTACIÓN DE LÓGICA (Asegúrate que el archivo se llame bot_logic.py) ---
try:
    from bot_logic import start, help_command, general_text_handler, invite_command, reset_command, button_handler, broadcast_command
except ImportError:
    print("⚠️ CRÍTICO: No se encontró bot_logic.py. Asegúrate de guardar el código anterior con ese nombre.")
    # Funciones dummy para que no crashee si falta el archivo al auditar
    async def start(u,c): pass
    async def help_command(u,c): pass
    async def general_text_handler(u,c): pass
    async def invite_command(u,c): pass
    async def reset_command(u,c): pass
    async def button_handler(u,c): pass
    async def broadcast_command(u,c): pass

import database as db
from cache import init_cache 

# Configuración de Logs (Mejorada para Debugging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger("HiveMain")

# TOKEN Seguro
TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- CONFIGURACIÓN DE OFERTAS (GEO-LOCALIZACIÓN INTELIGENTE) ---
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

# --- RUTAS WEB & REDIRECCIÓN INTELIGENTE ---
@app.get("/ingreso")
async def entry_detect(request: Request):
    """Ruta de entrada para capturar analíticas simples"""
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    if "," in str(client_ip): client_ip = str(client_ip).split(",")[0]
    
    # Aquí podríamos guardar la IP en Redis para analíticas de tráfico
    return RedirectResponse(url="/")

@app.get("/go")
async def redirect_tasks(request: Request):
    """Detecta país y redirige a la mejor oferta CPA con Fallback rápido"""
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    if "," in str(client_ip): client_ip = str(client_ip).split(",")[0]
    
    target_url = OFFERS_BY_COUNTRY["DEFAULT"]
    
    try:
        # Timeout corto (1.5s) para que el usuario no espere. Si falla, va al default.
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{client_ip}", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    country = data.get('countryCode')
                    target_url = OFFERS_BY_COUNTRY.get(country, OFFERS_BY_COUNTRY["DEFAULT"])
                    logger.info(f"🌍 Redirección: IP {client_ip} -> {country} -> {target_url}")
    except Exception as e:
        logger.warning(f"⚠️ Fallo GeoIP ({e}). Usando Default.")
        
    return RedirectResponse(url=target_url)

@app.get("/")
async def read_index():
    try:
        with open("index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>SYSTEM ERROR: Index Missing</h1>", status_code=404)

@app.get("/health")
async def health_check():
    """Endpoint para que Render/Railway sepan que estamos vivos"""
    return {"status": "ok", "hive": "online"}

# --- INICIO DEL BOT (CICLO DE VIDA) ---
@app.on_event("startup")
async def startup_event():
    global bot_app
    
    logger.info("🚀 INICIANDO SISTEMA HIVE V48.0...")
    
    # 1. Iniciar Base de Datos
    await db.init_db()
    
    # 2. Conectar Caché (CRÍTICO)
    if db.r:
        await init_cache(db.r)
        logger.info("✅ CACHÉ CONECTADO")
    else:
        logger.warning("⚠️ ERROR: Caché no conectado (Redis falló)")
    
    if TOKEN:
        try:
            bot_app = ApplicationBuilder().token(TOKEN).build()
            
            # 3. Registrar Handlers
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("help", help_command))
            bot_app.add_handler(CommandHandler("invitar", invite_command))
            bot_app.add_handler(CommandHandler("reset", reset_command))
            # Comentado si no tienes la funcion broadcast implementada en bot_logic aun
            # bot_app.add_handler(CommandHandler("broadcast", broadcast_command)) 
            
            bot_app.add_handler(CallbackQueryHandler(button_handler))
            bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
            
            await bot_app.initialize()
            await bot_app.start()
            
            # 4. Anti-Crash & Polling Seguro
            logger.info("🔪 Limpiando webhooks antiguos...")
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            
            # Ejecutar polling en background de forma segura
            asyncio.create_task(run_polling_safely())
            
        except Exception as e:
            logger.critical(f"🔥 ERROR FATAL AL INICIAR BOT: {e}")
    else:
        logger.error("❌ FALTA TELEGRAM_TOKEN EN VARIABLES DE ENTORNO")

async def run_polling_safely():
    """Ejecuta el polling con reinicio automático anti-caídas"""
    retry_delay = 5
    while True:
        try:
            logger.info("📡 Iniciando Polling...")
            # allowed_updates optimiza el ancho de banda
            await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            break # Si sale del start_polling normalmente, rompemos el bucle (shutdown)
        except Conflict:
            logger.warning("⚠️ Conflicto de Webhook/Polling. Otra instancia está corriendo.")
            await asyncio.sleep(retry_delay)
            # Intentar matar el webhook otra vez
            try: await bot_app.bot.delete_webhook() 
            except: pass
        except NetworkError:
            logger.error(f"⚠️ Error de Red. Reintentando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60) # Exponential backoff hasta 60s
        except Exception as e:
            logger.error(f"🔥 Error desconocido en Polling: {e}. Reiniciando...")
            await asyncio.sleep(5)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 APAGANDO SISTEMA HIVE...")
    if bot_app:
        if bot_app.updater.running:
            await bot_app.updater.stop()
        if bot_app.running:
            await bot_app.stop()
            await bot_app.shutdown()
    await db.close_db()
