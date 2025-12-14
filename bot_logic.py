import logging
import re
import asyncio
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 500  
ADMIN_ID = 123456789 

# TU WEBAPP (Render)
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# --- IMAGEN DE BIENVENIDA (LA QUE ME ACABAS DE PASAR) ---
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ARSENAL MAESTRO DE ENLACES (TODOS INCLUIDOS - NO FALTA NINGUNO) ---
LINKS = {
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'COINPAYU': "https://www.coinpayu.com/?r=TheSkywalker",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    'TIMEBUCKS': "https://timebucks.com/?refID=227501472",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'FREECASH': "https://freecash.com/r/XYN98"
}

LEGAL_TEXT = "📜 Protocolos Hive: Datos protegidos SHA-256."

# --- TEXTOS ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE DETECTADO**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**.\n\n"
            "⚠️ **VERIFICACIÓN DE SEGURIDAD:**\n"
            "Para acceder a la Colmena, necesitamos verificar que eres humano.\n\n"
            "👇 **PASO 1:**\n"
            "Copia tu **CÓDIGO DE SEGURIDAD** y envíalo aquí abajo."
        ),
        'btn_verify_webapp': "🔐 GENERAR CÓDIGO",
        
        'ask_email': (
            "✅ **CÓDIGO CORRECTO**\n"
            "───────────────────────\n"
            "Acceso autorizado.\n\n"
            "📧 **PASO 2 (FINAL):**\n"
            "Escribe tu **CORREO ELECTRÓNICO** para vincular tu billetera:"
        ),
        
        'ask_bonus': (
            "✅ **CUENTA VINCULADA**\n"
            "───────────────────────\n"
            "🎁 **¡TIENES UN BONO PENDIENTE!**\n"
            "Antes de entrar, activa tu cuenta y reclama **$6.00 USD** pulsando aquí:"
        ),
        'btn_claim_bonus': "💰 RECLAMAR BONO AHORA",

        'dashboard_body': """
🎮 **CENTRO DE COMANDO HIVE**
──────────────────────────
👤 **Piloto:** {name}
🛡️ **Rango:** {rank}
✅ **Estado:** ACTIVO

💰 **SALDO:** ${usd:.2f}
💠 **TOKENS:** {tokens} HVT
──────────────────────────
""",
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Auto)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_help': "📜 Ayuda", 'btn_team': "📡 Equipo", 'btn_profile': "⚙️ Perfil", 'btn_withdraw': "🏧 Retirar",
        't1_title': "🟢 **ZONA 1**", 't2_title': "🟡 **ZONA 2**", 't3_title': "🔴 **ZONA 3**",
        'btn_back': "🔙 VOLVER", 'withdraw_lock': "🔒 **BLOQUEADO** ($10 min)", 'help_text': "Guía..."
    },
    'en': { 
        'welcome_caption': "Verify Human...", 'btn_verify_webapp': "Get Code", 
        'ask_email': "Enter Email:", 'ask_bonus': "Claim Bonus...", 'btn_claim_bonus': "Claim", 
        'dashboard_body': "Dashboard...", 
        'btn_t1': "LVL 1", 'btn_t2': "LVL 2", 'btn_t3': "LVL 3",
        'btn_help': "Help", 'btn_team': "Team", 'btn_profile': "Profile", 'btn_withdraw': "Withdraw",
        't1_title': "LVL 1", 't2_title': "LVL 2", 't3_title': "LVL 3",
        'btn_back': "BACK", 'withdraw_lock': "LOCKED", 'help_text': "Guide..."
    }
}

def get_text(lang_code, key):
    lang = 'en'
    if lang_code and lang_code.startswith('es'): lang = 'es'
    return TEXTS[lang].get(key, TEXTS['en'].get(key, key))

def generate_captcha():
    num = random.randint(100, 999)
    return f"HIVE-{num}"

# --- LÓGICA PRINCIPAL ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """INICIO ROBUSTO: ENVÍA FOTO Y TEXTO POR SEPARADO"""
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Limpiamos teclado anterior
    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # CHEQUEO DE ESTADO
    user_data = await db.get_user(user.id)
    
    # 1. Usuario Full (Email + Bono) -> Dashboard
    if user_data and user_data.get('email') and context.user_data.get('bonus_claimed'):
        await show_dashboard(update, context)
        return

    # 2. INICIO DE CERO (CAPTCHA)
    captcha_code = generate_captcha()
    context.user_data['required_captcha'] = captcha_code
    context.user_data['waiting_for_captcha'] = True
    context.user_data['waiting_for_email'] = False
    
    # --- ENVÍO SEPARADO PARA QUE NO FALLE ---
    
    # INTENTO 1: Enviar FOTO sola
    try:
        await update.message.reply_photo(photo=IMG_BEEBY)
    except Exception as e:
        logger.error(f"No se pudo cargar la imagen: {e}")
        # Si falla la imagen, seguimos con el texto
    
    # INTENTO 2: Enviar TEXTO con el CÓDIGO
    base_txt = get_text(lang, 'welcome_caption').format(name=user.first_name)
    code_txt = f"\n\n🔑 **TU CÓDIGO DE ACCESO:** `{captcha_code}`\n(Cópialo y envíalo)"
    
    full_text = base_txt + code_txt
    
    await update.message.reply_text(full_text, parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    user = update.effective_user
    lang = user.language_code

    # COMANDOS GLOBALES
    if text.upper() == "/RESET" or text.upper() == "/FORCE_RESET": 
        context.user_data.clear()
        if text.upper() == "/FORCE_RESET" and hasattr(db, 'update_email'): 
            await db.update_email(user.id, None)
        await update.message.reply_text("🔄 Sistema Reiniciado. Escribe /start")
        return

    # --- PASO 1: VERIFICAR CAPTCHA ---
    if context.user_data.get('waiting_for_captcha'):
        required = context.user_data.get('required_captcha')
        
        # Validamos (ignorando mayúsculas/minúsculas)
        if text.upper() == required:
            context.user_data['waiting_for_captcha'] = False
            context.user_data['waiting_for_email'] = True
            
            await update.message.reply_text(get_text(lang, 'ask_email'), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text(f"❌ **CÓDIGO INCORRECTO.**\nDebes enviar exactamente: `{required}`", parse_mode="Markdown")
            return

    # --- PASO 2: CAPTURA DE EMAIL ---
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            
            # --- PASO 3: OFRECER BONO ---
            await offer_bonus_step(update, context)
            return
        else:
            await update.message.reply_text("⚠️ Email inválido. Intenta de nuevo:")
            return

    # NAVEGACIÓN
    if text.upper() in ["DASHBOARD", "PERFIL", "/START"]: 
        user_db = await db.get_user(user.id)
        if user_db and user_db.get('email'):
            await show_dashboard(update, context)
        else:
            await start(update, context)
        return

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    
    txt = get_text(lang, 'ask_bonus')
    
    kb = [[InlineKeyboardButton(
        get_text(lang, 'btn_claim_bonus'), 
        url=LINKS['COINPAYU'] 
    )]]
    
    kb.append([InlineKeyboardButton("✅ LISTO (ENTRAR)", callback_data="bonus_done")])
    
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    
    rank = "🐛 LARVA"
    if ref_count >= 5: rank = "🐝 OBRERA"
    if ref_count >= 20: rank = "👑 REINA"

    body = get_text(lang, 'dashboard_body').format(name=user.first_name, rank=rank, usd=usd, tokens=tokens)
    
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

# --- MENÚS ---
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
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't3_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_guide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(get_text(lang, 'help_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); ref_count = len(user_data.get('referrals', [])) if user_data else 0; link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"📡 **RED**\n👑 Nodos: `{ref_count}`\n🔗 `{link}`" 
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data
    
    if data == "bonus_done":
        context.user_data['bonus_claimed'] = True
        await show_dashboard(update, context)
        return

    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "tier_1": await tier1_menu(update, context)
    elif data == "tier_2": await tier2_menu(update, context)
    elif data == "tier_3": await tier3_menu(update, context)
    elif data == "help_guide": await help_guide_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    elif data == "legal_terms": 
        kb = [[InlineKeyboardButton("🔙", callback_data="my_profile")]]
        await query.message.edit_text(LEGAL_TEXT, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "my_profile":
        kb = [[InlineKeyboardButton("⚖️ Legal", callback_data="legal_terms"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
        await query.message.edit_text(f"👤 **PERFIL**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "withdraw": await query.answer("🔒 $10 MIN", show_alert=True)

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Use menu")
async def broadcast_command(u, c): pass
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK")
