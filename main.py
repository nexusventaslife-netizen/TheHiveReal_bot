import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("TheOneHive")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta configurar TELEGRAM_TOKEN en Render")

app = FastAPI(title="TheOneHive Backend (mínimo y limpio)")

telegram_app: Application | None = None


# ---------------------------------------------------------------------
# BOT HANDLERS
# ---------------------------------------------------------------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "🧠 Bienvenido a TheOneHive\n\n"
        f"Hola {user.first_name}, la plataforma está ONLINE.\n"
        "Este es el bot oficial donde vas a poder hacer tareas, ganar dinero,\n"
        "invitar amigos y más.\n\n"
        "Esta es la versión base. A partir de aquí vamos a ir agregando\n"
        "dashboard, tareas, referidos y retiros."
    )
    if update.message:
        await update.message.reply_text(text)


async def init_telegram_app() -> Application:
    """Crea una única instancia de Application (sin Updater)."""
    global telegram_app

    if telegram_app:
        return telegram_app

    logger.info("Iniciando aplicación de Telegram (TheOneHive) ...")
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start_cmd))

    await telegram_app.initialize()
    logger.info("Aplicación de Telegram inicializada.")
    return telegram_app


# ---------------------------------------------------------------------
# FASTAPI EVENTS
# ---------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Iniciando backend de TheOneHive...")
    app_telegram = await init_telegram_app()

    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/telegram/webhook/{TELEGRAM_TOKEN}"
        await app_telegram.bot.delete_webhook(drop_pending_updates=True)
        await app_telegram.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook configurado: {webhook_url}")
    else:
        logger.warning(
            "RENDER_EXTERNAL_URL no configurado. No se configuró el webhook de Telegram."
        )

    logger.info("✅ Backend de TheOneHive iniciado correctamente.")


@app.on_event("shutdown")
async def on_shutdown():
    global telegram_app
    logger.info("🛑 Apagando backend de TheOneHive...")
    if telegram_app:
        await telegram_app.shutdown()
        await telegram_app.stop()
        telegram_app = None
    logger.info("🛑 Backend apagado.")


# ---------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "project": "TheOneHive"}


@app.get("/")
async def root():
    return {
        "name": "TheOneHive",
        "status": "online",
        "message": "Backend mínimo funcionando",
    }


@app.post("/telegram/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN:
        return JSONResponse(status_code=403, content={"detail": "Invalid token"})

    data = await request.json()

    app_telegram = await init_telegram_app()
    update = Update.de_json(data, app_telegram.bot)
    await app_telegram.process_update(update)

    return {"ok": True}
