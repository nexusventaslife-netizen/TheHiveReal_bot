import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Importamos las funciones de base de datos
# Asegúrate de que database.py tenga estas funciones o adáptalas
from database import (
    add_user,
    get_user,
    update_user_email,
    add_lead,
    update_user_gate_status,
    get_user_balance
)

# --- CONFIGURACIÓN ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Link de Adsterra desde Variables de Entorno (Fallback a Google si falla para no romper el bot)
ADSTERRA_LINK = os.getenv("ADSTERRA_LINK", "https://google.com")

# --- FLUJO DE INICIO (/start) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Punto de entrada. Verifica el estado del usuario en la DB
    y lo dirige al paso que le falta (Email -> Gate -> Menú).
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 1. Registrar o recuperar usuario de la DB
    # (add_user debe manejar si el usuario ya existe para no dar error)
    await add_user(user.id, user.first_name, user.username)
    
    # 2. Consultar datos actuales del usuario
    db_user = await get_user(user.id)
    
    # --- LÓGICA DE ESTADOS ---
    
    # CASO A: Ya completó todo -> Ir al Menú
    if db_user and db_user.get('email') and db_user.get('api_gate_passed'):
        await menu_handler(update, context)
        return

    # CASO B: Tiene Email pero falta el Gate (Adsterra)
    if db_user and db_user.get('email') and not db_user.get('api_gate_passed'):
        await show_gate_message(update, context)
        return

    # CASO C: Usuario Nuevo o sin Email -> Pedir Email
    await update.message.reply_text(
        f"👋 <b>Hola {user.first_name}!</b> Bienvenido a TheHiveReal.\n\n"
        "🤖 Somos una Reward App que te paga por tareas simples.\n\n"
        "📧 <b>PASO 1:</b> Para crear tu billetera y evitar bots, "
        "por favor <b>envíame tu correo electrónico</b> ahora mismo.",
        parse_mode="HTML"
    )
    # Marcamos en el contexto que esperamos un email (opcional si usas lógica stateless)
    context.user_data['waiting_for_email'] = True


# --- MANEJO DE EMAIL ---

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Captura cualquier texto enviado por el usuario y valida si es un email.
    """
    # Si estamos en el menú, ignorar textos o manejar comandos
    # Aquí asumimos que si no ha pasado el gate, cualquier texto es un intento de email
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Validación simple de Regex para Email
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, text):
        await update.message.reply_text("❌ Eso no parece un email válido. Inténtalo de nuevo.")
        return

    # 1. Guardar Email en la tabla de usuarios
    await update_user_email(user_id, text)
    
    # 2. Guardar en leads_harvest (Para venta de datos/backup)
    await add_lead(user_id, text)
    
    await update.message.reply_text(f"✅ Email <b>{text}</b> registrado correctamente.", parse_mode="HTML")
    
    # 3. Pasar inmediatamente al Gate de Monetización
    await show_gate_message(update, context)


# --- GATE DE SEGURIDAD (MONETIZACIÓN ADSTERRA) ---

async def show_gate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra el botón de Adsterra.
    Usa estrategia de DOBLE BOTÓN para asegurar el click y la validación.
    """
    # Texto persuasivo
    text = (
        "🚨 <b>ÚLTIMO PASO DE SEGURIDAD</b> 🚨\n\n"
        "Nuestro sistema detecta tráfico nuevo. Para activar tu billetera y empezar a minar, "
        "necesitas validar tu sesión.\n\n"
        "👇 <b>INSTRUCCIONES:</b>\n"
        "1. Toca <b>'ACTIVAR CUENTA'</b> (Se abrirá un enlace seguro).\n"
        "2. Espera 5 segundos en la página.\n"
        "3. Vuelve aquí y toca <b>'✅ YA LO HICE'</b>."
    )

    keyboard = [
        # BOTÓN 1: URL EXTERNA (Adsterra) - Telegram abre el navegador
        [InlineKeyboardButton("🚀 1. ACTIVAR CUENTA (Click Aquí)", url=ADSTERRA_LINK)],
        
        # BOTÓN 2: CALLBACK INTERNO - Verifica la acción
        [InlineKeyboardButton("✅ 2. YA LO HICE / VERIFICAR", callback_data="check_gate_verify")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar o Editar mensaje dependiendo del contexto
    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        # Si venimos de un callback anterior, editamos para no hacer spam
        try:
            await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            # Fallback si el mensaje es muy viejo
            await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)


async def check_gate_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja el botón 'YA LO HICE'.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("🔄 Verificando conexión...")

    # AQUÍ ESTÁ EL TRUCO:
    # Como Adsterra no nos avisa server-to-server, confiamos en el click del usuario
    # pero forzamos la interacción de dos pasos.
    
    # 1. Actualizar DB
    await update_user_gate_status(user_id, status=True)

    # 2. Feedback positivo
    await query.message.reply_text("✅ <b>¡CUENTA ACTIVADA!</b> Accediendo al sistema...", parse_mode="HTML")
    
    # 3. Ir al Menú Principal
    await menu_handler(update, context)


# --- MENÚ PRINCIPAL Y LÓGICA DEL BOT ---

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dashboard principal del usuario.
    """
    user = update.effective_user
    user_id = user.id
    
    # Obtener saldos actualizados de la DB
    # Retorna tupla o dict: {'balance_usd': 0.00, 'balance_hive': 0}
    financials = await get_user_balance(user_id) 
    
    usd = financials.get('balance_usd', 0.0)
    hive = financials.get('balance_hive', 0)

    text = (
        f"🐝 <b>THE HIVE REAL - DASHBOARD</b>\n"
        f"👤 Usuario: {user.first_name}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 <b>Saldo USD:</b> ${usd:.4f}\n"
        f"🍯 <b>Miel (Puntos):</b> {hive} HIVE\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"¡Mina puntos o invita amigos para ganar dinero real!"
    )

    keyboard = [
        [InlineKeyboardButton("⛏️ MINAR MIEL", callback_data="mine_tap")],
        [InlineKeyboardButton("👥 REFERIDOS", callback_data="referrals_menu"), 
         InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw_menu")],
        [InlineKeyboardButton("🆘 SOPORTE / AYUDA", callback_data="help_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)


# --- HANDLERS DE ACCIONES DEL MENÚ ---

async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Simulación de minería. Aquí integraremos Shortlinks (Ouo.io) en el futuro.
    """
    query = update.callback_query
    await query.answer("⛏️ ¡Minando... +5 HIVE!")
    
    # TODO: Llamar a DB para sumar puntos
    # await add_balance(user_id, hive=5)
    
    # Efecto visual simple: Editar el mensaje con el nuevo saldo (opcional)
    # Por ahora solo notificamos con el alert de arriba.
    pass

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("⚠️ El mínimo de retiro es $5.00 USD. Sigue minando.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    UTILIDAD DE DEBUG: Permite resetear tu propio usuario para probar el flujo de nuevo.
    """
    # Solo permitir al admin o en modo debug
    # await reset_user_db(update.effective_user.id)
    await update.message.reply_text("🔄 Usuario reseteado (Simulación). Escribe /start para probar de cero.")
