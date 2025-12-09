import logging
import re  # Para validar emails
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# URL DE TU WEB (Donde están ByBit y Monetag)
# Asegúrate de que esta sea la url de tu index.html correcto
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Paso 1: Bienvenida.
    Si NO tiene email, se lo pide.
    Si YA tiene email, le muestra el botón de verificar.
    """
    user = update.effective_user
    
    # Registramos al usuario en la DB (si es nuevo)
    await db.add_user(user.id, user.first_name, user.username)
    
    # Consultamos sus datos para ver si ya dio el mail
    user_data = await db.get_user(user.id)
    email_guardado = user_data['email'] if user_data else None

    if not email_guardado:
        # --- CASO 1: NO TENEMOS SU MAIL ---
        # Le pedimos el correo antes de dejarle pasar.
        msg = (
            f"👋 *Hola, {user.first_name}*\n\n"
            "🔒 *SISTEMA DE SEGURIDAD*\n"
            "Para activar tu billetera y acceder a las señales, necesitamos registrar tu usuario.\n\n"
            "📧 *Por favor, ENVÍA TU CORREO ELECTRÓNICO ahora mismo.*\n\n"
            "_(Al enviar tu correo, aceptas recibir novedades y ofertas exclusivas de nuestros patrocinadores)_"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    else:
        # --- CASO 2: YA TENEMOS SU MAIL ---
        # Le mostramos directamente el botón de verificación web.
        await show_verification_button(update)


async def show_verification_button(update: Update):
    """Función auxiliar para mostrar el botón de la Web."""
    msg = (
        "✅ *Correo Registrado.*\n\n"
        "🚀 *ÚLTIMO PASO: ACTIVACIÓN*\n"
        "Debes verificar que eres humano completando una tarea rápida.\n\n"
        "👇 Haz clic abajo, completa la tarea y vuelve con el código."
    )
    
    keyboard = [[InlineKeyboardButton("🔐 VERIFICAR CUENTA AHORA", url=LANDING_PAGE_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")


async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manejador Inteligente:
    - Detecta si es un EMAIL.
    - Detecta si es el CÓDIGO (HIVE-777).
    """
    text = update.message.text.strip()
    user = update.effective_user
    
    # 1. ¿ES UN EMAIL? (Usamos una expresión regular simple)
    if re.match(r"[^@]+@[^@]+\.[^@]+", text):
        # Guardamos el email en la DB
        success = await db.update_email(user.id, text)
        
        if success:
            await update.message.reply_text("💾 *Email Guardado exitosamente.*", parse_mode="Markdown")
            # Ahora le mostramos el botón para ir a la web
            await show_verification_button(update)
        else:
            await update.message.reply_text("❌ Hubo un error guardando tu email. Intenta de nuevo.")
        return

    # 2. ¿ES EL CÓDIGO DE VERIFICACIÓN?
    if text.upper() == "HIVE-777":
        # Aquí daríamos el acceso final
        await update.message.reply_text(
            "🎉 *¡FELICIDADES! ACCESO CONCEDIDO* 🎉\n\n"
            "Tu cuenta ha sido verificada y la minería ha comenzado. ⛏️\n"
            "💰 *Saldo Inicial:* $50.00 USD (Bono)\n\n"
            "Usa el menú para ver tus señales.",
            parse_mode="Markdown"
        )
        return

    # 3. SI NO ES NI MAIL NI CÓDIGO
    await update.message.reply_text(
        "❌ No entiendo ese mensaje.\n\n"
        "👉 Si estás registrándote, envíame tu **CORREO**.\n"
        "👉 Si ya te registraste en la web, envíame el **CÓDIGO**."
    )

# Comandos extra
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ayuda: Envía tu correo para registrarte.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.delete_user(user.id)
    await update.message.reply_text("🗑️ Usuario borrado. Usa /start para probar de nuevo.")
