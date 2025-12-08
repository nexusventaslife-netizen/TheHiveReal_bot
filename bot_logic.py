import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    add_user, 
    add_lead, 
    update_user_gate_status, 
    get_user, 
    get_user_balance,
    add_hive_points,
    update_user_email
)

logger = logging.getLogger("Hive.Logic")
ADSTERRA_LINK = os.getenv("ADSTERRA_LINK", "https://google.com") 

# --- COMANDO START (Punto de Entrada) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Registrar usuario en DB (Si no existe)
    await add_user(user.id, user.first_name, user.username)
    
    # 2. Consultar estado actual
    db_user = await get_user(user.id)
    
    # CASO A: Usuario Completo (Email + Gate) -> Ver Menú
    if db_user and db_user.get('email') and db_user.get('api_gate_passed'):
        await menu_handler(update, context)
        return

    # CASO B: Tiene Email pero falta Gate (Adsterra)
    if db_user and db_user.get('email') and not db_user.get('api_gate_passed'):
        await show_gate_message(update, context)
        return

    # CASO C: Usuario Nuevo (Falta Email)
    await update.message.reply_text(
        f"👋 <b>Hola {user.first_name}!</b>\n\n"
        "🔒 Para proteger la economía del bot, necesitamos un registro único.\n\n"
        "📧 <b>ESCRIBE TU EMAIL:</b> Por favor, envíame tu correo electrónico ahora para continuar.",
        parse_mode="HTML"
    )

# --- PROCESAMIENTO INTELIGENTE DE EMAIL ---
async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # 1. VERIFICAR SI EL USUARIO YA TIENE EMAIL
    # Si ya tiene email, NO intentamos validarlo de nuevo. Lo mandamos al menú o al gate.
    db_user = await get_user(user_id)
    
    if db_user and db_user.get('email'):
        # Ya está registrado, no necesitamos validar nada.
        if not db_user.get('api_gate_passed'):
            await show_gate_message(update, context)
        else:
            await menu_handler(update, context)
        return

    # 2. VALIDACIÓN (Solo si NO tiene email)
    # Regex simple para evitar falsos positivos con texto normal
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, text):
        await update.message.reply_text(
            "❌ <b>Email no válido.</b>\n"
            "Por favor asegúrate de enviar un correo real (ejemplo: `nombre@gmail.com`).\n"
            "Inténtalo de nuevo 👇",
            parse_mode="HTML"
        )
        return

    # 3. GUARDAR EMAIL
    await update_user_email(user_id, text)
    await add_lead(user_id, text)
    
    # 4. AVANZAR
    await update.message.reply_text(f"✅ Guardado: {text}")
    await show_gate_message(update, context)


# --- GATE DE SEGURIDAD (ADSTERRA) ---
async def show_gate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚨 <b>VERIFICACIÓN FINAL</b> 🚨\n\n"
        "Para activar tu billetera:\n"
        "1. Toca <b>'ACTIVAR CUENTA'</b> (Link Seguro).\n"
        "2. Espera 5 segundos.\n"
        "3. Vuelve y toca <b>'YA LO HICE'</b>."
    )
    keyboard = [
        [InlineKeyboardButton("🚀 1. ACTIVAR CUENTA", url=ADSTERRA_LINK)],
        [InlineKeyboardButton("✅ 2. YA LO HICE", callback_data="check_gate_verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        # Intenta editar, si falla (mensaje viejo) envía uno nuevo
        try:
            await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            await context.bot.send_message(update.effective_chat.id, text, parse_mode="HTML", reply_markup=reply_markup)

async def check_gate_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Verificando...")
    
    # Validar
    await update_user_gate_status(query.from_user.id, True)
    
    try:
        await query.message.edit_text("✅ <b>¡CUENTA ACTIVADA!</b>", parse_mode="HTML")
    except:
        pass
        
    await menu_handler(update, context)

# --- MENÚ PRINCIPAL ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = await get_user_balance(user_id)
    
    text = (
        f"🐝 <b>HIVE DASHBOARD</b>\n\n"
        f"💵 Saldo: <b>${bal['balance_usd']:.4f} USD</b>\n"
        f"🍯 Miel: <b>{bal['balance_hive']}</b>\n\n"
        "👇 Toca MINAR para ganar puntos."
    )
    keyboard = [
        [InlineKeyboardButton("⛏️ MINAR MIEL", callback_data="mine_tap")],
        [InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

# --- ACCIONES ---
async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Sumar puntos
    await add_hive_points(user_id, 10) # 10 puntos por click
    
    await update.callback_query.answer("⛏️ +10 Miel!")
    # No editamos el mensaje para evitar Rate Limit, solo el popup (answer)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("⚠️ Mínimo $10.00 USD", show_alert=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos: /start, /menu")
