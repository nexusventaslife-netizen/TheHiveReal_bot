import os
import sys
import logging
import asyncio
import time
import re
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from telegram import Update 
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, 
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.request import HTTPXRequest
from telegram.error import Conflict, NetworkError

import database as db
from loguru import logger

# Importación Segura
try:
    from bot_logic import (
        start_command, help_cmd, invite_cmd, reset_cmd,
        button_handler, general_text_handler, broadcast_cmd
    )
except ImportError as e:
    logger.critical(f"❌ FALLO IMPORT: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))

# --- CORRECCIÓN DEL ERROR DE SECRET TOKEN ---
# Telegram solo permite A-Z, a-z, 0-9, _ y -
# Esta función limpia tu variable de entorno para que no rompa el servidor.
raw_token = os.getenv("SECRET_TOKEN", "HIVE-TITAN-V302")
SECRET_TOKEN = re.sub(r'[^a-zA-Z0-9_-]', '', raw_token) # Elimina espacios y símbolos raros
if not SECRET_TOKEN: SECRET_TOKEN = "HIVE-DEFAULT-SECURE" # Fallback por seguridad

bot_app: Optional[Application] = None

def build_bot() -> Application:
    # Pool de 1000 conexiones para aguantar 300k usuarios
    req = HTTPXRequest(connection_pool_size=1000)
    app = ApplicationBuilder().token(TOKEN).request(req).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("invitar", invite_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), general_text_handler))
    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app
    logger.info("🚀 STARTING TITAN V302...")
    logger.info(f"🔒 Secret Token Sanitizado: {SECRET_TOKEN}") # Log para verificar

    await db.db.connect()
    
    bot_app = build_bot()
    await bot_app.initialize()
    await bot_app.start()
    
    if WEBHOOK_URL:
        logger.info(f"📡 Webhook: {WEBHOOK_URL}")
        # Aquí es donde fallaba antes. Ahora SECRET_TOKEN está limpio.
        await bot_app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook", 
            secret_token=SECRET_TOKEN,
            max_connections=100,
            drop_pending_updates=True
        )
    else:
        logger.warning("⚠️ Polling Mode")
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(run_polling())

    yield
    
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await db.db.close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root(): return HTMLResponse("<h1>HIVE ONLINE</h1>")

@app.get("/health")
async def health(): return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    # Verificación de seguridad usando el token limpio
    sec = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_URL and sec != SECRET_TOKEN:
        return JSONResponse(status_code=403, content={"error": "Auth Failed"})
    
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"Webhook Err: {e}")
        return JSONResponse(content={"ok": True})

async def run_polling():
    while True:
        try:
            await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            break
        except Conflict: await asyncio.sleep(5)
        except Exception: await asyncio.sleep(5)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
