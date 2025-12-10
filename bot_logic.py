import logging
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE ECONOMÍA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 100 

# --- CONFIGURACIÓN DE ENLACES ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"
LINK_SMART_TASKS = f"{RENDER_URL}/go"

# Tus enlaces de Afiliado (CPA)
OFFERS = {
    'US': {'link': 'https://freecash.com/r/TU_LINK_USA', 'name': '🇺🇸 Misión VIP USA'},
    'ES': {'link': 'https://www.bybit.com/invite?ref=LINK_ESPANA', 'name': '🇪🇸 Verificar ID España'},
    'MX': {'link': 'https://bitso.com/?ref=LINK_MEXICO', 'name': '🇲🇽 Bono Crypto México'},
    'AR': {'link': 'https://lemon.me/LINK_ARGENTINA', 'name': '🇦🇷 Validar Wallet Arg'},
    'DEFAULT': {'link': 'https://otieu.com/4/10302294', 'name': '🌍 Verificación Global'} 
}

# --- FUNCIÓN DE INICIO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if hasattr(db, 'add_user'):
        await db.add_user(user.id, user.first_name, user.username)

    # 1. Borramos el teclado viejo feo (si existe)
    waiting_msg = await update.message.reply_text(
        "🔄 *Cargando Interfaz TheOneHive...*", 
        reply_markup=ReplyKeyboardRemove(), # ESTO BORRA EL TECLADO DE ABAJO
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)
    await context.bot.delete_message(chat_id=user.id, message_id=waiting_msg.message_id)

    # 2. Mensaje de Bienvenida Estilo Terminal
    welcome_text = (
        f"🖥️ **SISTEMA DE CONTROL v2.4**\n"
        f"👤 Usuario: `{user.first_name}`\n"
        f"🟢 Estado: Conectado\n\n"
        "🔒 **ACCESO REQUERIDO**\n"
        "Para ingresar al Dashboard Principal, valida tu identidad humana."
    )
    
    keyboard = [[InlineKeyboardButton("🛡️ INICIAR PROTOCOLO DE ACCESO", url=LINK_ENTRY_DETECT)]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- MANEJADOR DE TEXTO (Detector de Código) ---
async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user
    
    # Si escriben comandos viejos, redirigir al Dashboard
    if text in ["MINAR", "PERFIL", "TAREAS"]:
        await show_dashboard(update, context)
        return

    # CASO EMAIL
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)

            msg_wait = await update.message.reply_text("⚙️ *Configurando entorno...*", parse_mode="Markdown")
            await asyncio.sleep(1.5)
            try: await context.bot.delete_message(chat_id=user.id, message_id=msg_wait.message_id)
            except: pass
            
            # AL FINALIZAR REGISTRO -> VAMOS AL DASHBOARD DIRECTO
            await show_dashboard(update, context)
            return
        else:
            await update.message.reply_text("❌ Error de sintaxis en Email.")
            return

    # CASO CÓDIGO
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        country = parts[2] if len(parts) >= 3 else 'GL'
        context.user_data['country'] = country
        
        await update.message.reply_text(
            f"🌍 **Región Detectada: {country}**\n"
            "📥 Ingresa tu **Email** para finalizar:",
            parse_mode="Markdown"
        )
        context.user_data['waiting_for_email'] = True
        return

# --- EL NUEVO DASHBOARD "DARK MODE" (Sin duplicados) ---
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el panel principal limpio y moderno."""
    user = update.effective_user
    country = context.user_data.get('country', 'GL')
    
    # Datos Simulados (Luego vendrán de DB)
    tokens = INITIAL_BONUS
    usd_val = tokens * HIVE_PRICE
    
    # DISEÑO GRÁFICO CON TEXTO (Estilo Neon/Dark)
    dashboard_text = (
        f"⬛⬛⬛⬛ **THE ONE HIVE** ⬛⬛⬛⬛\n"
        f"ID: `{user.id}` | 🏳️ `{country}`\n\n"
        
        f"📊 **MÉTRICAS EN TIEMPO REAL**\n"
        f"➤ Rendimiento: ▮▮▮▮▮▮▮▮▯▯ 80%\n"
        f"➤ Nivel de Cuenta: **PRINCIPIANTE**\n\n"
        
        f"💰 **BILLETERA HÍBRIDA**\n"
        f"🪙 **{tokens} HIVE** (Tokens Minados)\n"
        f"💵 **${usd_val:.2f} USD** (Saldo Retirable)\n\n"
        
        f"🚀 **ACCIONES RÁPIDAS**\n"
        f"Selecciona una operación en la consola:"
    )
    
    # BOTONES DE NAVEGACIÓN (Limpio, sin menú abajo)
    keyboard = [
        [InlineKeyboardButton("⚡ MINAR & TAREAS (Boost)", callback_data="go_tasks")],
        [InlineKeyboardButton("👥 RED DE REFERIDOS", callback_data="invite_friends"), InlineKeyboardButton("🎒 MIS NFTs", callback_data="my_nfts")],
        [InlineKeyboardButton("⚙️ MI PERFIL", callback_data="my_profile"), InlineKeyboardButton("🏧 RETIRAR FONDOS", callback_data="withdraw")]
    ]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- MENÚ DE TAREAS (Estilo Neon) ---
async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = context.user_data.get('country', 'DEFAULT')
    offer = OFFERS.get(country, OFFERS['DEFAULT'])
    
    text = (
        f"⚡ **CENTRO DE MINERÍA**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Para aumentar tu Hashrate y ganar USD, completa los nodos activos:\n\n"
        
        f"🔥 **NODO PRIORITARIO (High Paying)**\n"
        f"➤ Misión: {offer['name']}\n"
        f"➤ Recompensa: **NFT Boost x5** + Bonos USD\n"
        f"➤ Estado: 🟢 Disponible\n\n"
        
        f"⚠️ _No uses VPN o el nodo rechazará la conexión._"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"🚀 INICIAR SECUENCIA DE MINADO", url=offer['link'])],
        [InlineKeyboardButton("🔙 VOLVER AL DASHBOARD", callback_data="go_dashboard")]
    ]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- PERFIL DEL USUARIO (Nuevo) ---
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    email = context.user_data.get('email', 'No verificado')
    
    text = (
        f"⚙️ **PERFIL DE OPERADOR**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Nombre: {user.first_name}\n"
        f"📧 Email: `{email}`\n"
        f"🛡️ Estado: Verificado\n"
        f"📅 Miembro desde: Hoy\n\n"
        f"🔧 **Opciones de Cuenta:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ Cambiar Email", callback_data="change_email")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- MANEJADOR DE BOTONES ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Confirma click para que no cargue infinito
    
    data = query.data
    
    if data == "go_tasks":
        await tasks_menu(update, context)
    elif data == "go_dashboard":
        await show_dashboard(update, context)
    elif data == "my_profile":
        await profile_menu(update, context)
    elif data == "invite_friends":
        link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
        await query.message.reply_text(f"🔗 **ENLACE DE RECLUTAMIENTO:**\n`{link}`", parse_mode="Markdown")
    elif data == "withdraw":
        await query.message.reply_text("⚠️ **ERROR DE SALDO:**\nNecesitas mínimo $10.00 USD para retirar.\nVe a 'MINAR & TAREAS' para llegar a la meta.", parse_mode="Markdown")
    elif data == "my_nfts":
         await query.message.reply_text("🎒 **INVENTARIO VACÍO**\nCompleta tareas para ganar NFTs de potencia.", parse_mode="Markdown")

# Comandos y Handlers Standard
async def help_command(u, c): await u.message.reply_text("Ayuda: /start")
async def invite_command(u, c): await u.message.reply_text("Invitar...")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset completo.")
