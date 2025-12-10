import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# URL DE TU WEB (SMARTLINK)
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paso 1: Bienvenida y enlace a la web."""
    user = update.effective_user
    
    # Intentamos guardar usuario en DB (si no existe)
    await db.add_user(user.id, user.first_name, user.username)

    # Verificamos si ya tiene email (si quieres ser estricto)
    # Por ahora mostramos el flujo estándar
    
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
    """
    MANEJADOR PRINCIPAL DE TEXTO
    Detecta si el usuario envía:
    1. Un Email (juan@gmail.com)
    2. El Código (HIVE-777)
    """
    text = update.message.text.strip()
    user = update.effective_user
    
    # --- CASO A: EL USUARIO ENVÍA UN EMAIL ---
    # (Solo si estamos esperando un email)
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            # Guardamos el mail temporalmente en memoria
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            
            # --- PEDIR CONSENTIMIENTO (GDPR / Venta de Datos) ---
            terms_text = (
                "📜 *TÉRMINOS Y CONDICIONES*\n\n"
                f"Correo registrado: `{text}`\n\n"
                "Para financiar este servicio gratuito, necesitamos tu permiso para:\n"
                "✅ Enviarte ofertas comerciales.\n"
                "✅ Compartir datos con partners publicitarios.\n\n"
                "¿Aceptas continuar?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ ACEPTO", callback_data="accept_terms")],
                [InlineKeyboardButton("❌ NO ACEPTO", callback_data="deny_terms")]
            ]
            await update.message.reply_text(terms_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text("❌ Formato de correo inválido. Intenta de nuevo.")
            return

    # --- CASO B: EL USUARIO ENVÍA EL CÓDIGO HIVE-777 ---
    if text.upper() == "HIVE-777":
        context.user_data['waiting_for_email'] = True
        await update.message.reply_text(
            "✅ *CÓDIGO CORRECTO*\n\n"
            "📧 Para vincular tu cuenta, escribe tu **Correo Electrónico** a continuación:",
            parse_mode="Markdown"
        )
        return

    # --- CASO C: CUALQUIER OTRA COSA ---
    await update.message.reply_text("❌ Mensaje no reconocido. Por favor, completa los pasos.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el clic en 'ACEPTO'."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "accept_terms":
        # RECUPERAMOS EL MAIL Y LO GUARDAMOS EN LA BASE DE DATOS REAL
        email = context.user_data.get('email', 'no-email')
        user = query.from_user
        
        # Guardar en DB
        await db.update_email(user.id, email)
        logger.info(f"💰 NUEVO LEAD CONFIRMADO: {user.id} - {email}")
        
        # Mensaje Final
        await query.edit_message_text(
            text=(
                "✅ *REGISTRO COMPLETADO*\n\n"
                "🎉 Has sido verificado correctamente.\n"
                "Tus datos han sido procesados.\n\n"
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
