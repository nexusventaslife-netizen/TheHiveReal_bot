import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# IMPORTANTE: Importamos el módulo completo, no la variable suelta.
# Esto soluciona el error "Base de datos no conectada".
import database 
from database import (
    register_user_smart, 
    get_user_fast, 
    save_user_email, 
    unlock_api_gate, 
    update_gamification
)

logger = logging.getLogger("Hive.Logic")

# Estados para la conversación
WAIT_EMAIL = 1
WAIT_API_CHECK = 2

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Punto de entrada. Aplica SEGURIDAD y FILTROS ANTI-BOT.
    Nadie entra al menú sin Email y API Check.
    """
    user = update.effective_user
    logger.info(f"User {user.id} started bot")
    
    # 1. Registro inicial silencioso
    await register_user_smart(user)
    
    # 2. Obtener estado actual del usuario
    db_user = await get_user_fast(user.id)
    
    # --- FILTRO 1: EMAIL OBLIGATORIO (Anti-Spam) ---
    if not db_user.get('email'):
        await update.message.reply_text(
            f"🛡 **SISTEMA DE SEGURIDAD THE HIVE**\n\n"
            f"Hola {user.first_name}. Para evitar bots y proteger la economía del servidor, "
            "necesitamos validar tu identidad.\n\n"
            "📧 **Paso 1:** Escribe tu correo electrónico para continuar:",
            parse_mode="Markdown"
        )
        return WAIT_EMAIL
    
    # --- FILTRO 2: API GATE / DESCARGA OBLIGATORIA (Monetización/Seguridad) ---
    if not db_user.get('api_gate_passed'):
        keyboard = [[InlineKeyboardButton("🔓 ACTIVAR CUENTA", callback_data="check_gate")]]
        await update.message.reply_text(
            "🔒 **CUENTA BLOQUEADA**\n\n"
            "Tu email está registrado, pero falta la validación del nodo.\n"
            "Esto asegura que eres un usuario real y único.\n\n"
            "👇 Presiona el botón para verificar tu conexión API:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return WAIT_API_CHECK

    # --- SI PASA TODO: AL MENÚ ---
    await menu_handler(update, context)
    return ConversationHandler.END

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el email y pasa al siguiente filtro."""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validación básica
    if "@" not in text or "." not in text:
        await update.message.reply_text("❌ Email inválido. Intenta de nuevo:")
        return WAIT_EMAIL
    
    # Guardar en DB
    await save_user_email(user_id, text, market_value=0.10)
    
    keyboard = [[InlineKeyboardButton("🔓 ACTIVAR CUENTA", callback_data="check_gate")]]
    await update.message.reply_text(
        f"✅ **Email verificado:** `{text}`\n\n"
        "⚠ **ÚLTIMO PASO:** Tu cuenta está en 'Modo Restringido'.\n"
        "Necesitamos verificar tu dispositivo.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAIT_API_CHECK

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simula la verificación de API/Descarga."""
    query = update.callback_query
    await query.answer("🔄 Conectando con servidor de validación...")
    
    user_id = update.effective_user.id
    
    # AQUÍ SE APLICA LA LÓGICA DE DESBLOQUEO
    # En el futuro, aquí podrías verificar si realmente instalaron una app o vieron un anuncio.
    await unlock_api_gate(user_id)
    
    await query.edit_message_text(
        "🚀 **¡ACCESO CONCEDIDO!**\n\n"
        "Bienvenido a The Hive. Ya puedes generar ingresos.",
        parse_mode="Markdown"
    )
    
    # Mostrar menú principal
    await show_main_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del menú principal."""
    await show_main_menu(update.effective_chat.id, context)

async def show_main_menu(chat_id, context):
    """Interfaz Gráfica del Menú Principal."""
    user_data = await get_user_fast(chat_id)
    
    balance_hive = user_data.get('balance_hive', 0.0)
    balance_usd = user_data.get('balance_available', 0.0) # Usamos available (The Hive original)
    rank = user_data.get('rank', 'LARVA')
    
    text = (
        f"🐝 **THE HIVE: DASHBOARD**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Rango: **{rank}**\n"
        f"💰 Saldo: **${balance_usd:.2f} USD**\n"
        f"🍯 Miel: **{balance_hive:.0f} pts**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        "¿Qué deseas hacer hoy?"
    )
    
    keyboard = [
        [InlineKeyboardButton("⛏ MINAR MIEL (Tap)", callback_data="mine_tap")],
        [InlineKeyboardButton("🏦 RETIRAR DINERO", callback_data="try_withdraw")]
    ]
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text=text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    stats = await update_gamification(user_id)
    streak = stats.get('streak', 0)
    
    await query.answer(f"⛏ +10 Miel recolectada | Racha: {streak} días", show_alert=False)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    user_data = await get_user_fast(user_id)
    balance = user_data.get('balance_available', 0.0)
    
    if balance < 10.0:
        await query.message.reply_text(
            f"❌ **Saldo insuficiente**\nMinimo: $10.00\nTu saldo: ${balance:.2f}",
            quote=True
        )
    else:
        await query.message.reply_text("✅ Procesando solicitud de retiro...", quote=True)

async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    COMANDO /reset: Reinicia la cuenta para pruebas.
    SOLUCIONADO: Ahora usa database.db_pool para acceder a la conexión viva.
    """
    user = update.effective_user
    
    # Verificación correcta de la conexión
    if not database.db_pool: 
        await update.message.reply_text("❌ Error crítico: Base de datos desconectada.")
        return

    try:
        async with database.db_pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE telegram_id=$1", user.id)
            await conn.execute("DELETE FROM leads_harvest WHERE telegram_id=$1", user.id)
            await conn.execute("DELETE FROM transactions WHERE user_id=$1", user.id)
            # Limpiar tablas extra si existen
            await conn.execute("DELETE FROM ledger WHERE user_id=$1", user.id)
            
            if database.redis_client:
                await database.redis_client.delete(f"user:{user.id}")

        await update.message.reply_text(
            "🔄 **RESET COMPLETADO**\n\n"
            "Tu cuenta ha sido eliminada.\n"
            "Escribe **/start** para probar el flujo de Email y API nuevamente."
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error SQL: {e}")
