import os
import sys
import logging
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

# Server & Network
import uvicorn
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

# Telegram Imports
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, Application
)
from telegram.error import Conflict, NetworkError, TimedOut

# Internal Modules
import database as db
from loguru import logger

# Importación Segura
try:
    from bot_logic import (
        start_command, help_command, invite_command, reset_command,
        button_handler, general_text_handler
    )
except ImportError as e:
    logger.critical(f"FATAL: No se pudo importar bot_logic: {e}")
    sys.exit(1)

# Configuración de Logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelname, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0)

# Variables de Entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    logger.critical("TELEGRAM_TOKEN no configurado.")
    sys.exit(1)

bot_app: Optional[Application] = None
start_time = time.time()

# ==============================================================================
# LIFESPAN MANAGER (Ciclo de Vida)
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor de arranque y parada seguros."""
    global bot_app
    logger.info("🚀 INICIANDO SISTEMA HIVE V200.0 (HEAVY LOAD READY)...")
    
    # 1. DB Connect
    try:
        await db.db.connect()
    except Exception as e:
        logger.error(f"Error DB: {e}")
    
    # 2. Bot Connect
    if TOKEN:
        bot_app = ApplicationBuilder().token(TOKEN).build()
        
        # Handlers
        bot_app.add_handler(CommandHandler("start", start_command))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("invitar", invite_command))
        bot_app.add_handler(CommandHandler("reset", reset_command))
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
        
        await bot_app.initialize()
        await bot_app.start()
        
        # Webhook vs Polling
        if WEBHOOK_URL:
            logger.info(f"📡 Modo Webhook: {WEBHOOK_URL}")
            await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        else:
            logger.info("📡 Modo Polling Asíncrono")
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            asyncio.create_task(polling_loop())
            
    yield
    
    # Shutdown
    logger.info("🛑 APAGANDO...")
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await db.db.close()

# ==============================================================================
# SERVIDOR WEB FASTAPI
# ==============================================================================

app = FastAPI(lifespan=lifespan, docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    uptime = int(time.time() - start_time)
    return HTMLResponse(f"""
    <body style="background:#000;color:#0f0;font-family:monospace;text-align:center;padding-top:100px;">
        <h1>🧬 HIVE SYSTEM ONLINE</h1>
        <p>UPTIME: {uptime}s</p>
        <p>STATUS: OPTIMAL</p>
    </body>
    """)

@app.get("/health")
async def health():
    return {"status": "ok", "db": "connected" if db.db.r else "error"}

@app.get("/go")
async def cpa_redirect(request: Request):
    """Geo-Redirección CPA Inteligente."""
    # Aquí iría lógica GeoIP real
    # Por defecto
    return RedirectResponse("https://freecash.com/r/XYN98")

@app.post("/webhook")
async def webhook_handler(request: Request):
    if not bot_app: return JSONResponse({"error": "No bot"}, status_code=500)
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ==============================================================================
# GESTOR DE POLLING (RESILIENTE)
# ==============================================================================

async def polling_loop():
    """Bucle infinito de polling que no muere."""
    while True:
        try:
            await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            # Mantener vivo mientras el updater corra
            while bot_app.updater.running:
                await asyncio.sleep(10)
            break
        except Conflict:
            logger.warning("Conflicto de Webhook. Esperando...")
            await asyncio.sleep(5)
            try: await bot_app.bot.delete_webhook()
            except: pass
        except NetworkError:
            logger.error("Error de Red. Reintentando...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.critical(f"Error Polling: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")
