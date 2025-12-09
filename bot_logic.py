import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db  # Importamos nuestro módulo de DB actualizado

logger = logging.getLogger(__name__)

# URL DE TU LANDING PAGE
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entrada principal. Maneja registros normales y por referidos.
    """
    user = update.effective_user
    args = context.args  # Aquí vienen los argumentos (ej: /start 12345)
    
    referrer_id = None
    if args and args[0].isdigit():
        referrer_id = int(args[0])
        # Evitar auto-referidos
        if referrer_id == user.id:
            referrer_id = None

    # 1. Registrar usuario en DB (La DB decide si da puntos al referrer)
    is_new = await db.add_user(user.id, user.first_name, user.username, referrer_id)
    
    # 2. Si hubo referido exitoso, intentamos notificar al padrino (Opcional, pero bueno para engagement)
    if is_new and referrer_id:
        try:
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"🎉 *¡NUEVO MINERO RECLUTADO!*\n\n{user.first_name} se ha unido a tu colmena.\nHas ganado +50 Puntos HIVE. 🐝💰",
                parse_mode="Markdown"
            )
        except Exception:
            pass # Si el bot está bloqueado por el padrino, ignoramos.

    logger.info(f"Usuario {user.id} ({user.first_name}) inició el bot. Referrer: {referrer_id}")

    # Texto de Bienvenida
    welcome_text = (
        f"👋 *Bienvenido a la Colmena, {user.first_name}*\n\n"
        "🔒 *SISTEMA DE VERIFICACIÓN HIVE*\n"
        "Estás a un paso de acceder a las señales y la minería.\n\n"
        "👇 *Haz clic para Verificar tu Humanidad:*"
    )

    keyboard = [
        [InlineKeyboardButton("🚀 VERIFICAR Y MINAR", url=LANDING_PAGE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Genera el enlace de referido para el usuario.
    """
    user = update.effective_user
    bot_username = context.bot.username
    
    # Enlace formato: t.me/NombreBot?start=ID_USUARIO
    ref_link = f"https://t.me/{bot_username}?start={user.id}"
    
    text = (
        "📢 *SISTEMA DE REFERIDOS ACTIVADO*\n\n"
        "¡Gana puntos invitando amigos a la colmena!\n"
        "💰 *Recompensa:* 50 Puntos HIVE por cada amigo.\n\n"
        "👇 *Tu Enlace Único:*\n"
        f"`{ref_link}`\n\n"
        "_(Toca el enlace para copiarlo)_"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *COMANDOS DISPONIBLES*\n\n"
        "/start - Reiniciar y Verificar\n"
        "/invitar - Conseguir enlace de referido (+50 Puntos)\n"
        "/help - Ayuda",
        parse_mode="Markdown"
    )

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida el código HIVE-777."""
    text = update.message.text.strip().upper()
    user = update.effective_user
    
    if text == "HIVE-777":
        # Dar puntos por verificar (opcional, ejemplo 100 puntos)
        await db.add_hive_points(user.id, 100)
        await db.update_user_gate_status(user.id, True)
        
        await update.message.reply_text(
            "✅ *VERIFICACIÓN EXITOSA*\n\n"
            "Has recibido +100 Puntos de Bienvenida.\n"
            "Tus motores de minería están activos. ⛏️\n\n"
            "Usa /invitar para ganar más velocidad.",
            parse_mode="Markdown"
        )
    else:
        pass
