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
    context.user_data.clear() # Limpiamos datos viejos
    
    # Intentamos guardar usuario en DB
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

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ESTA ES LA FUNCIÓN QUE MAIN BUSCA.
    Maneja Código HIVE-777 y también el EMAIL.
    """
    text = update.message.text.strip()
    user = update.effective_user
    
    # --- PASO 3: VALIDAR EMAIL (Si estamos esperando uno) ---
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            # Guardamos el mail temporalmente
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            
            # --- PASO 4: PEDIR CONSENTIMIENTO ---
            terms_text = (
                "📜 *TÉRMINOS Y CONDICIONES*\n\n"
                f"Correo registrado: `{text}`\n\n"
                "Para financiar este servicio, necesitamos tu permiso para enviarte ofertas.\n"
                "¿Aceptas continuar?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ ACEPTO", callback_data="accept_terms")],
                [InlineKeyboardButton("❌ NO", callback_data="deny_terms")]
            ]
            await update.message.reply_text(terms_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            
        else:
            await update.message.reply_text("❌ Formato de correo inválido. Intenta de nuevo.")
        return

    # --- PASO 2: VALIDAR CÓDIGO HIVE-777 ---
    if text.upper() == "HIVE-777":
        context.user_data['waiting_for_email'] = True
        await update.message.reply_text(
            "✅ *CÓDIGO CORRECTO*\n\n"
            "📧 Escribe tu **Correo Electrónico** para vincular la cuenta:",
            parse_mode="Markdown"
        )
    else:
        # Si escribe otra cosa que no es el código
        await update.message.reply_text("❌ Código incorrecto o comando no reconocido.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el clic en 'ACEPTO'."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "accept_terms":
        email = context.user_data.get('email', 'no-email')
        user = query.from_user
        
        # Guardamos el mail en la base de datos REALMENTE
        await db.update_email(user.id, email)
        
        logger.info(f"💰 NUEVO LEAD: {user.id} - {email}")
        
        await query.edit_message_text(
            text=(
                "✅ *REGISTRO COMPLETADO*\n\n"
                "🎉 Has sido verificado correctamente.\n"
                "⛏️ *MINERÍA INICIADA...*"
            ),
            parse_mode="Markdown"
        )
        
    elif query.data == "deny_terms":
        await query.edit_message_text("❌ Debes aceptar los términos para usar el bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa /start para iniciar.")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    link = f"https://t.me/{context.bot.username}?start={user.id}"
    await update.message.reply_text(f"🔗 Tu enlace: `{link}`", parse_mode="Markdown")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.delete_user(user.id)
    context.user_data.clear()
    await update.message.reply_text("🗑️ Reset completo.")
