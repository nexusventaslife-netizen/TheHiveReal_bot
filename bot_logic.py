import logging
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# URL DE TU WEB (SMARTLINK)
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paso 1: Bienvenida."""
    user = update.effective_user
    if hasattr(db, 'add_user'):
        await db.add_user(user.id, user.first_name, user.username)

    welcome_text = (
        f"👋 *Hola, {user.first_name}*\n\n"
        "🔒 *SISTEMA DE SEGURIDAD*\n"
        "Para activar la minería, necesitamos verificar que eres humano.\n\n"
        "1️⃣ Toca el botón y obtén tu código.\n"
        "2️⃣ Vuelve aquí y pégalo."
    )

    # Solo dejamos el botón de obtener código (quitamos los otros como pediste)
    keyboard = [[InlineKeyboardButton("🚀 OBTENER CÓDIGO", url=LANDING_PAGE_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja Emails y Códigos."""
    text = update.message.text.strip()
    user = update.effective_user
    
    # 1. CASO: USUARIO ENVÍA UN EMAIL
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            
            # Mensaje de espera para el email también
            msg_wait = await update.message.reply_text("⏳ *Procesando datos...*", parse_mode="Markdown")
            await asyncio.sleep(1.5) # Pequeña pausa dramática
            await context.bot.delete_message(chat_id=user.id, message_id=msg_wait.message_id)

            terms_text = (
                "📜 *ÚLTIMO PASO*\n\n"
                f"Email: `{text}`\n\n"
                "Para financiar el proyecto y minar gratis, aceptas recibir promociones de nuestros socios.\n"
                "¿Aceptas?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ ACEPTO Y MINAR", callback_data="accept_terms")],
                [InlineKeyboardButton("❌ NO", callback_data="deny_terms")]
            ]
            await update.message.reply_text(terms_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text("❌ Formato de email incorrecto.")
            return

    # 2. CASO: USUARIO ENVÍA EL CÓDIGO
    if text.upper() == "HIVE-777":
        # --- AQUÍ ESTÁ EL CAMBIO ---
        # 1. Enviamos mensaje de espera
        wait_msg = await update.message.reply_text("⏳ *Verificando código en la Blockchain...* Espere un momento.", parse_mode="Markdown")
        
        # 2. Simulamos tiempo de proceso (opcional, pero da realismo)
        await asyncio.sleep(2) 
        
        # 3. Borramos el mensaje de espera (para que quede limpio)
        try:
            await context.bot.delete_message(chat_id=user.id, message_id=wait_msg.message_id)
        except:
            pass # Si falla borrar, no importa
            
        context.user_data['waiting_for_email'] = True
        
        # 4. Enviamos la confirmación
        await update.message.reply_text(
            "✅ *CÓDIGO CONFIRMADO*\n\n"
            "🔓 Acceso concedido.\n"
            "📧 Ahora escribe tu **Correo Electrónico** para vincular tu cuenta:",
            parse_mode="Markdown"
        )
        return

    # 3. OTROS
    await update.message.reply_text("❌ Comando no reconocido. Usa /start.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "accept_terms":
        email = context.user_data.get('email', 'no-email')
        user = query.from_user
        
        # Guardamos en DB
        if hasattr(db, 'update_email'):
            await db.update_email(user.id, email)
        
        # Mensaje final de éxito
        await query.edit_message_text(
            text=(
                "🎉 *¡BIENVENIDO A LA COLMENA!*\n\n"
                "✅ Verificación Total: Completada\n"
                "⛏️ **Minería en la Nube: ACTIVA**\n\n"
                "Tu saldo empezará a subir en breve..."
            ),
            parse_mode="Markdown"
        )
        
    elif query.data == "deny_terms":
        await query.edit_message_text("❌ Debes aceptar para poder minar gratis.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa /start para reiniciar.")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    link = f"https://t.me/{context.bot.username}?start={user.id}"
    await update.message.reply_text(f"🔗 Tu enlace de referido:\n`{link}`", parse_mode="Markdown")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if hasattr(db, 'delete_user'):
        await db.delete_user(user.id)
    context.user_data.clear()
    await update.message.reply_text("🗑️ Cuenta reiniciada.")
