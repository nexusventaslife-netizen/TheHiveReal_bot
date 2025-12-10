import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# TU ENLACE DE MONETIZACIÓN
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user(user.id, user.first_name, user.username)
    
    welcome_text = (
        f"👋 *Hola, {user.first_name}*\n\n"
        "🔒 *VERIFICACIÓN REQUERIDA*\n"
        "Sistema de seguridad activo. Para minar, verifica tu cuenta:\n\n"
        "1️⃣ Entra al enlace y obtén el código.\n"
        "2️⃣ Vuelve aquí y pégalo."
    )
    keyboard = [[InlineKeyboardButton("🚀 OBTENER CÓDIGO", url=LANDING_PAGE_URL)]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja Emails y Códigos HIVE-777"""
    text = update.message.text.strip()
    user = update.effective_user
    
    # 1. CASO EMAIL
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            
            # Pedimos Aceptación de Publicidad
            terms = f"📧 Correo: `{text}`\n\n¿Aceptas recibir novedades y promociones para financiar el bot?"
            kb = [
                [InlineKeyboardButton("✅ ACEPTO", callback_data="accept_terms")],
                [InlineKeyboardButton("❌ NO", callback_data="deny_terms")]
            ]
            await update.message.reply_text(terms, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Email inválido. Intenta de nuevo.")
        return

    # 2. CASO CÓDIGO
    if text.upper() == "HIVE-777":
        context.user_data['waiting_for_email'] = True
        await update.message.reply_text("✅ *CÓDIGO CORRECTO*\n\n📧 Ahora escribe tu **Correo Electrónico**:", parse_mode="Markdown")
        return

    await update.message.reply_text("❌ Comando no reconocido. Usa /start si te perdiste.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "accept_terms":
        email = context.user_data.get('email', 'Desconocido')
        await db.update_email(query.from_user.id, email)
        await query.edit_message_text("✅ *VERIFICADO*\n\nMinería Iniciada... ⛏️", parse_mode="Markdown")
    elif query.data == "deny_terms":
        await query.edit_message_text("❌ Debes aceptar para continuar.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa /start para reiniciar.")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"🔗 Tu link: `https://t.me/{context.bot.username}?start={user.id}`", parse_mode="Markdown")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.delete_user(user.id)
    context.user_data.clear()
    await update.message.reply_text("🗑️ Cuenta reseteada.")
