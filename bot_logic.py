import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import database as db

logger = logging.getLogger(__name__)

# URL DE TU LANDING PAGE
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com"

# Estados para ConversationHandler (Si usáramos conversación, por ahora es flujo simple)
EMAIL_INPUT = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el inicio, registro y referidos."""
    user = update.effective_user
    args = context.args
    
    # 1. Detectar Referido
    referrer_id = None
    if args and args[0].isdigit():
        possible_ref = int(args[0])
        if possible_ref != user.id: # No auto-referirse
            referrer_id = possible_ref

    # 2. Registrar Usuario en DB
    # Intentamos crearlo. db.add_user devuelve True si es NUEVO.
    is_new = await db.add_user(user.id, user.first_name, user.username, referrer_id)
    
    # 3. Lógica de Recompensa
    if is_new and referrer_id:
        await db.reward_referrer(referrer_id, points=50)
        # Notificar al invitador
        try:
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"🚀 <b>¡NUEVO MINERO RECLUTADO!</b>\nHas ganado +50 Miel por invitar a {user.first_name}.",
                parse_mode="HTML"
            )
        except:
            pass # El usuario bloqueó el bot

    # 4. Verificar si tiene Email (Para mostrar Gate o pedir Email)
    db_user = await db.get_user(user.id)
    
    if not db_user or not db_user.get('email'):
        await update.message.reply_text(
            f"👋 ¡Hola {user.first_name}!\n\n"
            "Antes de empezar a minar, necesitamos verificar tu cuenta.\n"
            "📧 <b>Por favor, responde a este mensaje con tu EMAIL:</b>",
            parse_mode="HTML"
        )
        return EMAIL_INPUT # Retornar estado si usas ConversationHandler (ver abajo)
    
    # Si ya tiene email, mostrar el botón de verificación
    await show_verification_gate(update)

async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el email del usuario."""
    email = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validación simple de regex
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await update.message.reply_text("❌ Email inválido. Inténtalo de nuevo:")
        return EMAIL_INPUT

    # Guardar en DB
    await db.update_user_email(user_id, email)
    await db.add_lead(user_id, email) # Backup en leads_harvest
    
    await update.message.reply_text("✅ Email guardado correctamente.")
    await show_verification_gate(update)
    return ConversationHandler.END

async def show_verification_gate(update: Update):
    """Muestra el botón para ir a la Web."""
    keyboard = [[InlineKeyboardButton("🔒 VERIFICAR AHORA", url=LANDING_PAGE_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🐝 <b>SISTEMA THE HIVE</b>\n\n"
        "Todo listo. Verifica tu identidad en nuestra web para activar la minería.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def invitar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera el link de referido."""
    user_id = update.effective_user.id
    bot_name = context.bot.username
    
    ref_link = f"https://t.me/{bot_name}?start={user_id}"
    
    # Obtener stats
    count = await db.get_user_referrals_count(user_id)
    
    text = (
        f"📢 <b>SISTEMA DE REFERIDOS</b>\n\n"
        f"👥 Has invitado a: <b>{count} personas</b>\n"
        f"💰 Ganas <b>50 Miel</b> por cada amigo.\n\n"
        f"👇 <b>Tu enlace único:</b>\n<code>{ref_link}</code>"
    )
    
    # Botón de compartir nativo
    share_url = f"https://t.me/share/url?url={ref_link}&text=Únete+a+TheHive+y+gana+dinero+real!+🐝"
    kb = [[InlineKeyboardButton("📤 Compartir con amigos", url=share_url)]]
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el código HIVE-777."""
    text = update.message.text.strip().upper()
    if text == "HIVE-777":
        user_id = update.effective_user.id
        user_data = await db.get_user(user_id)
        balance = user_data.get('balance_hive', 0)
        
        await update.message.reply_text(
            f"✅ <b>ACCESO CONCEDIDO</b>\n\n"
            f"Tus motores están minando... 🔥\n"
            f"💰 Saldo actual: <b>{balance} Miel</b>\n\n"
            "Usa /invitar para ganar más.",
            parse_mode="HTML"
        )

# --- COMANDO MÁGICO PARA TESTING ---
async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra al usuario de la DB para probar de cero."""
    await db.delete_user(update.effective_user.id)
    await update.message.reply_text("🗑 Usuario borrado. Envía /start para probar registro.")
