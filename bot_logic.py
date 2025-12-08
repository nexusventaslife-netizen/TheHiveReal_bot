import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    register_user_smart, 
    get_user_fast, 
    save_user_email, 
    unlock_api_gate, 
    update_gamification, 
    db_pool,
    redis_client
)

logger = logging.getLogger("Hive.Logic")

# Constantes para ConversationHandler (deben coincidir con lo que main.py espera)
WAIT_EMAIL = 1
WAIT_API_CHECK = 2

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicio del bot: Verifica estado del usuario y decide el flujo."""
    user = update.effective_user
    logger.info(f"User {user.id} started bot")
    
    # 1. Registro silencioso en base de datos
    await register_user_smart(user)
    
    # 2. Verificar estado actual del usuario
    db_user = await get_user_fast(user.id)
    
    # Flujo A: Si no tiene email, forzamos el flujo de conversación
    if not db_user.get('email'):
        await update.message.reply_text(
            f"👋 **Bienvenido, {user.first_name}!**\n\n"
            "Para acceder al Panal (The Hive), necesitamos verificar tu identidad.\n"
            "📧 **Por favor, envía tu correo electrónico para continuar:**",
            parse_mode="Markdown"
        )
        return WAIT_EMAIL
    
    # Flujo B: Si tiene email pero no ha pasado el API Gate
    if not db_user.get('api_gate_passed'):
        keyboard = [[InlineKeyboardButton("🔍 Verificar Conexión", callback_data="check_gate")]]
        await update.message.reply_text(
            "🔒 **Verificación de Seguridad**\n\n"
            "Tu email ya está registrado. Falta un último paso de seguridad.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return WAIT_API_CHECK

    # Flujo C: Usuario completo, mostrar menú principal
    await menu_handler(update, context)
    return ConversationHandler.END

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y guarda el email del usuario."""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validación simple de email
    if "@" not in text or "." not in text:
        await update.message.reply_text("❌ **Email inválido.** Por favor intenta de nuevo:")
        return WAIT_EMAIL
    
    # Guardar email en DB
    await save_user_email(user_id, text, market_value=0.10)
    
    keyboard = [[InlineKeyboardButton("✅ Verificar Acceso", callback_data="check_gate")]]
    await update.message.reply_text(
        f"✅ **Email guardado:** `{text}`\n\n"
        "Presiona el botón abajo para validar tu acceso al sistema.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAIT_API_CHECK

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cuando el usuario presiona 'Verificar API'."""
    query = update.callback_query
    await query.answer("🔄 Verificando credenciales...")
    
    user_id = update.effective_user.id
    
    # Desbloquear usuario en DB
    await unlock_api_gate(user_id)
    
    await query.edit_message_text(
        "🔓 **ACCESO CONCEDIDO**\n"
        "Bienvenido a la Colmena."
    , parse_mode="Markdown")
    
    # Mostrar el menú principal
    await show_main_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para mensajes de texto normales o retorno al menú."""
    await show_main_menu(update.effective_chat.id, context)

async def show_main_menu(chat_id, context):
    """Función auxiliar para enviar el menú visual."""
    # Recuperamos datos frescos del usuario
    user_data = await get_user_fast(chat_id)
    
    # Valores por defecto si es la primera vez
    balance_hive = user_data.get('balance_hive', 0.0)
    balance_usd = user_data.get('balance_available', 0.0)
    rank = user_data.get('rank', 'LARVA')
    
    text = (
        f"🐝 **PANEL DE CONTROL - THE HIVE**\n\n"
        f"👤 Rango: **{rank}**\n"
        f"🍯 Miel (Points): `{balance_hive:.2f}`\n"
        f"💵 Saldo USD: `${balance_usd:.2f}`\n\n"
        "👇 _Selecciona una acción:_"
    )
    
    keyboard = [
        [InlineKeyboardButton("⛏ MINAR MIEL", callback_data="mine_tap")],
        [InlineKeyboardButton("🏦 RETIRAR FONDOS", callback_data="try_withdraw")]
    ]
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text=text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción al presionar Minar."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Actualizamos racha y actividad
    stats = await update_gamification(user_id)
    streak = stats.get('streak', 0)
    
    # Feedback visual (sin editar mensaje para no saturar API)
    await query.answer(f"⛏ ¡Recolectando! Racha: {streak} días", show_alert=False)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción al presionar Retirar."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    user_data = await get_user_fast(user_id)
    balance = user_data.get('balance_available', 0.0)
    
    if balance < 10.0:
        await query.message.reply_text(
            f"⚠️ **Saldo insuficiente**\n"
            f"Tu saldo: `${balance:.2f}`\n"
            f"Mínimo para retirar: `$10.00`",
            parse_mode="Markdown",
            quote=True
        )
    else:
        await query.message.reply_text("✅ Iniciando proceso de retiro seguro...", quote=True)

async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """COMANDO DE DESARROLLO: Borra tu cuenta para probar el registro desde cero"""
    user = update.effective_user
    if not db_pool: 
        await update.message.reply_text("❌ Error: Base de datos no conectada.")
        return

    async with db_pool.acquire() as conn:
        # Borramos todo rastro tuyo
        await conn.execute("DELETE FROM users WHERE telegram_id=$1", user.id)
        await conn.execute("DELETE FROM leads_harvest WHERE telegram_id=$1", user.id)
        await conn.execute("DELETE FROM transactions WHERE user_id=$1", user.id)
        
        # Limpiamos caché de Redis si existe
        if redis_client:
            await redis_client.delete(f"user:{user.id}")

    await update.message.reply_text(
        "🔄 **CUENTA DE FÁBRICA RESTAURADA**\n\n"
        "El sistema ya no te conoce.\n"
        "Escribe **/start** para simular ser un usuario nuevo (te pedirá Email y API)."
    )
