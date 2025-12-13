import logging
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 100 
ADMIN_ID = 123456789 

# --- ENLACES DE SISTEMA ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"

# IMAGEN DE BIENVENIDA (BEEBY)
IMG_BEEBY = "https://cdn-icons-png.flaticon.com/512/826/826963.png"

# --- ☢️ ARSENAL MAESTRO DE ENLACES (ORGANIZADO POR TIERS) ---
LINKS = {
    # --- TIER 1: TAREAS RÁPIDAS (CLICKS & JUEGOS) ---
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINPAYU': "https://www.coinpayu.com/?r=TheSkywalker",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'EVERVE': "https://everve.net/ref/1950045/",
    'BETFURY': "https://t.me/misterFury_bot/app?startapp=tgReLUser7012661",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    
    # --- TIER 2: TAREAS MEDIAS (APPS & ENCUESTAS) ---
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'TIMEBUCKS': "https://timebucks.com/?refID=227501472",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAWNS': "https://pawns.app/?r=18399810",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",

    # --- TIER 3: TAREAS PREMIUM (HIGH TICKET & FINTECH) ---
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'FREECASH': "https://freecash.com/r/XYN98",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend"
}

# --- TEXTOS LEGALES ---
LEGAL_TEXT = """
📜 **TÉRMINOS DE SERVICIO Y POLÍTICA DE PRIVACIDAD**
─────────────────────────────────
**1. Aceptación del Servicio**
Al utilizar THEONE HIVE, aceptas estos términos.

**2. Sistema de Niveles (Tiers)**
El bot organiza tareas de terceros en niveles de dificultad. No garantizamos el pago de dichas plataformas externas.

**3. Privacidad**
Tus datos (ID Telegram, Email) son privados y solo para uso interno.

_Última actualización: Diciembre 2025_
"""

# --- TEXTOS: INTERFAZ & NARRATIVA ---
TEXTS = {
    'es': {
        'welcome': (
            "🐝 **¡BIENVENIDO A LA COLMENA!**\n"
            "───────────────────────\n"
            "👋 Hola `{name}`, soy **Beeby**, tu asistente de operaciones.\n\n"
            "💠 **SISTEMA PROFESIONAL:**\n"
            "Hemos organizado las tareas en **3 NIVELES (TIERS)** para maximizar tu eficiencia.\n\n"
            "📊 **ESTADO:**\n"
            "• Rango: 🐛 Larva (Nivel 0)\n"
            "• Saldo: $0.00 USD\n\n"
            "👇 **INICIA TU NODO:**"
        ),
        'btn_start': "⚡ ACCEDER AL SISTEMA",
        
        # DASHBOARD ORGANIZADO (Aquí está la clave)
        'dashboard_body': """
🐝 **PANEL DE CONTROL PROFESIONAL**
──────────────────────────
👤 **Operador:** {name}
🏅 **Rango:** 🐝 {rank} ({refs} refs)

💰 **CAPITAL (MIEL):**
**${usd:.2f} USD**

🧪 **PUNTOS DE NIVEL (NÉCTAR):**
**{tokens} Pts**

🎯 **RUTA DE TRABAJO:**
Selecciona un nivel según tu experiencia:
──────────────────────────
""",
        # BOTONES DEL DASHBOARD (AHORA SÍ POR TIERS)
        'btn_t1': "🟢 TIER 1: Principiante (Clicks Rápidos)",
        'btn_t2': "🟡 TIER 2: Intermedio (Apps & Minería)",
        'btn_t3': "🔴 TIER 3: Avanzado (High Ticket $)",
        
        'btn_help': "❓ GUÍA DE ASISTENCIA",
        'btn_team': "👥 Mi Equipo",
        'btn_profile': "⚙️ Perfil",
        'btn_withdraw': "🏧 Retirar",
        
        # MENSAJE DE AYUDA (ASISTENTE)
        'help_text': (
            "🤖 **ASISTENTE INTELIGENTE - GUÍA DE NIVELES**\n"
            "───────────────────────\n\n"
            "🟢 **TIER 1 (PRINCIPIANTE):**\n"
            "Ideal para empezar hoy mismo. No requiere verificación de identidad.\n"
            "• *Incluye: Ver anuncios, Faucets, Juegos.* \n\n"
            "🟡 **TIER 2 (INTERMEDIO):**\n"
            "Generación de ingresos pasivos y tareas de tiempo medio.\n"
            "• *Incluye: Apps de minería (instalar y olvidar), Encuestas.*\n\n"
            "🔴 **TIER 3 (AVANZADO):**\n"
            "Las ofertas mejor pagadas del mercado. Requieren registro real.\n"
            "• *Incluye: Bonos bancarios, Trading, Herramientas Pro.*"
        ),

        # TÍTULOS DE LOS MENÚS
        't1_title': "🟢 **ZONA TIER 1**\nAcciones rápidas para generar capital inicial:",
        't2_title': "🟡 **ZONA TIER 2**\nIngresos recurrentes y aplicaciones:",
        't3_title': "🔴 **ZONA TIER 3 (PREMIUM)**\nOfertas de alto valor ($10 - $50 USD):",
        
        'btn_back': "🔙 VOLVER AL PANEL",
        'btn_legal': "📜 Términos Legales",
        'withdraw_lock': "🔒 **BLOQUEADO**\nSaldo insuficiente ($10.00 USD)."
    },
    'en': { 
        'welcome': "🐝 **WELCOME!**\nI'm Beeby.", 'btn_start': "⚡ ENTER",
        'dashboard_body': "🐝 **PRO DASHBOARD**\nUser: {name}\n💰 Balance: ${usd:.2f}",
        'btn_t1': "🟢 TIER 1: Easy", 'btn_t2': "🟡 TIER 2: Medium", 'btn_t3': "🔴 TIER 3: Pro",
        'btn_help': "❓ HELP", 'help_text': "Guide...", 'btn_team': "👥 Team", 'btn_profile': "⚙️ Profile", 'btn_withdraw': "🏧 Withdraw",
        't1_title': "🟢 T1", 't2_title': "🟡 T2", 't3_title': "🔴 T3",
        'btn_back': "🔙 BACK", 'btn_legal': "📜 Terms", 'withdraw_lock': "🔒 DENIED"
    },
    'pt': { 
        'welcome': "🐝 **BEM-VINDO!**\nSou Beeby.", 'btn_start': "⚡ ENTRAR",
        'dashboard_body': "🐝 **PAINEL PRO**\nUsuário: {name}\n💰 Saldo: ${usd:.2f}",
        'btn_t1': "🟢 TIER 1: Fácil", 'btn_t2': "🟡 TIER 2: Médio", 'btn_t3': "🔴 TIER 3: Pro",
        'btn_help': "❓ AJUDA", 'help_text': "Guia...", 'btn_team': "👥 Equipe", 'btn_profile': "⚙️ Perfil", 'btn_withdraw': "🏧 Sacar",
        't1_title': "🟢 T1", 't2_title': "🟡 T2", 't3_title': "🔴 T3",
        'btn_back': "🔙 VOLTAR", 'btn_legal': "📜 Termos", 'withdraw_lock': "🔒 BLOQUEADO"
    }
}

def get_text(lang_code, key):
    lang = 'en'
    if lang_code:
        if lang_code.startswith('es'): lang = 'es'
        elif lang_code.startswith('pt'): lang = 'pt'
    return TEXTS[lang].get(key, TEXTS['en'][key])

# --- FUNCIONES PRINCIPALES ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    
    args = context.args
    referrer_id = None
    if args and str(args[0]) != str(user.id): referrer_id = args[0]
        
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # BIENVENIDA CON FOTO (BEEBY)
    txt = get_text(lang, 'welcome').format(name=user.first_name)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_start'), url=LINK_ENTRY_DETECT)]]
    
    try:
        await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user
    
    if text in ["DASHBOARD", "PERFIL", "/START"]: 
        await show_dashboard(update, context)
        return
    
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            await show_dashboard(update, context)
            return
        else: await update.message.reply_text("⚠️ Email inválido.")
    
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        context.user_data['country'] = parts[2] if len(parts) >= 3 else 'GL'
        await update.message.reply_text("✅ OK. Email:", parse_mode="Markdown")
        context.user_data['waiting_for_email'] = True

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PANEL PRINCIPAL - AQUÍ SE MUESTRAN LOS TIERS"""
    user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    rank = "Larva"
    if ref_count >= 5: rank = "Obrera"
    if ref_count >= 20: rank = "Reina"
    
    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, 
        id=user.id, 
        tokens=tokens, 
        usd=usd, 
        rank=rank, 
        refs=ref_count
    )
    
    # BOTONERA ESTRUCTURADA POR NIVELES
    kb = [
        # BLOQUE 1: LOS NIVELES (TIERS)
        [InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")],
        
        # BLOQUE 2: ASISTENCIA
        [InlineKeyboardButton(get_text(lang, 'btn_help'), callback_data="help_guide")],
        
        # BLOQUE 3: GESTIÓN
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MENÚS DE DETALLE (TIERS) ---

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("📺 COINPAYU", url=LINKS['COINPAYU']), InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY']), InlineKeyboardButton("👍 EVERVE", url=LINKS['EVERVE'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't1_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("⏱ TIMEBUCKS", url=LINKS['TIMEBUCKS'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't2_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("📈 BYBIT", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER'])],
        [InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("📊 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't3_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_guide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(get_text(lang, 'help_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"👥 **COLMENA**\n👑 Referidos: `{ref_count}`\n🔗 `{link}`" 
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def legal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="my_profile")]]
    await query.message.edit_text(LEGAL_TEXT, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "tier_1": await tier1_menu(update, context)
    elif data == "tier_2": await tier2_menu(update, context)
    elif data == "tier_3": await tier3_menu(update, context)
    elif data == "help_guide": await help_guide_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    elif data == "legal_terms": await legal_menu(update, context)
    elif data == "my_profile":
        kb = [
            [InlineKeyboardButton(get_text(query.from_user.language_code, 'btn_legal'), callback_data="legal_terms")],
            [InlineKeyboardButton(get_text(query.from_user.language_code, 'btn_back'), callback_data="go_dashboard")]
        ]
        await query.message.edit_text(f"👤 **PERFIL**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "withdraw": 
        await query.answer("🔒 Locked", show_alert=True)
        await query.message.reply_text(get_text(query.from_user.language_code, 'withdraw_lock'), parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return 
    message = " ".join(context.args)
    if message: await update.message.reply_text(f"📢 **AVISO:**\n{message}", parse_mode="Markdown")

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Use el menú Equipo")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Sistema Reiniciado.")
