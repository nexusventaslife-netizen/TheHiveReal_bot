import logging
import re
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE ECONOMÍA Y ENLACES ---
HIVE_PRICE = 0.012  # Un poco más alto para que se vea mejor
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"
LINK_SMART_TASKS = f"{RENDER_URL}/go"
LINK_BYBIT = "https://www.bybit.com/invite?ref=TU_CODIGO"
LINK_BCGAME = "https://bc.game/i-TU_CODIGO-n/"

# --- SIMULACIÓN DE DATOS EN TIEMPO REAL (PSICOLOGÍA) ---
def get_live_stats():
    """Genera números creíbles para el gancho inicial."""
    users_active = random.randint(2800, 3100)
    earned_today = random.randint(45000, 48000)
    return users_active, earned_today

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if hasattr(db, 'add_user'):
        await db.add_user(user.id, user.first_name, user.username)

    active_now, cash_today = get_live_stats()
    
    # TEXTO DE ALTO IMPACTO (Griddled Style)
    welcome_text = (
        f"🚀 **BIENVENIDO A TheOneHive**\n"
        "La única app donde REALMENTE facturas desde tu teléfono.\n\n"
        f"💰 **Usuarios ganaron HOY:** `${cash_today:,.2f} USD`\n"
        f"👥 **Personas activas AHORA:** `{active_now}`\n\n"
        "No pierdas tiempo. El dinero que no ganas tú, se lo lleva otro.\n"
        "¿Qué vas a hacer?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 EMPEZAR A GANAR YA", callback_data="step_verify_country")],
        [InlineKeyboardButton("❓ ¿CÓMO FUNCIONA?", callback_data="how_it_works")]
    ]
    
    # Si tienes una imagen de bienvenida, usa reply_photo. Por ahora reply_text.
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    # --- PANTALLA "CÓMO FUNCIONA" ---
    if query.data == "how_it_works":
        text = (
            "📹 **SISTEMA TheOneHive EN 30 SEGUNDOS**\n\n"
            "1. **Entras.**\n"
            "2. **Verificas tu país** (Para darte ofertas en tu moneda).\n"
            "3. **Haces tareas simples** (Apps, Encuestas, Juegos).\n"
            "4. **Cobras** en Cripto o Dólares.\n\n"
            "Simple. Sin vueltas."
        )
        kb = [[InlineKeyboardButton("🚀 ENTENDIDO, QUIERO GANAR", callback_data="step_verify_country")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    # --- PANTALLA 2: VERIFICACIÓN RÁPIDA (PAÍS) ---
    elif query.data == "step_verify_country":
        text = (
            "⚡ **SETUP RÁPIDO (Paso 1/3)**\n\n"
            "Para asignarte las tareas que más pagan, necesitamos validar tu conexión.\n\n"
            "1️⃣ **¿Desde qué país nos escribes?**"
        )
        # Aquí usamos tu link de detección automática
        kb = [
            [InlineKeyboardButton("🌍 DETECTAR AUTOMÁTICAMENTE (Recomendado)", url=LINK_ENTRY_DETECT)],
            [InlineKeyboardButton("📍 ELEGIR MANUALMENTE", callback_data="manual_country_select")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    # --- SELECCIÓN MANUAL (POR SI FALLA EL LINK O PREFIEREN NO SALIR) ---
    elif query.data == "manual_country_select":
        kb = [
            [InlineKeyboardButton("🇺🇸 Estados Unidos", callback_data="set_country_US"), InlineKeyboardButton("🇪🇸 España", callback_data="set_country_ES")],
            [InlineKeyboardButton("🇲🇽 México", callback_data="set_country_MX"), InlineKeyboardButton("🇦🇷 Argentina", callback_data="set_country_AR")],
            [InlineKeyboardButton("🇨🇴 Colombia", callback_data="set_country_CO"), InlineKeyboardButton("🌎 Otro", callback_data="set_country_GL")]
        ]
        await query.edit_message_text("📍 Selecciona tu región:", reply_markup=InlineKeyboardMarkup(kb))

    # --- GUARDAR PAÍS Y PEDIR EMAIL ---
    elif query.data.startswith("set_country_"):
        country = query.data.split("_")[2]
        context.user_data['country'] = country
        
        # Guardar en contexto que esperamos email
        context.user_data['waiting_for_email'] = True
        
        text = (
            f"✅ Región **{country}** configurada.\n\n"
            "⚡ **SETUP RÁPIDO (Paso 2/3)**\n\n"
            "2️⃣ **Escribe tu Email** aquí abajo 👇\n"
            "*(Lo usamos para enviarte los comprobantes de pago)*"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    # --- PANTALLA 3: PERMISOS (GAMIFICADOS) ---
    elif query.data == "accept_permissions":
        # Simulación de aceptar permisos
        text = (
            "🎉 **¡LISTO, CONFIGURACIÓN COMPLETADA!**\n\n"
            "🎁 **REGALO DE BIENVENIDA:**\n"
            "• `100 Tokens HIVE` (Acreditados)\n"
            "• **Tu primera tarea vale +50%** ($0.15 -> $0.22)\n\n"
            "📊 **TU POTENCIAL HOY:**\n"
            "┌───────────────────────────┐\n"
            "│ 10 min  → $2.50           │\n"
            "│ 30 min  → $8.50           │\n"
            "│ 2 horas → $40.00 ⭐ RECOM. │\n"
            "└───────────────────────────┘"
        )
        kb = [[InlineKeyboardButton("🚀 VER MI PRIMERA TAREA", callback_data="go_dashboard")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    # --- EL DASHBOARD PRINCIPAL (HOME) ---
    elif query.data == "go_dashboard":
        await show_dashboard(update, context)

    # --- PANTALLA DE TAREAS ---
    elif query.data == "view_tasks":
        await tasks_menu(update, context)
        
    elif query.data == "invite_friends":
         link = f"https://t.me/{context.bot.username}?start={user.id}"
         await query.message.reply_text(f"🔗 Tu link de reclutamiento:\n`{link}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user

    # CASO CÓDIGO DEL LINK (El usuario viene del detector)
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        country = parts[2] if len(parts) >= 3 else 'GL'
        context.user_data['country'] = country
        context.user_data['waiting_for_email'] = True
        
        await update.message.reply_text(
            f"🌍 **Conexión Segura: {country}**\n\n"
            "⚡ **SETUP RÁPIDO (Paso 2/3)**\n"
            "2️⃣ **Escribe tu Email** para activar la cuenta:",
            parse_mode="Markdown"
        )
        return

    # CASO EMAIL
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            
            # PANTALLA 3: PERMISOS (Paso 3/3)
            msg = (
                "⚡ **SETUP RÁPIDO (Paso 3/3)**\n\n"
                "3️⃣ **Permisos de Alto Rendimiento**\n"
                "✅ Enviarme ofertas exclusivas (High Ticket)\n"
                "✅ Recordatorios de tareas nuevas\n"
                "✅ Notificarme cuando pueda retirar\n\n"
                "💡 *Recibirás +50 tokens EXTRA por aceptar*"
            )
            kb = [[InlineKeyboardButton("✅ ACEPTO TODO (Recomendado)", callback_data="accept_permissions")]]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Email inválido.")
        return

    # MENÚ INFERIOR (SI ESCRIBEN COMANDOS)
    if "TAREAS" in text.upper():
        await tasks_menu(update, context)

# --- FUNCIÓN: MOSTRAR DASHBOARD ---
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    country = context.user_data.get('country', 'GL')
    
    # Datos simulados para enganchar
    earned_today = 12.50
    goal_daily = 20.00
    
    dashboard_text = (
        f"╔════════════════════════════╗\n"
        f"║  **TheOneHive**            🔔 [3] 👤  ║\n"
        f"╠════════════════════════════╣\n"
        f"  👋 Hola {user.first_name}           {country}\n"
        f"  Nivel 3 ⭐⭐⭐             [75% -> L4]\n\n"
        f"  🔥 **TU RACHA: 7 DÍAS**\n"
        f"  [✅][✅][✅][✅][✅][✅][✅]\n"
        f"  *¡No la pierdas! +5% bonus activo.*\n\n"
        f"  💰 **HOY GANASTE:**       `${earned_today} USD`\n"
        f"  ━━━━━━━━━━━━━━ 62% de tu meta\n"
        f"  🎯 **Meta:** ${goal_daily}  (Faltan: $7.50)\n\n"
        f"  🎁 **BONUS DISPONIBLE:**\n"
        f"  ⚡ Hora Feliz (23 min): Tareas pagan +25%\n"
        f"╚════════════════════════════╝"
    )
    
    kb = [
        [InlineKeyboardButton("💼 VER TAREAS (8 nuevas)", callback_data="view_tasks")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats"), InlineKeyboardButton("💸 Retirar", callback_data="withdraw")]
    ]
    
    # Manejo inteligente de mensajes (Editar o Nuevo)
    if update.callback_query:
        await update.callback_query.edit_message_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- FUNCIÓN: LISTA DE TAREAS ---
async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_country = context.user_data.get('country', 'DEFAULT')
    
    # Textos de alto CTR
    text = (
        "💼 **TAREAS DISPONIBLES**\n"
        "🔥 **TAREAS CALIENTES (Expiran pronto)**\n\n"
        "1️⃣ **[HORA FELIZ] Verificación Rápida**\n"
        "   💰 **$2.50**  ⏱ 2 min  🔥 Quedan 14 cupos\n"
        "   [▶️ Empezar ahora]\n\n"
        "2️⃣ **Instalar App + Probar**\n"
        "   💰 **$0.85**  ⏱ 3 min  🏆 Top Semanal\n"
        "   [▶️ Empezar]\n\n"
        "💎 **TAREAS PREMIUM (Tu plan: FREE)**\n"
        "   🔒 Research de mercado ($5.00) -> [Desbloquear]"
    )
    
    # Aquí es donde va TU link de Monetag/SmartLink
    # Le ponemos un nombre atractivo al botón
    kb = [[InlineKeyboardButton("🚀 EMPEZAR TAREA RÁPIDA ($2.50)", url=LINK_SMART_TASKS)]]
    
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# Comandos y Handlers Standard
async def help_command(u, c): await u.message.reply_text("Usa /start")
async def invite_command(u, c): await u.message.reply_text("Invitar...")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset completo.")
