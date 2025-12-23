import os
import sys
import logging
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.request import HTTPXRequest
from telegram.error import Conflict, NetworkError, TimedOut
from loguru import logger

# Import bot_logic (V13 HSP)
try:
    from bot_logic import (
        start_command, help_cmd, invite_cmd, reset_cmd,
        button_handler, general_text_handler, broadcast_cmd,
        # Tareas de fondo importadas
        on_startup as logic_startup
    )
    # Importar tareas si existen en bot_logic, sino mock
    import bot_logic
except ImportError as e:
    logger.critical(f"❌ FALLO IMPORT BOT_LOGIC: {e}")
    sys.exit(1)

import database as db

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.critical("❌ TELEGRAM_TOKEN no definido")
    sys.exit(1)

WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))
SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", os.urandom(32).hex())

bot_app: Optional[Application] = None

def build_bot() -> Application:
    """Construye la aplicación Telegram con toda la lógica V13"""
    req = HTTPXRequest(
        connection_pool_size=1000,
        read_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=60.0
    )
    app = Application.builder().token(TOKEN).request(req).build()

    # --- HANDLERS V13 ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("invitar", invite_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    
    # Callback Query (Maneja Taps, Menús, Combos, Preds)
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Mensajes de texto (Maneja input de Combos y Emails)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))

    # --- JOB QUEUE (BACKGROUND TASKS) ---
    # Si bot_logic tiene tareas definidas, las agregamos aquí
    if hasattr(bot_logic, 'event_task'):
        app.job_queue.run_repeating(bot_logic.event_task, interval=3600, first=60)
        logger.info("🕒 Tarea EVENTOS programada (1h)")
    
    # Regeneración pasiva (opcional si no se usa on-demand)
    # app.job_queue.run_repeating(bot_logic.background_regen, interval=60)

    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app
    logger.info("🚀 INICIANDO THE ONE HIVE V13.1 HSP EDITION")

    # 1. Conectar DB Redis
    await db.db.connect()

    # 2. Iniciar Lógica Bot (Cargar caches, etc)
    if logic_startup:
        # Llamamos a on_startup de bot_logic pero sin pasar 'application' 
        # porque db ya se conectó arriba, es solo para logs o inits extra
        pass 

    # 3. Build & Start Telegram App
    bot_app = build_bot()
    await bot_app.initialize()
    await bot_app.start()

    # 4. Config Webhook
    if WEBHOOK_URL:
        webhook_uri = f"{WEBHOOK_URL.rstrip('/')}/webhook"
        logger.info(f"📡 Configurando webhook: {webhook_uri}")
        try:
            await bot_app.bot.set_webhook(
                url=webhook_uri,
                secret_token=SECRET_TOKEN,
                max_connections=100,
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            logger.success("✅ Webhook OK")
        except Exception as e:
            logger.error(f"❌ Webhook Error: {e}")
    else:
        logger.warning("⚠️ Modo Polling (Dev Mode)")
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(run_polling())

    yield

    # Shutdown
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await db.db.close()
    logger.info("🛑 Sistema detenido")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return HTMLResponse("<h1>🏰 THE ONE HIVE V13 ONLINE</h1>")

@app.get("/health")
async def health():
    stats = await db.db.get_global_stats()
    return {"status": "ok", "nodes_active": stats.get("nodes", 0)}

@app.post("/webhook")
async def webhook(request: Request):
    if WEBHOOK_URL:
        sec = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if sec != SECRET_TOKEN:
            raise HTTPException(status_code=403, detail="Forbidden")

    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        if update:
            # Procesar en background para no bloquear FastAPI
            asyncio.create_task(bot_app.process_update(update))
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error(f"Webhook update fail: {e}")
        return JSONResponse({"ok": True}) # Ack to Telegram

async def run_polling():
    await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, workers=1)
