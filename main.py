"""
TheOneHive - Backend + Bot Telegram optimizado para Render

Este archivo contiene:

- FastAPI app (para Render, Python 3.13).
- Bot de Telegram usando python-telegram-bot v20 (Application, sin Updater).
- Base de datos SQLite con aiosqlite (sin drivers nativos).
- Esqueleto de todas las funciones clave que hablamos:

  * Registro /start con código de referido
  * Planes FREE y PREMIUM (15 USD/mes, simulado)
  * Dashboard con estadísticas
  * Sistema básico de referidos
  * Tareas (mock) preparadas para integrarse con redes CPA
  * Retiros (esqueleto)
  * Config por país (daily cap, métodos de pago, mínimos)
  * Tokens internos (moneda invisible)
  * Preparado para:
      - Algoritmo de optimización de tareas por país / usuario
      - Integración con pagos (Stripe/PayPal/Cripto)
      - Integración con redes externas (CPA, encuestas)
      - Datos agregados / publicidad / NFTs (a implementar después)

Para Render:

- Start Command:
    uvicorn main:app --host 0.0.0.0 --port $PORT

- Env vars mínimas:
    TELEGRAM_TOKEN      -> token de BotFather
    RENDER_EXTERNAL_URL -> URL pública de Render (https://....onrender.com)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import aiosqlite
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------
# CONFIGURACIÓN BÁSICA Y CONSTANTES
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("TheOneHive")

APP_NAME = "TheOneHive"
DB_PATH = os.environ.get("THEONEHIVE_DB_PATH", "theonehive.db")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

if not TELEGRAM_TOKEN:
    # Esto hace que el error sea claro en Render si falta el token
    raise RuntimeError("Falta configurar TELEGRAM_TOKEN en las variables de entorno de Render")

PREMIUM_PRICE_USD = 15.0  # Precio mensual del plan Premium (simulado)

# Config simple por país (ejemplo – puedes extenderlo)
COUNTRY_CONFIG: Dict[str, Dict[str, Any]] = {
    "US": {
        "name": "United States",
        "daily_cap_usd": 180,
        "currency": "USD",
        "payment_methods": ["paypal", "stripe", "venmo", "crypto"],
        "min_withdraw_usd": 5,
    },
    "MX": {
        "name": "México",
        "daily_cap_usd": 60,
        "currency": "MXN",
        "payment_methods": ["paypal", "oxxo", "spei"],
        "min_withdraw_usd": 2,
    },
    "GLOBAL": {
        "name": "Global",
        "daily_cap_usd": 80,
        "currency": "USD",
        "payment_methods": ["paypal", "binance", "wise", "crypto"],
        "min_withdraw_usd": 2,
    },
    # Aquí puedes añadir AR, CO, ES, BR, VE, NG, AU, IN, ZA, etc.
}

# Teclado principal del bot
MAIN_KEYBOARD = [
    ["🎯 Tareas", "📊 Dashboard"],
    ["👥 Referidos", "💳 Plan"],
    ["💸 Retirar", "⚙️ Configurar"],
]

# ---------------------------------------------------------------------
# FASTAPI APP Y BOT APP
# ---------------------------------------------------------------------

app = FastAPI(title=f"{APP_NAME} Backend")

telegram_app: Optional[Application] = None

# ---------------------------------------------------------------------
# UTILIDADES DE BASE DE DATOS (SQLite + aiosqlite)
# ---------------------------------------------------------------------


async def init_db() -> None:
    """
    Crea tablas mínimas si no existen.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              telegram_id        INTEGER PRIMARY KEY,
              first_name         TEXT,
              username           TEXT,
              email              TEXT,
              email_verified     INTEGER DEFAULT 0,
              country_code       TEXT DEFAULT 'GLOBAL',
              plan               TEXT DEFAULT 'FREE',
              referral_code      TEXT,
              referred_by        INTEGER,
              tokens             INTEGER DEFAULT 0,
              total_earned       REAL DEFAULT 0,
              pending_payout     REAL DEFAULT 0,
              total_withdrawn    REAL DEFAULT 0,
              tasks_completed    INTEGER DEFAULT 0,
              referrals_count    INTEGER DEFAULT 0,
              subscription_until TEXT,
              created_at         TEXT,
              last_active        TEXT
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
              id                 INTEGER PRIMARY KEY AUTOINCREMENT,
              referrer_id        INTEGER,
              referred_id        INTEGER,
              commission_earned  REAL DEFAULT 0,
              created_at         TEXT
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS task_completions (
              id                  INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id             INTEGER,
              task_id             INTEGER,
              reward_user_usd     REAL,
              reward_referrer_usd REAL,
              status              TEXT,
              completed_at        TEXT
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS withdrawals (
              id               INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id          INTEGER,
              amount_usd       REAL,
              method           TEXT,
              destination      TEXT,
              status           TEXT,
              created_at       TEXT,
              processed_at     TEXT
            );
            """
        )

        await db.commit()

    logger.info("SQLite DB inicializada para TheOneHive.")


async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        await cur.close()
    return dict(row) if row else None


async def create_or_update_user(
    telegram_id: int,
    first_name: str,
    username: str,
    referral_code: Optional[str] = None,
) -> dict:
    """
    Crea el usuario si no existe, o actualiza last_active si ya existe.
    Maneja 1 nivel de referidos.
    """
    now = datetime.utcnow().isoformat()

    existing = await get_user(telegram_id)
    if existing:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET first_name=?, username=?, last_active=? WHERE telegram_id=?",
                (first_name, username, now, telegram_id),
            )
            await db.commit()
        existing["first_name"] = first_name
        existing["username"] = username
        existing["last_active"] = now
        return existing

    # Generar código de referido (simple hash)
    import hashlib

    my_ref_code = hashlib.md5(str(telegram_id).encode()).hexdigest()[:8].upper()
    referred_by = None

    if referral_code:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT telegram_id FROM users WHERE referral_code = ?",
                (referral_code,),
            )
            row = await cur.fetchone()
            await cur.close()
            if row:
                referred_by = row["telegram_id"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (
              telegram_id, first_name, username, email, email_verified,
              country_code, plan, referral_code, referred_by, tokens,
              total_earned, pending_payout, total_withdrawn,
              tasks_completed, referrals_count, subscription_until,
              created_at, last_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                first_name,
                username,
                None,
                0,
                "GLOBAL",
                "FREE",
                my_ref_code,
                referred_by,
                0,
                0.0,
                0.0,
                0.0,
                0,
                0,
                None,
                now,
                now,
            ),
        )
        await db.commit()

    user = await get_user(telegram_id)

    # Registrar referral si corresponde
    if referred_by:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO referrals (referrer_id, referred_id, commission_earned, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (referred_by, telegram_id, now),
            )
            await db.execute(
                "UPDATE users SET referrals_count = referrals_count + 1 WHERE telegram_id = ?",
                (referred_by,),
            )
            await db.commit()

    return user


# ---------------------------------------------------------------------
# HANDLERS DEL BOT – FUNCIONES PRINCIPALES
# ---------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start [referral_code] – registro del usuario + manejo de referidos
    """
    args = context.args
    referral_code = args[0] if args else None

    tg_user = update.effective_user
    user = await create_or_update_user(
        telegram_id=tg_user.id,
        first_name=tg_user.first_name or "",
        username=tg_user.username or "",
        referral_code=referral_code,
    )

    country_code = user.get("country_code", "GLOBAL")
    country_conf = COUNTRY_CONFIG.get(country_code, COUNTRY_CONFIG["GLOBAL"])
    plan = user.get("plan", "FREE")

    msg = (
        f"🧠 BIENVENIDO A {APP_NAME}\n\n"
        f"Hola {tg_user.first_name or 'amig@'}!\n\n"
        f"País: {country_conf['name']}\n"
        f"Plan actual: {plan}\n"
        f"Teórico máximo diario (según mercado): hasta {country_conf['daily_cap_usd']} USD.\n\n"
        "Aquí podrás:\n"
        "- Completar tareas y encuestas.\n"
        "- Invitar amigos y ganar comisiones.\n"
        "- Configurar tus métodos de cobro.\n"
        "- (Pronto) acceder a plan PREMIUM con trabajos mejor pagos.\n\n"
        "Usa los botones de abajo para navegar."
    )

    if update.message:
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True),
        )


async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await get_user(tg_user.id)
    if not user:
        await update.message.reply_text("No te encuentro. Usa /start primero.")
        return

    country_code = user.get("country_code", "GLOBAL")
    country_conf = COUNTRY_CONFIG.get(country_code, COUNTRY_CONFIG["GLOBAL"])
    plan = user.get("plan", "FREE")

    msg = (
        "📊 TU DASHBOARD – RESUMEN\n\n"
        f"Plan: {plan}\n"
        f"País: {country_conf['name']}\n"
        f"Tokens internos: {user['tokens']}\n"
        f"Total ganado: ${user['total_earned']:.2f}\n"
        f"Pendiente de retirar: ${user['pending_payout']:.2f}\n"
        f"Total retirado: ${user['total_withdrawn']:.2f}\n"
        f"Tareas completadas: {user['tasks_completed']}\n"
        f"Referidos activos: {user['referrals_count']}\n"
    )

    await update.message.reply_text(msg)


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await get_user(tg_user.id)
    if not user:
        await update.message.reply_text("No te encuentro. Usa /start primero.")
        return

    plan = user.get("plan", "FREE")

    text = (
        "💳 PLANES THEONEHIVE\n\n"
        "FREE (actual):\n"
        "- Acceso a tareas estándar.\n"
        "- % estándar y mínimos normales.\n\n"
        "PREMIUM ($15/mes):\n"
        "- Más tareas y mejor pagadas.\n"
        "- % mayor en cada tarea.\n"
        "- Retiros más rápidos y mínimos más bajos.\n"
        "- Bonos extra por referidos y campañas.\n\n"
        f"Tu plan actual: {plan}\n\n"
        "En esta versión se simula la activación de PREMIUM;\n"
        "en producción debe conectarse a pasarelas de pago (Stripe, PayPal, Cripto)."
    )

    keyboard = [
        [InlineKeyboardButton("Seguir con FREE", callback_data="plan_free")],
        [InlineKeyboardButton("Quiero PREMIUM ($15/mes)", callback_data="plan_premium")],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja los botones de selección de plan.
    Aquí simulamos PREMIUM por 30 días (sin cobro).
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    tg_user = query.from_user

    user = await get_user(tg_user.id)
    if not user:
        await query.edit_message_text("No te encuentro. Usa /start primero.")
        return

    if data == "plan_free":
        await query.edit_message_text("Sigues en plan FREE. Más adelante podrás cambiar a PREMIUM con pago real.")
        return

    if data == "plan_premium":
        new_until = (datetime.utcnow() + timedelta(days=30)).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET plan=?, subscription_until=? WHERE telegram_id=?",
                ("PREMIUM", new_until, tg_user.id),
            )
            await db.commit()

        await query.edit_message_text(
            "🎉 Se ha activado el plan PREMIUM de prueba por 30 días.\n"
            "En la versión completa se activará solo tras un pago exitoso."
        )


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra tareas de ejemplo. Preparado para enganchar redes CPA y algoritmo de optimización.
    """
    tg_user = update.effective_user
    user = await get_user(tg_user.id)
    if not user:
        await update.message.reply_text("No te encuentro. Usa /start primero.")
        return

    # EJEMPLO: en producción se obtienen tareas de APIs externas + score por usuario
    sample_tasks = [
        {"id": 1, "title": "Encuesta rápida (2 min)", "payout_user_usd": 0.50},
        {"id": 2, "title": "Instalar app y registrarse", "payout_user_usd": 1.20},
        {"id": 3, "title": "Registro KYC en plataforma financiera", "payout_user_usd": 4.00},
    ]

    lines = ["🎯 TAREAS DISPONIBLES (DE EJEMPLO)\n"]
    for t in sample_tasks:
        lines.append(f"{t['id']}. {t['title']} – Ganas ${t['payout_user_usd']:.2f}")
    lines.append(
        "\nEn la versión completa, estas tareas vendrán de redes CPA, "
        "optimizadas por país, plan y algoritmo de rendimiento."
    )

    await update.message.reply_text("\n".join(lines))


async def cmd_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await get_user(tg_user.id)
    if not user:
        await update.message.reply_text("No te encuentro. Usa /start primero.")
        return

    ref_code = user.get("referral_code")
    bot_username = context.bot.username if context.bot else "TheOneHiveBot"
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"

    msg = (
        "👥 PROGRAMA DE REFERIDOS THEONEHIVE\n\n"
        f"Tu código de referido: {ref_code}\n"
        f"Tu link de invitación:\n{ref_link}\n\n"
        "Ganas por cada amigo activo y un % de lo que ellos generen.\n"
        "Los montos exactos se configuran por país y plan en la versión completa."
    )

    await update.message.reply_text(msg)


async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await get_user(tg_user.id)
    if not user:
        await update.message.reply_text("No te encuentro. Usa /start primero.")
        return

    country_code = user.get("country_code", "GLOBAL")
    conf = COUNTRY_CONFIG.get(country_code, COUNTRY_CONFIG["GLOBAL"])

    msg = (
        "💸 RETIROS (ESQUELETO)\n\n"
        f"Saldo listo para retirar: ${user['pending_payout']:.2f}\n"
        f"Mínimo de retiro para tu país: ${conf['min_withdraw_usd']:.2f}\n"
        f"Métodos sugeridos: {', '.join(conf['payment_methods'])}\n\n"
        "En la versión completa se implementará:\n"
        "- Elección de método (PayPal, cripto, otros locales).\n"
        "- Ingreso de datos de pago (email/wallet/etc.).\n"
        "- Solicitud de retiro diaria con validación antifraude.\n"
        "- Proceso backend que paga automáticamente según ingresos reales.\n"
    )

    await update.message.reply_text(msg)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja texto libre y botones del teclado principal.
    """
    if not update.message:
        return

    text = (update.message.text or "").strip().lower()

    if "tarea" in text:
        await cmd_tasks(update, context)
    elif "dashboard" in text or "panel" in text:
        await cmd_dashboard(update, context)
    elif "refer" in text or "invitar" in text:
        await cmd_referrals(update, context)
    elif "plan" in text:
        await cmd_plan(update, context)
    elif "retir" in text:
        await cmd_withdraw(update, context)
    else:
        await update.message.reply_text(
            "No entendí tu mensaje.\n"
            "Usa los botones o comandos: /start, /dashboard, /tareas, /referidos, /plan, /retirar"
        )


# ---------------------------------------------------------------------
# INICIALIZACIÓN DEL BOT (Application, SIN Updater)
# ---------------------------------------------------------------------


async def init_telegram_app() -> Application:
    """
    Crea una única instancia de Application (bot) para todo el backend.
    """
    global telegram_app
    if telegram_app:
        return telegram_app

    logger.info("Iniciando aplicación de Telegram de TheOneHive...")
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", cmd_start))
    telegram_app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    telegram_app.add_handler(CommandHandler("plan", cmd_plan))
    telegram_app.add_handler(CommandHandler("tareas", cmd_tasks))
    telegram_app.add_handler(CommandHandler("referidos", cmd_referrals))
    telegram_app.add_handler(CommandHandler("retirar", cmd_withdraw))
    telegram_app.add_handler(CallbackQueryHandler(cb_plan, pattern="^plan_"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await telegram_app.initialize()
    logger.info("Aplicación de Telegram inicializada.")
    return telegram_app


# ---------------------------------------------------------------------
# FASTAPI – EVENTOS Y RUTAS
# ---------------------------------------------------------------------


@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Iniciando backend de TheOneHive en Render...")
    await init_db()
    app_telegram = await init_telegram_app()

    # Configurar webhook si tenemos URL externa (Render nos la da)
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/telegram/webhook/{TELEGRAM_TOKEN}"
        await app_telegram.bot.delete_webhook(drop_pending_updates=True)
        await app_telegram.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook configurado: {webhook_url}")
    else:
        logger.warning(
            "RENDER_EXTERNAL_URL no configurado. No se configuró webhook de Telegram."
        )

    logger.info("✅ Backend de TheOneHive listo.")


@app.on_event("shutdown")
async def on_shutdown():
    global telegram_app
    logger.info("🛑 Apagando backend de TheOneHive...")
    if telegram_app:
        await telegram_app.shutdown()
        await telegram_app.stop()
        telegram_app = None
    logger.info("🛑 Backend apagado.")


@app.get("/health")
async def health():
    return {"status": "ok", "project": APP_NAME}


@app.get("/")
async def root():
    return {
        "name": APP_NAME,
        "status": "online",
        "message": "Backend mínimo de TheOneHive en FastAPI + Telegram.",
    }


@app.post("/telegram/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Endpoint que recibe los updates de Telegram.
    Render envía el tráfico de Telegram aquí a través del webhook configurado.
    """
    if token != TELEGRAM_TOKEN:
        return JSONResponse(status_code=403, content={"detail": "Invalid token"})

    data = await request.json()
    app_telegram = await init_telegram_app()
    update = Update.de_json(data, app_telegram.bot)
    await app_telegram.process_update(update)
    return {"ok": True}
