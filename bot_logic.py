import logging
import re
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE ECONOMÍA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 100 
MIN_WITHDRAW = 10.00

# --- TUS ENLACES DE RENDER (CÁMBIALOS SI ES NECESARIO) ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"
LINK_SMART_TASKS = f"{RENDER_URL}/go"

# --- TUS OFERTAS REALES (CPA) ---
OFFERS = {
    'US': {'link': 'https://freecash.com/r/TU_LINK_USA', 'name': '🇺🇸 Misión VIP USA (High Pay)'},
    'ES': {'link': 'https://www.bybit.com/invite?ref=LINK_ESPANA', 'name': '🇪🇸 Verificar ID España'},
    'MX': {'link': 'https://bitso.com/?ref=LINK_MEXICO', 'name': '🇲🇽 Bono Crypto México'},
    'AR': {'link': 'https://lemon.me/LINK_ARGENTINA', 'name': '🇦🇷 Validar Wallet Arg'},
    'CO': {'link': 'https://binance.com/LINK_COLOMBIA', 'name': '🇨🇴 Misión Colombia'},
    'DEFAULT': {'link': 'https://otieu.com/4/10302294', 'name': '🌍 Verificación Global'} 
}

# --- INICIO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if hasattr(db, 'add_user'): await db.add_user(user.id, user.first_name, user.username)

    # Borrado de teclado viejo
    msg = await update.message.reply_text("🔄 *System Boot...*", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await asyncio.sleep(1)
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    welcome_text = (
        f"🐝 **THE ONE HIVE OS** `v3.1`\n"
        f"👤 Operador: `{user.first_name}`\n"
        f"🟢 Estado: **Online**\n\n"
        "Bienvenido a la Colmena. Somos la revolución de la fuerza laboral descentralizada.\n\n"
        "🔒 **PASO 1:** Valida tu nodo (País) para sincronizar ofertas."
    )
    kb = [[InlineKeyboardButton("🛡️ INICIAR PROTOCOLO", url=LINK_ENTRY_DETECT)]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- TEXT HANDLER ---
async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user

    # Comandos directos
    if text in ["DASHBOARD", "PERFIL", "MINAR"]: await show_dashboard(update, context); return

    # Email Handling
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            
            # Feedback visual
            msg = await update.message.reply_text("⚙️ *Creando Billetera Híbrida...*", parse_mode="Markdown")
            await asyncio.sleep(1.5)
            try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
            except: pass
            
            await show_dashboard(update, context)
            return
        else:
            await update.message.reply_text("❌ Email inválido."); return

    # Código de Entrada
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        country = parts[2] if len(parts) >= 3 else 'GL'
        context.user_data['country'] = country
        
        await update.message.reply_text(f"🌍 **Región Conectada: {country}**\n📥 Escribe tu **Email**:", parse_mode="Markdown")
        context.user_data['waiting_for_email'] = True
        return

# --- DASHBOARD DARK MODE (Visualmente Rico) ---
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    country = context.user_data.get('country', 'GL')
    
    # Saldo Simulado (Tokens + USD)
    tokens = context.user_data.get('tokens', INITIAL_BONUS)
    usd_val = tokens * HIVE_PRICE
    
    dashboard_text = (
        f"⬛⬛⬛⬛ **HIVE DASHBOARD** ⬛⬛⬛⬛\n"
        f"🆔 `{user.id}` | 📍 `{country}`\n\n"
        f"📊 **RENDIMIENTO**\n"
        f"➤ Actividad: ▮▮▮▮▮▮▮▮▯▯ 80%\n"
        f"➤ Rango: **LARVA**\n\n"
        f"💰 **BILLETERA**\n"
        f"🪙 **{tokens} HIVE**\n"
        f"💵 **${usd_val:.2f} USD**\n\n"
        f"👇 **CENTRO DE COMANDO:**"
    )
    
    kb = [
        [InlineKeyboardButton("🧠 BUSCAR TAREA (IA AGENT)", callback_data="ai_task_search")],
        [InlineKeyboardButton("📅 BONUS DIARIO", callback_data="daily_bonus"), InlineKeyboardButton("📂 LISTA MANUAL", callback_data="manual_tasks")],
        [InlineKeyboardButton("👥 EQUIPO", callback_data="invite_friends"), InlineKeyboardButton("🏧 RETIRAR", callback_data="withdraw")],
        [InlineKeyboardButton("⚙️ PERFIL PRO", callback_data="my_profile")]
    ]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- FUNCIÓN ESTRELLA: IA TASK SEARCH ---
async def ai_task_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Animación de carga (El gancho psicológico)
    steps = [
        "🔄 Conectando a la Blockchain...",
        "🔍 Buscando ofertas High-Ticket...",
        "⚡ Optimizando para tu región...",
        "✅ **MATCH CONFIRMADO**"
    ]
    
    for step in steps:
        try:
            await query.message.edit_text(f"🧠 **HIVE AI AGENT**\n\n{step}", parse_mode="Markdown")
            await asyncio.sleep(1.0)
        except: pass # Evita error si el usuario hace click muy rápido

    country = context.user_data.get('country', 'DEFAULT')
    offer = OFFERS.get(country, OFFERS['DEFAULT'])
    
    text = (
        f"🎯 **OPORTUNIDAD DETECTADA #8492**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"La IA ha seleccionado esta misión para maximizar tu ganancia en **{country}**.\n\n"
        f"🔥 **DATOS DE LA MISIÓN:**\n"
        f"➤ Objetivo: {offer['name']}\n"
        f"➤ Pago Estimado: **$2.00 - $10.00 USD**\n"
        f"➤ Probabilidad de Éxito: **99%**\n\n"
        f"⚠️ _Tiempo límite: 15 minutos_"
    )
    kb = [
        [InlineKeyboardButton("🚀 ACEPTAR Y MINAR ($)", url=offer['link'])],
        [InlineKeyboardButton("🔙 CANCELAR", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- LISTA MANUAL (Para los que quieren ver todo) ---
async def manual_tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = context.user_data.get('country', 'DEFAULT')
    offer = OFFERS.get(country, OFFERS['DEFAULT'])
    
    text = (
        f"📂 **LISTA DE NODOS (MANUAL)**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Selecciona un nodo activo para minar manualmente:\n\n"
        f"1️⃣ **Nodo Principal ({country})**\n"
        f"   🔗 [Iniciar Protocolo]({offer['link']})\n\n"
        f"2️⃣ **Nodo Global (Backup)**\n"
        f"   🔗 [Iniciar Protocolo]({OFFERS['DEFAULT']['link']})\n"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

# --- BONUS DIARIO (Retención) ---
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Aquí podríamos chequear fecha en DB, por ahora simulamos
    new_tokens = 50
    current = context.user_data.get('tokens', INITIAL_BONUS)
    context.user_data['tokens'] = current + new_tokens
    
    await query.message.edit_text(
        f"🎁 **RECOMPENSA DIARIA RECLAMADA**\n\n"
        f"Has recibido: **+{new_tokens} HIVE**\n"
        f"Vuelve mañana para mantener tu racha 🔥.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ ENTENDIDO", callback_data="go_dashboard")]]),
        parse_mode="Markdown"
    )

# --- PERFIL PRO ---
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    email = context.user_data.get('email', 'N/A')
    text = (
        f"⚙️ **PERFIL DE AGENTE**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Nombre: {user.first_name}\n"
        f"📧 Email: `{email}`\n"
        f"🛡️ Rango: Larva (Sube de nivel completando tareas)\n"
        f"📅 Antigüedad: 1 Día"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- HANDLER CENTRAL ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # No usamos answer() aquí porque algunas funciones ya lo usan y da error doble
    data = query.data
    
    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "ai_task_search": await ai_task_search(update, context)
    elif data == "manual_tasks": await manual_tasks_menu(update, context)
    elif data == "daily_bonus": await daily_bonus(update, context)
    elif data == "my_profile": await profile_menu(update, context)
    
    elif data == "withdraw":
        await query.answer("⚠️ Acceso Denegado", show_alert=True)
        await query.message.reply_text("⚠️ **RETIRO BLOQUEADO:**\nSistema de seguridad activo. Completa 2 misiones de la IA para desbloquear la pasarela de pagos.", parse_mode="Markdown")
        
    elif data == "invite_friends":
        link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
        await query.answer()
        await query.message.reply_text(f"🔗 **ENLACE DE RECLUTAMIENTO:**\n`{link}`\n\nGana el **10%** de tu equipo.", parse_mode="Markdown")

# Handlers standard
async def help_command(u, c): await u.message.reply_text("Ayuda: /start")
async def invite_command(u, c): await u.message.reply_text("Invitar...")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset completo.")
