import logging
import re
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
HIVE_PRICE = 0.012 
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"
LINK_SMART_TASKS = f"{RENDER_URL}/go"

# --- UTILIDAD: GENERADOR DE GRÁFICAS ASCII (TIPO FOTO) ---
def generate_graph(percent):
    """Crea una barra de progreso estilo Dashboard moderno"""
    # Usamos caracteres de bloque para simular la gráfica de la foto
    total_blocks = 12
    filled = int((percent / 100) * total_blocks)
    
    # Estilo degradado visual (naranja/rojo como la foto)
    bar = "▓" * filled + "░" * (total_blocks - filled)
    return bar

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if hasattr(db, 'add_user'):
        await db.add_user(user.id, user.first_name, user.username)

    # PERFIL AUTOMÁTICO (Recuperamos su foto si es posible en futuro, por ahora nombre)
    welcome_text = (
        f"💠 **TheOneHive OS** `v2.4`\n"
        f"👤 **Usuario:** {user.first_name}\n"
        "🟢 **Estado:** Conectado\n\n"
        "Bienvenido a la Colmena. Tu terminal de ingresos está lista.\n"
        "Para acceder al Dashboard Financiero, necesitamos verificar tu nodo."
    )
    
    keyboard = [
        [InlineKeyboardButton("🛡️ INICIAR VERIFICACIÓN DE NODO", url=LINK_ENTRY_DETECT)],
        [InlineKeyboardButton("ℹ️ SOBRE NOSOTROS", callback_data="about")]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user

    # CASO: CÓDIGO DE ENTRADA
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        country = parts[2] if len(parts) >= 3 else 'GL'
        context.user_data['country'] = country
        context.user_data['waiting_for_email'] = True
        
        await update.message.reply_text(
            f"🌍 **Nodo Localizado: {country}**\n"
            "Sincronizando datos...\n\n"
            "📧 **Ingresa tu Email** para crear tu perfil de pagos:",
            parse_mode="Markdown"
        )
        return

    # CASO: EMAIL
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            
            # Al terminar registro, vamos directo al Dashboard Pro
            await show_dashboard(update, context, is_new=True)
        else:
            await update.message.reply_text("❌ Email inválido.")
        return

    # SI ESCRIBEN "PERFIL" O "DASHBOARD"
    if "PERFIL" in text.upper() or "DASHBOARD" in text.upper():
        await show_dashboard(update, context)

# --- EL DASHBOARD PRO (IGUAL A LA FOTO) ---
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new=False):
    user = update.effective_user
    country = context.user_data.get('country', 'GL')
    
    # DATOS REALES (Inicialmente en 0 para ser honestos)
    hive_balance = 100 if is_new else 100 # Bono inicial
    usd_val = hive_balance * HIVE_PRICE
    
    # Simulamos actividad semanal para la gráfica (Estética)
    graph_activity = generate_graph(75) # 75% de actividad
    graph_earning = generate_graph(30)  # 30% de la meta

    dashboard_text = (
        f"🎛 **PANEL DE CONTROL: {user.first_name.upper()}**\n"
        f"ID: `{user.id}` | 📍 Región: {country}\n"
        "──────────────────────────\n\n"
        "📊 **MÉTRICAS DE RENDIMIENTO**\n"
        f"Actividad: {graph_activity} `75%`\n"
        f"Ingresos:  {graph_earning} `30%`\n\n"
        "💰 **BILLETERA HÍBRIDA**\n"
        f"💎 **Tokens:** `{hive_balance} HIVE`\n"
        f"💵 **Valor:**  `${usd_val:.2f} USD`\n\n"
        "🚀 **MISIONES ACTIVAS**\n"
        "• Verificación de Identidad: ⏳ Pendiente\n"
        "• Vinculación de Wallet: ⏳ Pendiente\n\n"
        "👇 *Selecciona una acción en tu terminal:*"
    )
    
    kb = [
        [InlineKeyboardButton("⚡ MINAR (TAREAS)", url=LINK_SMART_TASKS)],
        [InlineKeyboardButton("👤 MI PERFIL PRO", callback_data="my_profile"), InlineKeyboardButton("🏦 RETIRAR", callback_data="withdraw")],
        [InlineKeyboardButton("📊 ESTADÍSTICAS", callback_data="stats")]
    ]
    
    if update.callback_query:
        await update.callback_query.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "my_profile":
        # AQUÍ ESTÁ LA MAGIA DEL PERFIL
        # Dejamos que el usuario sienta que lo personaliza
        user = query.from_user
        email = context.user_data.get('email', 'No verificado')
        
        profile_text = (
            f"👤 **PERFIL DE AGENTE**\n\n"
            f"**Nombre:** {user.first_name}\n"
            f"**Alias:** {user.username or 'Anónimo'}\n"
            f"**Email:** `{email}`\n"
            f"**Rango:** Larva (Nivel 1)\n\n"
            "🛠 **CONFIGURACIÓN**\n"
            "Para subir de rango y ganar más, completa tu primera tarea."
        )
        kb = [[InlineKeyboardButton("🔙 Volver al Dashboard", callback_data="back_dashboard")]]
        await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif query.data == "back_dashboard":
        await show_dashboard(update, context)
        
    elif query.data == "withdraw":
        await query.message.reply_text("⚠️ **Error de Retiro:** Necesitas acumular mínimo $10.00 USD para habilitar la pasarela.", parse_mode="Markdown")

    elif query.data == "about":
        await query.message.reply_text("Somos TheOneHive. Minería social descentralizada.", parse_mode="Markdown")

# Handlers standard
async def help_command(u, c): await u.message.reply_text("Ayuda: /start")
async def invite_command(u, c): await u.message.reply_text("Invitar...")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset completo.")
