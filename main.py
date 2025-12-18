import os
import sys
import logging
import asyncio
import time
import signal
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

# --- SERVIDOR DE ALTO RENDIMIENTO (ASGI) ---
import uvicorn
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy()) # Aceleración C++
except ImportError:
    pass 

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# --- TELEGRAM BOT API (OPTIMIZADA) ---
from telegram import Update 
from telegram.ext import (
    Application, 
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters,
    Defaults
)
from telegram.request import HTTPXRequest # Crucial para el pooling
from telegram.error import Conflict, NetworkError, TimedOut

# --- MÓDULOS INTERNOS ---
import database as db
from loguru import logger

# ==============================================================================
# 1. CONFIGURACIÓN DE INFRAESTRUCTURA
# ==============================================================================

# Variables Críticas
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
SECRET_KEY = os.getenv("SECRET_KEY", "HIVE-SECURE-NODE-V300")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Configuración de Logging Profesional
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger("httpx").setLevel(logging.WARNING) # Silenciar ruido
logging.getLogger("telegram").setLevel(logging.INFO)

# Importación Defensiva de la Lógica
try:
    from bot_logic import (
        start_command, 
        help_command, 
        invite_command, 
        reset_command,
        button_handler, 
        general_text_handler, 
        broadcast_command
    )
except ImportError as e:
    logger.critical(f"❌ FALLO CRÍTICO DE IMPORTACIÓN (LÓGICA): {e}")
    sys.exit(1)

# Estado Global del Sistema
SYS_STATE = {
    "status": "BOOTING",
    "startup_time": time.time(),
    "updates_processed": 0,
    "errors_count": 0,
    "mode": "UNKNOWN"
}

bot_app: Optional[Application] = None

# ==============================================================================
# 2. CONSTRUCTOR DEL BOT (OPTIMIZADO PARA CARGA)
# ==============================================================================

def build_titan_bot() -> Application:
    """
    Construye la instancia del bot con parámetros de red agresivos.
    """
    if not TOKEN:
        logger.critical("❌ NO TELEGRAM TOKEN FOUND.")
        sys.exit(1)

    # Configuración de Requests (Connection Pooling)
    request_config = HTTPXRequest(
        connection_pool_size=1000,    # Soporta 1000 conexiones simultáneas
        read_timeout=15.0,            
        write_timeout=15.0,
        connect_timeout=10.0,
        pool_timeout=20.0
    )

    builder = ApplicationBuilder()
    builder.token(TOKEN)
    builder.request(request_config)
    builder.concurrent_updates(True) # Procesamiento paralelo real
    
    app = builder.build()

    # --- REGISTRO DE HANDLERS ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("invitar", invite_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Interacción Masiva
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))

    return app

# ==============================================================================
# 3. GESTOR DE CICLO DE VIDA
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orquestador Maestro."""
    global bot_app
    SYS_STATE["status"] = "INITIALIZING"
    logger.info("🚀 INICIANDO PROTOCOLO PANDORA V301 (TITAN MODE)...")

    # 1. CONEXIÓN A BASE DE DATOS
    try:
        await db.db.connect()
        if db.db.r: logger.success("✅ BASE DE DATOS LISTA")
    except Exception as e:
        logger.critical(f"🔥 ERROR FATAL DB: {e}")
    
    # 2. INICIAR BOT
    bot_app = build_titan_bot()
    await bot_app.initialize()
    await bot_app.start()
    
    # 3. CONFIGURACIÓN DE RED
    if WEBHOOK_URL:
        webhook_path = f"{WEBHOOK_URL}/webhook"
        logger.info(f"📡 Configurando Webhook en: {webhook_path}")
        try:
            await bot_app.bot.set_webhook(
                url=webhook_path,
                secret_token=SECRET_KEY,
                max_connections=100,
                drop_pending_updates=True
            )
            SYS_STATE["mode"] = "WEBHOOK"
            logger.success("✅ WEBHOOK ESTABLECIDO")
        except Exception as e:
            logger.error(f"❌ Error configurando Webhook: {e}")
    else:
        logger.warning("⚠️ MODO POLLING ACTIVO")
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(run_resilient_polling())
        SYS_STATE["mode"] = "POLLING"

    SYS_STATE["status"] = "OPERATIONAL"
    yield
    
    # 4. APAGADO LIMPIO
    logger.info("🛑 DETENIENDO SISTEMA...")
    if bot_app:
        if bot_app.updater.running: await bot_app.updater.stop()
        if bot_app.running: await bot_app.stop(); await bot_app.shutdown()
    await db.db.close()
    logger.success("✅ SISTEMA APAGADO CORRECTAMENTE")

# ==============================================================================
# 4. LÓGICA DE POLLING RESILIENTE
# ==============================================================================

async def run_resilient_polling():
    retry_delay = 1
    while True:
        try:
            logger.info("🛰️ Iniciando Long-Polling...")
            await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            while bot_app.updater.running: await asyncio.sleep(5)
            break
        except Conflict:
            logger.warning("⚠️ CONFLICTO. Esperando 10s...")
            await asyncio.sleep(10)
        except NetworkError:
            logger.error(f"⚠️ ERROR DE RED. Reintentando...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)
        except Exception as e:
            logger.critical(f"🔥 ERROR POLLING: {e}")
            await asyncio.sleep(5)

# ==============================================================================
# 5. SERVIDOR WEB FASTAPI
# ==============================================================================

app = FastAPI(title="HIVE CORE TITAN", version="301.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    uptime = int(time.time() - SYS_STATE["startup_time"])
    return HTMLResponse(f"""
    <html><body style="background:#0a0a0a;color:#00ff00;font-family:monospace;text-align:center;padding:10vh;">
    <h1>🧬 PANDORA HIVE V301</h1>
    <p>STATUS: {SYS_STATE['status']} | MODE: {SYS_STATE['mode']}</p>
    <p>UPTIME: {uptime}s | UPDATES: {SYS_STATE['updates_processed']}</p>
    </body></html>
    """)

@app.get("/health")
async def health_check():
    db_status = "connected" if db.db.r else "disconnected"
    if db_status == "disconnected": raise HTTPException(status_code=503, detail="DB Down")
    return {"status": "healthy", "database": db_status}

@app.get("/go")
async def cpa_redirect(request: Request):
    return RedirectResponse("https://freecash.com/r/XYN98")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_URL and secret != SECRET_KEY:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    try:
        payload = await request.json()
        update = Update.de_json(payload, bot_app.bot)
        await bot_app.process_update(update)
        SYS_STATE["updates_processed"] += 1
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"⚠️ Error Webhook: {e}")
        return JSONResponse(content={"ok": True}, status_code=200)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, access_log=False)
