import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db  # IMPORTANTE: Asegúrate de tener database.py en la misma carpeta

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# URL DE TU LANDING PAGE
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com" 

# --- HANDLER: START (Con Sistema de Referidos) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra usuario, maneja referidos y envía bienvenida."""
    user = update.effective_user
    telegram_id = user.id
    first_name = user.first_name
    
    logger.info(f"Usuario {telegram_id} inició el bot.")

    # 1. Detectar Referido (ej: /start 12345)
    referrer_id = None
    args = context.args
    if args and args[0].isdigit():
        possible_id = int(args[0])
        # Evitar que alguien se invite a sí mismo
        if possible_id != telegram_id:
            referrer_id = possible_id

    # 2. Intentar registrar en Base de Datos
    # Nota: Si el usuario ya existe, la DB lo ignora y no sobreescribe
    is_new_user = await db.create_user(telegram_id, first_name, referrer_id)

    # 3. Lógica de Recompensa (Solo si es nuevo y fue invitado)
    if is_new_user and referrer_id:
        try:
            # Dar 50 puntos al padrino
            await db.reward_referrer(referrer_id, points=50)
            
            # Notificar al Padrino (Growth Hack: Feedback inmediato)
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"🚀 <b>¡NUEVO RECLUTA!</b>\n\n{first_name} se unió con tu enlace.\nGanaste +50 Puntos HIVE.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"No se pudo notificar al referrer {referrer_id}: {e}")

    # 4. Mensaje de Bienvenida (Frontend)
    welcome_text = (
        f"🐝 *BIENVENIDO A THE HIVE, {first_name}*\n\n"
        "Sistema de Minería Social Activo.\n"
        "Gana dinero invitando amigos y completando tareas.\n\n"
        "👇 *PASO 1: Verifica que eres humano para activar tu cuenta.*"
    )

    keyboard = [
        [InlineKeyboardButton("🔒 VERIFICAR AHORA", url=LANDING_PAGE_URL)],
        [InlineKeyboardButton("👥 OBTENER MI LINK DE INVITADO", callback_data="get_ref_link")] # Opcional, o usar comando
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# --- HANDLER: INVITAR (Viralidad) ---
async def invitar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera y muestra el link de referido del usuario."""
    user_id = update.effective_user.id
    bot_username = context.bot.username
    
    # Construir Link
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    text = (
        "📢 *SISTEMA DE REFERIDOS*\n\n"
        "¡Invita a tus amigos y gana dinero pasivo!\n"
        "💰 *Recompensa:* 50 Puntos por amigo.\n\n"
        "👇 *Tu Enlace Único:*\n"
        f"`{ref_link}`\n\n"
        "(Toca para copiar)"
    )
    
    # Botón nativo de compartir
    share_url = f"https://t.me/share/url?url={ref_link}&text=Entra+a+TheHive+y+gana+dinero+real!+🐝"
    keyboard = [[InlineKeyboardButton("📤 ENVIAR A AMIGOS", url=share_url)]]
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- HANDLER: PERFIL (Estadísticas) ---
async def perfil_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra saldo y referidos."""
    user_id = update.effective_user.id
    
    # Consultar DB
    stats = await db.get_user_stats(user_id)
    
    text = (
        f"👤 *PERFIL DEL MINERO*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💰 Saldo: *{stats['balance']} HIVE*\n"
        f"👥 Referidos: *{stats['referrals_count']}*"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

# --- HANDLER: RESET (Solo para Pruebas) ---
async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra al usuario de la DB para probar flujo desde cero."""
    user_id = update.effective_user.id
    await db.delete_user(user_id)
    await update.message.reply_text("🗑 *RESET COMPLETO.* Envía /start para probar de nuevo.", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n/start - Iniciar\n/invitar - Ganar Puntos\n/perfil - Ver Saldo"
    )

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el código HIVE-777."""
    text = update.message.text.strip().upper()
    
    if text == "HIVE-777":
        # AQUÍ PODRÍAS DAR PUNTOS TAMBIÉN EN EL FUTURO
        await update.message.reply_text(
            "✅ *ACCESO CONCEDIDO*\n\n"
            "Has sido verificado exitosamente.\n"
            "Usa /invitar para comenzar a ganar puntos ya mismo.",
            parse_mode="Markdown"
        )
