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

# Import bot_logic (con tus handlers + los nuevos HSP)
try:
    from bot_logic import (
        start_command, help_cmd, invite_cmd, reset_cmd,
        button_handler, general_text_handler, broadcast_cmd
    )
except ImportError as e:
    logger.critical(f"❌ FALLO IMPORT BOT_LOGIC: {e}")
    sys.exit(1)

import database as db

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.critical("❌ TELEGRAM_TOKEN no definido")
    sys.exit(1)

WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")  # e.g., https://tu-bot.onrender.com
PORT = int(os.getenv("PORT", 10000))

# Secret token más seguro: usa env o genera random
SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", os.urandom(32).hex())  # 64 chars, válido A-Z0-9

bot_app: Optional[Application] = None

def build_bot() -> Application:
    req = HTTPXRequest(
        connection_pool_size=1000,
        read_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=60.0
    )
    app = Application.builder().token(TOKEN).request(req).build()

    # Handlers (añade más si usas HSP)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("invitar", invite_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))

    # Aquí puedes añadir JobQueue tasks (regen, eventos, leaderboards)
    # Ejemplo: app.job_queue.run_repeating(background_regen, interval=60)

    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app
    logger.info("🚀 INICIANDO THE ONE HIVE V13.1 HSP")

    await db.db.connect()

    bot_app = build_bot()
    await bot_app.initialize()
    await bot_app.start()

    if WEBHOOK_URL:
        webhook_uri = f"{WEBHOOK_URL.rstrip('/')}/webhook"
        logger.info(f"📡 Configurando webhook: {webhook_uri}")

        for attempt in range(5):  # Retries para set_webhook
            try:
                await bot_app.bot.set_webhook(
                    url=webhook_uri,
                    secret_token=SECRET_TOKEN,
                    max_connections=100,
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                logger.success("✅ Webhook configurado correctamente")
                break
            except (NetworkError, TimedOut) as e:
                logger.warning(f"⚠️ Intento {attempt+1}/5 webhook falló: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"❌ Error fatal webhook: {e}")
                break
    else:
        logger.warning("⚠️ Modo Polling activado (no WEBHOOK_URL)")
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(run_polling())

    yield

    # Shutdown graceful
    if bot_app:
        await bot_app.updater.stop() if bot_app.updater else None
        await bot_app.stop()
        await bot_app.shutdown()
    await db.db.close()
    logger.info("🛑 Bot detenido")

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
    return HTMLResponse("<h1>🏰 THE ONE HIVE ONLINE - V13.1 HSP</h1>")

@app.get("/health")
async def health():
    webhook_info = await bot_app.bot.get_webhook_info() if bot_app else {}
    return {
        "status": "ok",
        "webhook": webhook_info.get("url", "polling"),
        "pending_updates": webhook_info.get("pending_update_count", 0),
        "nodes": (await db.db.get_global_stats())["nodes"]
    }

@app.post("/webhook")
async def webhook(request: Request):
    if WEBHOOK_URL:
        sec = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if sec != SECRET_TOKEN:
            logger.warning(f"🚫 Webhook auth falló: {sec[:10] if sec else None}")
            raise HTTPException(status_code=403, detail="Forbidden")

    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        if update:
            asyncio.create_task(bot_app.process_update(update))  # Background para no bloquear
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        return JSONResponse({"ok": True})  # Siempre 200 para evitar retries infinitos

async def run_polling():
    logger.info("🔄 Iniciando polling fallback...")
    while True:
        try:
            await bot_app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False
            )
            break
        except (Conflict, NetworkError) as e:
            logger.warning(f"Polling conflict: {e} - reintentando...")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, workers=1)  # Render usa 1 worker
