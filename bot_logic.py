import logging
import re
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN MAESTRA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 500
ADMIN_ID = 123456789 

# TU WEBAPP (RENDER)
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# IMAGEN DE BIENVENIDA
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-1.jpg"

# --- ☢️ ARSENAL DE ENLACES (COMPLETO - NO FALTA NADA) ---
LINKS = {
    # TIER 1: CLICK & FARM
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINPAYU': "https://www.coinpayu.com/?r=TheSkywalker",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'EVERVE': "https://everve.net/ref/1950045/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    
    # TIER 2: AUTOMATIZACIÓN
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

    # TIER 3: FINANZAS
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

# --- TEXTOS Y IDIOMAS (LÓGICA LARGA RESTAURADA) ---
TEXTS = {
    'es': {
        'welcome': (
            "🧬 **SISTEMA HIVE DETECTADO**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**, tu IA de gestión.\n\n"
            "⚠️ **ACCIÓN REQUERIDA:**\n"
            "El sistema ha detectado una nueva conexión. Para proteger la economía de la Colmena, necesitamos validar tu humanidad y registrar tu credencial.\n\n"
            "👇 **PASO 1: PULSA EL BOTÓN PARA ACTIVAR EL NODO**"
        ),
        'btn_verify_webapp': "⚡ ACTIVAR NODO (Verificar)",
        'email_request': (
            "✅ **VERIFICACIÓN EXITOSA**\n"
            "───────────────────────\n"
            "Tu humanidad ha sido confirmada.\n\n"
            "📧 **PASO 2: REGISTRO DE CREDENCIAL**\n"
            "Por favor, **escribe tu correo electrónico** para vincularlo a tu cuenta de Hive y asegurar tus fondos.\n\n"
            "_(Ejemplo: usuario@gmail.com)_"
        ),
        'dashboard_body': """
🎮 **HIVE COMMAND CENTER** 💠
──────────────────────────
👤 **Operador:** {name}
🛡️ **Rango:** {rank}
✅ **Estado:** CONECTADO

💰 **ALMACÉN DE MIEL (USD):**
**${usd:.2f}** 

💠 **POLEN (HIVE TOKENS):**
**{tokens} HVT** 

📊 **PROGRESO:**
`[█████░░░░░] 50%`
──────────────────────────
⚔️ **SELECCIONA TU MISIÓN:**
""",
        'btn_t1': "🟢 ZONA 1: Recolección (Easy)",
        'btn_t2': "🟡 ZONA 2: Automáticos (Bots)",
        'btn_t3': "🔴 ZONA 3: Contratos (High $)",
        'btn_help': "📜 Ayuda",
        'btn_team': "📡 Equipo",
        'btn_profile': "⚙️ Perfil",
        'btn_withdraw': "🏧 Retirar",
        't1_title': "🟢 **ZONA 1: FARMING**\nRecursos rápidos:",
        't2_title': "🟡 **ZONA 2: AUTOMATIZACIÓN**\nIngresos pasivos:",
        't3_title': "🔴 **ZONA 3: HIGH TICKET**\nGrandes bonos:",
        'btn_back': "🔙 VOLVER",
        'withdraw_lock': "🔒 **BLOQUEADO**\nNecesitas $10.00 USD para retirar."
    },
    'en': { 
        'welcome': "Connect Node...", 
        'btn_verify_webapp': "Connect", 
        'email_request': "✅ Verified. Please enter your email:",
        'dashboard_body': "Dashboard...",
        'btn_back': "Back" 
    }
}

def get_text(lang_code, key):
    lang = 'en'
    if lang_code and lang_code.startswith('es'): lang = 'es'
    return TEXTS[lang].get(key, TEXTS['en'][key])

# --- LÓGICA PRINCIPAL DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """INICIO: Verifica estado y muestra botón WebApp si no está verificado."""
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = None
    if args and str(args[0]) != str(user.id): referrer_id = args[0]
        
    # Registro inicial en DB
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Limpieza de mensajes viejos
    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # 1. ¿YA TIENE EMAIL? -> DASHBOARD DIRECTO
    # (Si verificamos esto, evitamos pedir el mail cada vez que pone start)
    user_data = await db.get_user(user.id)
    if user_data and user_data.get('email'):
        context.user_data['verified'] = True
        await show_dashboard(update, context)
        return

    # 2. ¿YA ESTÁ VERIFICADO PERO FALTA EL EMAIL?
    if context.user_data.get('verified') and not user_data.get('email'):
        await ask_for_email(update, context)
        return

    # 3. SI NO ESTÁ VERIFICADO -> BOTÓN WEBAPP
    txt = get_text(lang, 'welcome').format(name=user.first_name)
    kb = [[InlineKeyboardButton(
        get_text(lang, 'btn_verify_webapp'), 
        web_app=WebAppInfo(url=RENDER_URL)
    )]]
    
    try:
        await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CENTRO DE CONTROL DE MENSAJES"""
    
    # --- A. RESPUESTA DE LA WEBAPP (VERIFICACIÓN) ---
    if update.message.web_app_data:
        data = update.message.web_app_data.data
        if data == "VERIFIED_OK":
            context.user_data['verified'] = True
            # AQUÍ ESTABA EL ERROR: ANTES IBA AL DASHBOARD DIRECTO.
            # AHORA VA AL PASO DEL EMAIL.
            await ask_for_email(update, context)
            return

    # --- B. MANEJO DE TEXTO DEL USUARIO ---
    text = update.message.text.strip()
    user = update.effective_user
    
    # COMANDO DE RESET
    if text.upper() == "/RESET":
        context.user_data.clear()
        await update.message.reply_text("🔄 Sistema Reiniciado. Usa /start")
        return

    # --- C. CAPTURA DE EMAIL (EL PASO QUE FALTABA) ---
    if context.user_data.get('waiting_for_email'):
        # Validación simple de email
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            # Guardamos el email
            if hasattr(db, 'update_email'): 
                await db.update_email(user.id, text)
            
            context.user_data['waiting_for_email'] = False # Ya no esperamos email
            
            await update.message.reply_text("✅ **EMAIL REGISTRADO CORRECTAMENTE.**\n\nAccediendo al sistema...", parse_mode="Markdown")
            await asyncio.sleep(1)
            await show_dashboard(update, context)
            return
        else:
            await update.message.reply_text("⚠️ **ERROR:** El formato del correo no es válido.\nInténtalo de nuevo (ejemplo: juan@gmail.com).")
            return

    # NAVEGACIÓN NORMAL
    if text.upper() in ["DASHBOARD", "PERFIL", "/START"]: 
        await show_dashboard(update, context)
        return

async def ask_for_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FUNCIÓN DEDICADA PARA PEDIR EL EMAIL"""
    user = update.effective_user
    lang = user.language_code
    
    # Activamos el estado de espera
    context.user_data['waiting_for_email'] = True
    
    txt = get_text(lang, 'email_request')
    await update.message.reply_text(txt, parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PANEL PRINCIPAL"""
    user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    
    rank = "🐛 LARVA"
    if ref_count >= 5: rank = "🐝 OBRERA"
    if ref_count >= 20: rank = "👑 REINA"
    
    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, tokens=tokens, usd=usd, rank=rank
    )
    
    # MENÚ COMPLETO RESTAURADO
    kb = [
        [InlineKeyboardButton("🎁 BONO EXTRA (COINPAYU)", url=LINKS['COINPAYU'])],
        [InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")],
        [InlineKeyboardButton(get_text(lang, 'btn_help'), callback_data="help_guide")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MENÚS DE LOS 3 TIERS (TODOS LOS LINKS) ---
# He verificado que estén todos los enlaces originales.

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📺 COINPAYU", url=LINKS['COINPAYU']), InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY']), InlineKeyboardButton("👍 EVERVE", url=LINKS['EVERVE'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't1_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("⏱ TIMEBUCKS", url=LINKS['TIMEBUCKS'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("🐦 TESTBIRDS", url=LINKS['TESTBIRDS']), InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't2_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📈 BYBIT", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER'])],
        [InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("📊 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't3_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_guide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text("Guía...", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); ref_count = len(user_data.get('referrals', [])) if user_data else 0; link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"📡 **RED**\n👑 Nodos: `{ref_count}`\n🔗 `{link}`" 
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data
    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "tier_1": await tier1_menu(update, context)
    elif data == "tier_2": await tier2_menu(update, context)
    elif data == "tier_3": await tier3_menu(update, context)
    elif data == "help_guide": await help_guide_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    elif data == "my_profile":
        kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
        await query.message.edit_text(f"👤 **PERFIL**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "withdraw": await query.answer("🔒 $10 MIN", show_alert=True)

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Use menu")
async def broadcast_command(u, c): pass
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK")
