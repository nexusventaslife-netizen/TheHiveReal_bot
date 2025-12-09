import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Si tienes el archivo database.py configurado, puedes descomentar la siguiente línea:
# import database as db

logger = logging.getLogger(__name__)

# ✅ ESTA ES LA URL DE TU SITIO ESTÁTICO (Donde están los 3 botones)
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mensaje de bienvenida.
    El botón 'url=' debe llevar al SITIO ESTÁTICO, no al bot.
    """
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.first_name}) inició el bot.")

    welcome_text = (
        f"👋 *Hola, {user.first_name}*\n\n"
        "🔒 *SISTEMA DE VERIFICACIÓN HIVE*\n"
        "Para acceder a las señales y minería, debes completar la verificación.\n\n"
        "👇 *Haz clic aquí para abrir las tareas:*"
    )

    # 🚀 AQUÍ ESTÁ LA MAGIA:
    # Usamos 'url=LANDING_PAGE_URL' para que Telegram abra tu HTML estático directamente.
    keyboard = [
        [InlineKeyboardButton("🚀 VERIFICAR AHORA", url=LANDING_PAGE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa /start para iniciar.")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera enlace de referido (Simple)."""
    user = update.effective_user
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start={user.id}"
    
    await update.message.reply_text(
        f"🔗 *TU ENLACE DE REFERIDO:*\n`{ref_link}`\n\nComparte este enlace para ganar puntos.",
        parse_mode="Markdown"
    )

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida el código HIVE-777 que el usuario trae de la web."""
    text = update.message.text.strip().upper()
    
    if text == "HIVE-777":
        await update.message.reply_text(
            "✅ *ACCESO CONCEDIDO*\n\n"
            "Has sido verificado.\n"
            "Tus puntos han comenzado a generarse. ⛏️💰"
        )
    else:
        pass
