import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# URL DE TU LANDING PAGE (La que tiene los 3 botones)
# IMPORTANTE: Asegúrate de que esta URL es la correcta de tu Render
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el mensaje de bienvenida con el botón de verificación."""
    user = update.effective_user
    logger.info(f"Usuario {user.id} inició el bot.")
    
    # Texto de bienvenida estilo Hacker/Crypto
    welcome_text = (
        f"🐝 *BIENVENIDO A THE HIVE, {user.first_name}*\n\n"
        "Sistema de Minería Social Activo.\n"
        "Para comenzar a minar y ganar puntos, debes verificar que eres humano.\n\n"
        "👇 *Haz clic abajo para verificar y ver las tareas:*"
    )

    # Botón que abre tu página web (URL)
    # Usamos url=... directamente para que Telegram lo abra sin esperar callback
    keyboard = [
        [InlineKeyboardButton("🔒 VERIFICAR AHORA", url=LANDING_PAGE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía un mensaje de ayuda."""
    await update.message.reply_text("Escribe /start para reiniciar el sistema.")

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el código HIVE-777 que envía el usuario."""
    text = update.message.text.strip().upper()
    
    if text == "HIVE-777":
        await update.message.reply_text(
            "✅ *ACCESO CONCEDIDO*\n\n"
            "Has sido verificado exitosamente.\n"
            "Tus motores de minería están calentando... 🔥\n\n"
            "🔜 _Próximamente: Sistema de Referidos y Puntos._",
            parse_mode="Markdown"
        )
    else:
        # Si escriben cualquier otra cosa
        pass
