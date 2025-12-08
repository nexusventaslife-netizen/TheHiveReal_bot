import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Importamos las funciones de DB
from database import (
    add_user,
    get_user,
    update_user_email,
    add_lead,
    update_user_gate_status,
    get_user_balance
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Link de Adsterra (Fallback seguro a Google para no romper)
ADSTERRA_LINK = os.getenv("ADSTERRA_LINK", "https://google.com")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Registrar usuario
    await add_user(user.id, user.first_name, user.username)
    
    # 2. Consultar estado
    db_user = await get_user(user.id)
    
    # CASO A: Todo completo -> Menú
    if db_user and db_user.get('email') and db_user.get('api_gate_passed'):
        await menu_handler(update, context)
        return

    # CASO B: Tiene Email, falta Gate
    if db_user and db_user.get('email') and not db_user.get('api_gate_passed'):
        await show_gate_message(update, context)
        return

    # CASO C: Nuevo -> Pedir Email
    await update.message.reply_text(
        f"👋 <b>Hola {user.first_name}!</b> Bienvenido a TheHiveReal.\n\n"
        "📧 <b>PASO 1:</b> Para crear tu billetera, envíame tu <b>correo electrónico</b>.",
        parse_mode="HTML"
    )
    context.user_data['waiting_for_email'] = True

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Validación simple
    if not re.match(r'[^@]+@[^@]+\.[^@]+', text):
        await update.message.reply_text("❌ Email inválido. Inténtalo de nuevo.")
        return

    await update_user_email(user_id, text)
    await add_lead(user_id, text) # Guardar en harvest
    
    await update.message.reply_text(f"✅ Email registrado. Pasando a verificación...")
    await show_gate_message(update, context)

async def show_gate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚨 <b>VERIFICACIÓN DE SEGURIDAD</b>\n\n"
        "Para activar la minería, completa este paso rápido:\n"
        "1. Toca <b>'ACTIVAR CUENTA'</b>.\n"
        "2. Espera 5 seg en la página.\n"
        "3. Toca <b>'YA LO HICE'</b>."
    )
    keyboard = [
        [InlineKeyboardButton("🚀 1. ACTIVAR CUENTA", url=ADSTERRA_LINK)],
        [InlineKeyboardButton("✅ 2. YA LO HICE", callback_data="check_gate_verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def check_gate_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Verificando...")
    
    # Validamos y pasamos al menú
    await update_user_gate_status(query.from_user.id, True)
    await query.message.edit_text("✅ <b>¡CUENTA ACTIVADA!</b>", parse_mode="HTML")
    await menu_handler(update, context)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = await get_user_balance(user_id)
    
    text = (
        f"🐝 <b>DASHBOARD</b>\n"
        f"💰 USD: ${bal['balance_usd']:.4f}\n"
        f"🍯 Miel: {bal['balance_hive']}\n"
    )
    keyboard = [
        [InlineKeyboardButton("⛏️ MINAR", callback_data="mine_tap")],
        [InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("⛏️ +5 Miel (Simulado)")

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Minimo $5.00 USD", show_alert=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Soporte: @admin")
