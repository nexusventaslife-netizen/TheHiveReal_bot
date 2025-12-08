import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    add_user, 
    add_lead, 
    update_user_gate_status, 
    get_user, 
    get_balance,
    add_hive_points
)

logger = logging.getLogger("Hive.Logic")

# ENLACE DE ADSTERRA (Cámbialo en Render Environment Variables o usa este fallback)
# Este link es el que genera $$$.
ADSTERRA_LINK = os.getenv("ADSTERRA_DIRECT_LINK", "https://google.com") 

# --- COMANDO START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # Para referidos en el futuro
    
    # Registrar usuario en DB
    await add_user(user.id, user.username, user.first_name)
    
    # Verificar si ya pasó el Gate
    db_user = await get_user(user.id)
    if db_user and db_user['gate_passed']:
        await menu_handler(update, context)
        return

    # Si no ha pasado el gate, pedir Email
    await update.message.reply_text(
        f"👋 Hola {user.first_name}!\n\n"
        "🔒 **Sistema de Seguridad TheHive**\n"
        "Para proteger la economía del token y evitar bots, necesitamos validar tu registro.\n\n"
        "📧 **Paso 1:** Por favor, escribe y envíame tu **correo electrónico** para continuar."
    )
    # Marcar estado interno (opcional si usas ConversationHandler, pero esto funciona con el MessageHandler simple del main)
    context.user_data['awaiting_email'] = True

# --- PROCESAMIENTO DE EMAIL Y GATE ---
async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recibe el email, lo guarda y muestra el botón de Adsterra.
    """
    user_id = update.effective_user.id
    email_text = update.message.text.strip()
    
    # Validación simple de formato email
    if "@" not in email_text or "." not in email_text:
        await update.message.reply_text("❌ Formato inválido. Por favor envía un email real (ej: usuario@gmail.com).")
        return

    # Guardar en DB
    success = await add_lead(user_id, email_text)
    if not success:
        await update.message.reply_text("⚠️ Hubo un error guardando tus datos. Intenta de nuevo.")
        return

    # --- LÓGICA DE MONETIZACIÓN (ADSTERRA) ---
    logger.info(f"Email capturado para {user_id}. Mostrando Link de Adsterra: {ADSTERRA_LINK}")
    
    # Botón 1: Va a Adsterra (Usuario ve anuncios -> Tú ganas $$$)
    # Botón 2: Callback para verificar que volvió
    keyboard = [
        [InlineKeyboardButton("🔓 ACTIVAR CUENTA (Click Aquí)", url=ADSTERRA_LINK)],
        [InlineKeyboardButton("✅ YA COMPLETÉ EL PASO", callback_data="check_gate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Email `{email_text}` registrado.\n\n"
        "🚨 **ÚLTIMO PASO DE ACTIVACIÓN** 🚨\n"
        "Tu billetera está bloqueada temporalmente. Para desbloquearla:\n\n"
        "1. Toca el botón **'ACTIVAR CUENTA'** y espera 5 segundos en la página.\n"
        "2. Vuelve aquí y toca **'YA COMPLETÉ EL PASO'**.\n\n"
        "👇 _Hazlo ahora para entrar al menú_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback cuando el usuario dice que ya vio el anuncio.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("🔄 Verificando...")
    
    # Aquí asumimos que lo hizo (Estrategia Adsterra Direct Link)
    # En el futuro, con Shortlinks (Ouo.io), aquí validaremos el token real.
    
    await update_user_gate_status(user_id, True)
    
    await query.edit_message_text(
        "✅ **¡CUENTA VERIFICADA!**\n\n"
        "Bienvenido a la Colmena. Ya puedes empezar a generar Miel.",
        parse_mode="Markdown"
    )
    
    # Mostrar menú principal
    await menu_handler(update, context)

# --- MENÚ PRINCIPAL ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Obtener saldo fresco de la DB
    usd, hive = await get_balance(user_id)
    
    keyboard = [
        [InlineKeyboardButton("⛏️ MINAR MIEL (Tap)", callback_data="mine_tap")],
        [InlineKeyboardButton("🏦 RETIRAR FONDOS", callback_data="withdraw")],
        [InlineKeyboardButton("🔗 REFERIDOS (Pronto)", callback_data="ref_system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"🐝 **DASHBOARD PRINCIPAL**\n\n"
        f"💵 Saldo USD: **${usd:.4f}**\n"
        f"🍯 Miel (Puntos): **{hive:.2f}**\n\n"
        "La Miel se convierte a USD cada 24h."
    )
    
    if update.callback_query:
        # Si venimos de un botón, editamos para no hacer spam
        try:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            # Si el mensaje es muy viejo o idéntico, enviamos uno nuevo
            await context.bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        # Si venimos del comando /menu
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- FUNCIONES DE MINERÍA Y RETIRO ---

async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Gamificación simple: Sumar 0.5 puntos de Miel
    await add_hive_points(user_id, 0.5)
    await query.answer("🔨 +0.5 Miel minada!")
    
    # Actualizar visualmente (Opcional: Para no saturar la API, no editamos el mensaje en cada click, solo alertamos)
    # Si quieres actualizar el texto, descomenta la siguiente línea, pero cuidado con el Rate Limit de Telegram:
    # await menu_handler(update, context)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    usd, _ = await get_balance(query.from_user.id)
    
    if usd < 10.0:
        await query.message.reply_text(
            f"❌ **Mínimo de retiro: $10.00 USD**\n"
            f"Tu saldo actual: ${usd:.4f}\n\n"
            "Sigue minando o invita amigos para llegar más rápido.",
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text("✅ Tienes fondos suficientes. Contacta a soporte para procesar el pago.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **AYUDA**\n\n"
        "/start - Reiniciar el bot\n"
        "/menu - Ver saldo y minar\n"
        "Si tienes problemas, contacta a @Soporte."
    )
