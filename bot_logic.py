import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
# ¡PON AQUÍ TU ENLACE DE RENDER (EL DEL SITIO WEB NEGRO Y AMARILLO)!
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida con botón directo."""
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.first_name}) inició el bot.")

    welcome_text = (
        f"👋 *Hola, {user.first_name}*\n\n"
        "🔒 *SISTEMA DE VERIFICACIÓN HIVE*\n"
        "Para acceder a las señales y minería, debes verificar que eres humano.\n\n"
        "👇 Haz clic en el botón para ver las tareas disponibles:"
    )

    # Botón con URL directa (Evita que se quede cargando)
    keyboard = [
        [InlineKeyboardButton("🚀 VERIFICAR AHORA", url=LANDING_PAGE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa /start para iniciar.")

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida el código HIVE-777."""
    text = update.message.text.strip().upper()
    
    if text == "HIVE-777":
        await update.message.reply_text(
            "✅ *ACCESO CONCEDIDO*\n\n"
            "Has sido verificado.\n"
            "Tus puntos han comenzado a generarse. ⛏️💰"
        )
    else:
        # Ignoramos otros textos por ahora
        pass
