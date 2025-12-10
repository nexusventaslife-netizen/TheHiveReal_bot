import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# URL DE TU WEB (SMARTLINK)
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paso 1: Bienvenida."""
    user = update.effective_user
    await db.add_user(user.id, user.first_name, user.username)

    welcome_text = (
        f"👋 *Hola, {user.first_name}*\n\n"
        "🔒 *VERIFICACIÓN DE SEGURIDAD*\n"
        "Para activar tu cuenta, necesitamos verificar que eres humano.\n\n"
        "1️⃣ Entra al enlace y obtén tu código.\n"
        "2️⃣ Vuelve aquí y pégalo.\n"
    )

    keyboard = [[InlineKeyboardButton("🚀 OBTENER CÓDIGO", url=LANDING_PAGE_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja Emails y Códigos."""
    text = update.message.text.strip()
    user = update.effective_user
    
    # 1. CASO: USUARIO ENVÍA UN EMAIL (Validación simple)
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            
            terms_text = (
                "📜 *TÉRMINOS DE SERVICIO*\n\n"
                f"Email: `{text}`\n\n"
                "Para continuar gratis, aceptas recibir ofertas y publicidad de nuestros socios.\n"
                "¿Aceptas?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ ACEPTO", callback_data="accept_terms")],
                [InlineKeyboardButton("❌ NO", callback_data="deny_terms")]
            ]
            await update.message.reply_text(terms_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text("❌ Email inválido. Intenta de nuevo.")
            return

    # 2. CASO: USUARIO ENVÍA EL CÓDIGO
    if text.upper() == "HIVE-777":
        context.user_data['waiting_for_email'] = True
        await update.message.reply_text(
            "✅ *CÓDIGO CORRECTO*\n\n"
            "📧 Escribe tu **Correo Electrónico** para finalizar el registro:",
            parse_mode="Markdown"
        )
        return

    # 3. OTROS TEXTOS
    await update.message.reply_text("❌ Comando no reconocido. Usa /start si te perdiste.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el botón de Aceptar Términos."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "accept_terms":
        email = context.user_data.get('email', 'no-email')
        user = query.from_user
        
        await db.update_email(user.id, email)
        logger.info(f"💰 LEAD CAPTURADO: {user.id} - {email}")
        
        await query.edit_message_text(
            text="✅ *REGISTRO COMPLETADO*\n\n🎉 Tu cuenta ha sido activada.\n⛏️ Minería Iniciada...",
            parse_mode="Markdown"
        )
        
    elif query.data == "deny_terms":
        await query.edit_message_text("❌ Debes aceptar para continuar.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ayuda: Usa /start para reiniciar.")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    link = f"https://t.me/{context.bot.username}?start={user.id}"
    await update.message.reply_text(f"🔗 Enlace: `{link}`", parse_mode="Markdown")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.delete_user(user.id)
    context.user_data.clear()
    await update.message.reply_text("🗑️ Usuario reiniciado.")
