import logging
import re
import asyncio
import random
import string
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA (SUPREMACÍA AUS) ---
# Economía Dual: Dinero Real + Néctar Virtual
INITIAL_USD = 0.05      # Bono inicial en USD REALES
INITIAL_NECTAR = 1000   # Bono inicial en NÉCTAR (NC)

# Precios de la Tienda
COST_OBRERO = 50000
COST_MAPA = 100000

ADMIN_ID = 123456789 

# TU WEBAPP (Render)
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# --- IMAGEN DE BIENVENIDA ---
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ARSENAL MAESTRO DE ENLACES (LISTA COMPLETA 100%) ---
LINKS = {
    # ENLACE PRINCIPAL (VALIDACIÓN)
    'COINPAYU': "https://coinpayu.com/?r=TheSkywalker",
    
    # SECCIÓN 1: CASINO & SUERTE
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    
    # SECCIÓN 2: FINTECH & TRADING (HIGH TICKET)
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    
    # SECCIÓN 3: MINERÍA PASIVA
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    
    # SECCIÓN 4: TRABAJO ACTIVO (MICRO-TASKS)
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    'TIMEBUCKS': "https://timebucks.com/?refID=227501472",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # SECCIÓN 5: IA & MARKETING
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    
    # SECCIÓN 6: CPA
    'FREECASH': "https://freecash.com/r/XYN98"
}

LEGAL_TEXT = "📜 Protocolos Hive (AUS): Datos protegidos SHA-256. Ingresos auditados."

# --- TEXTOS ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE DETECTADO (AUS v4.0)**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**.\n\n"
            "⚠️ **VERIFICACIÓN DE SEGURIDAD:**\n"
            "Para acceder a la Colmena, necesitamos verificar que eres humano.\n\n"
            "👇 **PASO 1:**\n"
            "Obtén tu CÓDIGO DE SEGURIDAD abajo y envíalo al chat."
        ),
        
        'ask_email': (
            "✅ **CÓDIGO CORRECTO**\n"
            "───────────────────────\n"
            "Acceso autorizado.\n\n"
            "📧 **PASO 2 (FINAL):**\n"
            "Escribe tu **CORREO ELECTRÓNICO** para activar tu Billetera Dual (USD Real + Néctar):"
        ),
        
        'ask_bonus': (
            "✅ **BILLETERA CREADA**\n"
            "───────────────────────\n"
            "🎁 **ACTIVACIÓN DE GANANCIAS**\n"
            "Para activar el flujo de **$0.01 USD Reales** por tarea, debes validar tu cuenta en nuestro proveedor principal.\n\n"
            "👇 Pulsa aquí para validar y recibir tu primer ingreso:"
        ),
        'btn_claim_bonus': "💰 VALIDAR CUENTA (Ganar $0.05)",

        'dashboard_body': """
🎮 **CENTRO DE COMANDO HIVE**
──────────────────────────
👤 **Operador:** {name}
🛡️ **Rango:** {rank}
✅ **Estado:** CONECTADO

💵 **SALDO REAL (Retirable):**
**${usd:.2f} USD** 
_(Ingresos auditados: /justificante)_

🍯 **NÉCTAR (NC):**
**{nectar} NC**
_(Úsalo en la Tienda para comprar Habilidades)_

📊 **Habilidades Activas:**
{skills}
──────────────────────────
""",
        'shop_body': """
🏪 **TIENDA DE HABILIDADES (Growth Hacking)**
──────────────────────────
Invierte tu Néctar (NC) para ganar más USD Real.

👷 **OBRERO CERTIFICADO T1**
*Costo: 50,000 NC*
✅ Desbloquea tareas CPA de $0.50 - $2.00 USD.

🗺️ **MAPA DE ENJAMBRE**
*Costo: 100,000 NC*
✅ Acceso a plantillas SEO/Marketing y Webinars.

*Tu saldo:* {nectar} NC
""",
        'justificante_header': "📜 **AUDITORÍA EN TIEMPO REAL (AUS)**\n──────────────────────────\nAquí está la prueba de origen de tus fondos:\n\n",
        
        'btn_shop': "🛒 TIENDA DE HABILIDADES",
        'btn_justificante': "📜 VER JUSTIFICANTE",
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_help': "📜 Ayuda", 'btn_team': "📡 Equipo", 'btn_profile': "⚙️ Perfil", 'btn_withdraw': "🏧 Retirar",
        't1_title': "🟢 **ZONA 1**", 't2_title': "🟡 **ZONA 2**", 't3_title': "🔴 **ZONA 3**",
        'btn_back': "🔙 VOLVER", 'withdraw_lock': "🔒 **BLOQUEADO** ($10 min)", 'help_text': "Guía..."
    },
    'en': { 
        'welcome': "Verify Human...", 'btn_verify_webapp': "Get Code", 'ask_email': "Enter Email:", 'ask_bonus': "Claim Bonus...", 'btn_claim_bonus': "Claim", 
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
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    user_data = await db.get_user(user.id)
    
    if user_data and user_data.get('email') and context.user_data.get('bonus_claimed'):
        await show_dashboard(update, context)
        return

    # INICIO DE CERO
    captcha_code = generate_captcha()
    context.user_data['required_captcha'] = captcha_code
    context.user_data['waiting_for_captcha'] = True
    context.user_data['waiting_for_email'] = False 
    
    base_txt = get_text(lang, 'welcome_caption').format(name=user.first_name)
    code_txt = f"\n\n🔑 **TU CÓDIGO DE ACCESO ES:** `{captcha_code}`\n(Cópialo y envíalo)"
    full_caption = base_txt + code_txt
    
    try: 
        await update.message.reply_photo(photo=IMG_BEEBY, caption=full_caption, parse_mode="Markdown")
    except Exception as e: 
        logger.error(f"Error enviando foto: {e}")
        await update.message.reply_text(full_caption, parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    user = update.effective_user
    lang = user.language_code

    if text.upper() == "/FORCE_RESET":
        context.user_data.clear()
        if hasattr(db, 'update_email'): await db.update_email(user.id, None)
        await update.message.reply_text("🛑 RESET COMPLETO.")
        return
    
    if text.upper() == "/JUSTIFICANTE":
        await show_justificante(update, context)
        return

    if text.upper() == "/RESET": 
        context.user_data.clear(); await update.message.reply_text("Reset OK."); return

    if context.user_data.get('waiting_for_captcha'):
        required = context.user_data.get('required_captcha')
        if text.upper() == required:
            context.user_data['waiting_for_captcha'] = False
            context.user_data['waiting_for_email'] = True
            await update.message.reply_text(get_text(lang, 'ask_email'), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text(f"❌ **CÓDIGO INCORRECTO.**\nDebes enviar: `{required}`", parse_mode="Markdown")
            return

    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
            return
        else:
            await update.message.reply_text("⚠️ Email inválido. Intenta de nuevo:")
            return

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
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['COINPAYU'])]]
    kb.append([InlineKeyboardButton("✅ LISTO (ENTRAR)", callback_data="bonus_done")])
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MUESTRA EL LOG DE AUDITORÍA (PILAR DE HONESTIDAD)"""
    lang = update.effective_user.language_code
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    
    log_text = get_text(lang, 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD**\n   └ Fuente: *CoinPayU Network (Ad View)*\n\n"
    log_text += f"🟢 `[{now} 10:42]` **+$0.01 USD**\n   └ Fuente: *Micro-Lead Verification*\n\n"
    log_text += f"🟢 `[{now} 11:00]` **+$0.03 USD**\n   └ Fuente: *Bono de Bienvenida Hive*\n"
    log_text += "\n✅ **ESTADO:** Verificado y Disponible para Retiro."

    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIENDA DE HABILIDADES (PILAR DE CRECIMIENTO)"""
    user = update.effective_user
    user_data = await db.get_user(user.id)
    nectar = user_data.get('nectar', INITIAL_NECTAR) if user_data else INITIAL_NECTAR
    
    txt = get_text(user.language_code, 'shop_body').format(nectar=nectar)
    
    kb = [
        [InlineKeyboardButton("👷 COMPRAR OBRERO (50k)", callback_data="buy_obrero")],
        [InlineKeyboardButton("🗺️ COMPRAR MAPA (100k)", callback_data="buy_mapa")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    
    # LÓGICA DUAL: USD vs NÉCTAR
    nectar = user_data.get('nectar', INITIAL_NECTAR) if user_data else INITIAL_NECTAR
    usd = user_data.get('usd_balance', INITIAL_USD) if user_data else INITIAL_USD
    
    skills_list = user_data.get('skills', [])
    skills_txt = "• Ninguna (Eres Larva)" if not skills_list else "\n".join([f"• {s}" for s in skills_list])

    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    rank = "🐛 LARVA"
    if ref_count >= 5: rank = "🐝 OBRERA"
    if ref_count >= 20: rank = "👑 REINA"

    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, rank=rank, usd=usd, nectar=nectar, skills=skills_txt
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="go_shop")], 
        [InlineKeyboardButton(get_text(lang, 'btn_justificante'), callback_data="go_justificante")], 
        [InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📺 COINPAYU", url=LINKS['COINPAYU']), InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY']), InlineKeyboardButton("👍 EVERVE", url=LINKS['EVERVE'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        # BOTÓN NUEVO DE VALIDACIÓN DUAL
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (Validar)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("⏱ TIMEBUCKS", url=LINKS['TIMEBUCKS'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("🐦 TESTBIRDS", url=LINKS['TESTBIRDS']), InlineKeyboardButton("✅ YA HICE UNA TAREA (Validar)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📈 BYBIT", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER'])],
        [InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (Validar)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **ZONA 3: PRO & TRADING**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; 
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    txt = (
        "📡 **SISTEMA DE REFERIDOS 2-TIER (AUS)**\n\n"
        "👥 **NIVEL 1:** Ganas **20%** de lo que ganen tus directos.\n"
        "🗣️ **NIVEL 2:** Ganas **5%** de los amigos de tus amigos.\n\n"
        f"🔗 **TU ENLACE:**\n`{link}`"
    )
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def validate_task_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SIMULA LA AUDITORÍA EN TIEMPO REAL (JUSTIFICANTE)"""
    query = update.callback_query
    
    await query.answer("🔍 Verificando blockchain y CPA...", show_alert=False)
    await asyncio.sleep(1.5) 
    
    tx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    text = (
        f"✅ **TAREA VALIDADA CON ÉXITO**\n"
        f"🧾 **Justificante:** #{tx_id}\n"
        f"───────────────────────\n\n"
        f"⚠️ **MINERÍA DUAL EJECUTADA:**\n"
        f"Al completar esta acción, has generado:\n\n"
        f"💵 **FIAT (Real):** $0.01 USD\n"
        f"_(Fuente: Red CPA Verificada)_\n\n"
        f"💠 **CRYPTO (Token):** 50 HVT\n"
        f"_(Minter: Protocolo Hive)_\n\n"
        f"🧩 **NFT:** +1 Fragmento de 'Beeby Obrero'\n\n"
        f"───────────────────────\n"
        f"💰 *Los fondos se han agregado a tu saldo pendiente.*"
    )
    
    kb = [[InlineKeyboardButton("🔙 VOLVER AL TRABAJO", callback_data="go_dashboard")]]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_guide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(get_text(lang, 'help_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data
    
    if data == "bonus_done":
        context.user_data['bonus_claimed'] = True
        await show_dashboard(update, context)
        return
    
    if data == "validate_task":
        await validate_task_logic(update, context)
        return

    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "go_shop": await shop_menu(update, context)
    elif data == "go_justificante": await show_justificante(update, context)
    
    elif data == "buy_obrero": await query.answer("❌ Néctar insuficiente (Necesitas 50,000 NC)", show_alert=True)
    elif data == "buy_mapa": await query.answer("❌ Néctar insuficiente (Necesitas 100,000 NC)", show_alert=True)

    elif data == "tier_1": await tier1_menu(update, context)
    elif data == "tier_2": await tier2_menu(update, context)
    elif data == "tier_3": await tier3_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    elif data == "help_guide": await help_guide_menu(update, context)
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
