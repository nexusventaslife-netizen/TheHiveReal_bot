import logging
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 100 
ADMIN_ID = 123456789 

# --- ENLACES DE SISTEMA ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"

# --- ☢️ ARSENAL MAESTRO (LISTA COMPLETA: 26 PLATAFORMAS) ---
LINKS = {
    # 🎰 CASINO & JACKPOTS
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://t.me/misterFury_bot/app?startapp=tgReLUser7012661", 
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    
    # 📈 FINTECH & TRADING
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    
    # ☁️ MINERÍA PASIVA (INTERNET SHARING)
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    
    # 📱 TRABAJO, TAREAS & ENCUESTAS
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
    
    # 🔄 OFERTAS CPA
    'FREECASH': "https://freecash.com/r/XYN98"
}

# --- TEXTOS: INTERFAZ "HIVE TERMINAL" (EXTENDIDA) ---
TEXTS = {
    'es': {
        'welcome': (
            "💠 **HIVE FINANCIAL TERMINAL**\n"
            "───────────────────────\n"
            "🆔 **Usuario:** `{name}`\n"
            "📡 **Conexión:** Segura (SSL)\n"
            "⏱ **Sesión:** Activa\n\n"
            "⚠️ **PROTOCOLO DE ACCESO:**\n"
            "El sistema requiere verificación humana para sincronizar la billetera de recompensas y activar el panel de control.\n\n"
            "🔻 **INICIAR ENLACE:**"
        ),
        'btn_start': "⚡ CONECTAR AL NODO",
        
        'dashboard_header': "🎛️ **PANEL DE CONTROL PRINCIPAL**",
        'dashboard_body': """
┌───────────────────────┐
│ 💳 **CAPITAL ESTIMADO**  │
│ `{tokens} HIVE`             │
│ `≈ ${usd:.2f} USD`            │
└───────────────────────┘
📊 **MÉTRICAS DEL SISTEMA**
├ 🟢 Estado: Operativo
├ 🌍 Región: {country}
└ ⚡ Nivel: Usuario Verificado
""",
        # NOMBRES DE MENÚS
        'menu_fintech': "🏦 BÓVEDA FINTECH (VIP)",
        'menu_jackpot': "💎 CRIPTO & JUEGOS",
        'menu_work': "💼 TAREAS & FREELANCE",
        'menu_passive': "☁️ MINERÍA PASIVA",
        'menu_team': "👥 GESTIÓN DE EQUIPO",
        'menu_withdraw': "🏧 RETIRAR FONDOS",
        'menu_profile': "⚙️ CONFIGURACIÓN",
        
        # DESCRIPCIONES COMPLETAS DE SECCIONES (PARA QUE NO FALTE NADA VISUALMENTE)
        'fintech_title': (
            "🏦 **BÓVEDA FINANCIERA (HIGH YIELD)**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Acceso exclusivo a bonos bancarios y trading.\n\n"
            "1. **BYBIT:** Exchange Top Tier.\n"
            "2. **REVOLUT:** Banca Digital Global.\n"
            "3. **NEXO:** Interés Compuesto en Cripto.\n"
            "4. **YOUHODLER:** Yield Farming.\n"
            "5. **PLUS500:** Trading de CFDs.\n"
            "6. **WISE:** Transferencias Internacionales.\n"
            "7. **AIRTM:** Dólar Digital sin restricciones.\n"
            "8. **FREECASH:** Ofertas CPA de alto pago.\n\n"
            "👇 **SELECCIONE PLATAFORMA:**"
        ),
        'jackpot_title': (
            "💎 **CRIPTOACTIVOS & AZAR**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Generación de activos mediante probabilidad.\n\n"
            "1. **FREEBITCOIN:** La Faucet #1 del mundo.\n"
            "2. **BETFURY:** Dividendos y Staking BFG.\n"
            "3. **BC.GAME:** Casino y Lotería Cripto.\n"
            "4. **COINTIPLY:** Chat Rain y Offerwall.\n\n"
            "👇 **SELECCIONE PROTOCOLO:**"
        ),
        'work_title': (
            "💼 **MÓDULO DE TRABAJO DIGITAL**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Monetización activa por tareas y tiempo.\n\n"
            "1. **PAIDWORK:** Tareas variadas en App.\n"
            "2. **COINPAYU:** Pago por ver anuncios (BTC).\n"
            "3. **SWAGBUCKS:** Encuestas pagadas.\n"
            "4. **TIMEBUCKS:** Tareas sociales.\n"
            "5. **SPROUTGIGS:** Micro-trabajos freelance.\n"
            "6. **GOTRANSCRIPT:** Transcripción de audio.\n"
            "7. **GAMEHAG:** Juega y gana premios.\n"
            "8. **EVERVE:** Intercambio social (Likes/Subs).\n"
            "9. **KOLOTIBABLO:** Resolución de Captchas.\n"
            "10. **TESTBIRDS:** Testing de Apps y Webs.\n\n"
            "👇 **SELECCIONE FUENTE DE INGRESOS:**"
        ),
        'passive_title': (
            "☁️ **MINERÍA PASIVA (NODOS)**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Instale las apps y gane en segundo plano.\n\n"
            "1. **HONEYGAIN:** Comparte internet.\n"
            "2. **PACKETSTREAM:** Nodo residencial.\n"
            "3. **PAWNS.APP:** IP Sharing + Encuestas.\n"
            "4. **TRAFFMONETIZER:** Tráfico monetizado.\n\n"
            "👇 **ACTIVE SUS NODOS:**"
        ),
        
        'btn_back': "🔙 VOLVER AL PANEL",
        'withdraw_lock': "🔒 **TRANSACCIÓN DENEGADA**\n\n⚠️ **Error:** Saldo insuficiente.\n💰 **Requerido:** $10.00 USD.\n\n_El sistema desbloqueará esta función automáticamente al alcanzar la meta._"
    },
    'en': { 
        'welcome': "💠 **HIVE FINANCIAL TERMINAL**\n───────────────────────\n🆔 **User:** `{name}`\n📡 **Status:** Secure\n\n👇 **SYSTEM ACCESS:**",
        'btn_start': "⚡ CONNECT NODE",
        'dashboard_header': "🎛️ **MAIN CONTROL PANEL**",
        'dashboard_body': "┌───────────────────────┐\n│ 💳 **ESTIMATED BALANCE** │\n│ `{tokens} HIVE`             │\n│ `≈ ${usd:.2f} USD`            │\n└───────────────────────┘",
        'menu_fintech': "🏦 FINTECH VAULT", 'menu_jackpot': "💎 CRYPTO & LUCK", 'menu_work': "💼 TASKS & FREELANCE", 'menu_passive': "☁️ CLOUD MINING", 'menu_team': "👥 TEAM", 'menu_withdraw': "🏧 WITHDRAW", 'menu_profile': "⚙️ SETTINGS",
        'fintech_title': "🏦 **FINANCIAL VAULT**\nSelect platform:", 'jackpot_title': "💎 **CRYPTO ASSETS**\nSelect protocol:", 'work_title': "💼 **ACTIVE TASKS**\nSelect source:", 'passive_title': "☁️ **PASSIVE MINING**\nActivate nodes:", 'btn_back': "🔙 BACK", 'withdraw_lock': "🔒 **DENIED**"
    },
    'pt': { 
        'welcome': "💠 **TERMINAL FINANCEIRO HIVE**\n───────────────────────\n🆔 **Usuário:** `{name}`\n📡 **Status:** Seguro\n\n👇 **ACESSAR SISTEMA:**",
        'btn_start': "⚡ CONECTAR NÓ",
        'dashboard_header': "🎛️ **PAINEL DE CONTROLE**",
        'dashboard_body': "┌───────────────────────┐\n│ 💳 **SALDO ESTIMADO**    │\n│ `{tokens} HIVE`             │\n│ `≈ ${usd:.2f} USD`            │\n└───────────────────────┘",
        'menu_fintech': "🏦 COFRE FINTECH", 'menu_jackpot': "💎 CRIPTO & SORTE", 'menu_work': "💼 TAREFAS & FREELANCE", 'menu_passive': "☁️ MINERAÇÃO", 'menu_team': "👥 EQUIPE", 'menu_withdraw': "🏧 SACAR", 'menu_profile': "⚙️ AJUSTES",
        'fintech_title': "🏦 **COFRE FINANCEIRO**\nSelecione:", 'jackpot_title': "💎 **CRIPTO ATIVOS**\nSelecione:", 'work_title': "💼 **TAREFAS ATIVAS**\nSelecione:", 'passive_title': "☁️ **MINERAÇÃO PASSIVA**\nAtivar:", 'btn_back': "🔙 VOLTAR", 'withdraw_lock': "🔒 **BLOQUEADO**"
    }
}

def get_text(lang_code, key):
    lang = 'en'
    if lang_code:
        if lang_code.startswith('es'): lang = 'es'
        elif lang_code.startswith('pt'): lang = 'pt'
    return TEXTS[lang].get(key, TEXTS['en'][key])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    
    args = context.args
    referrer_id = None
    if args and str(args[0]) != str(user.id):
        referrer_id = args[0]
        
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # INTERFAZ PROFESIONAL
    txt = get_text(lang, 'welcome').format(name=user.first_name)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_start'), url=LINK_ENTRY_DETECT)]]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user
    if text in ["DASHBOARD", "PERFIL", "MINAR", "/START"]: await show_dashboard(update, context); return
    
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            await show_dashboard(update, context)
            return
        else: await update.message.reply_text("⚠️ **ERROR DE FORMATO**\nPor favor ingrese un correo válido.")
    
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        context.user_data['country'] = parts[2] if len(parts) >= 3 else 'GL'
        # CAPTURA DE LEAD PROFESIONAL
        await update.message.reply_text(
            f"✅ **CREDENCIALES ACEPTADAS**\n\n📥 **REGISTRO DE USUARIO:**\nIngrese su correo electrónico para finalizar la configuración de la cuenta y habilitar los retiros.", 
            parse_mode="Markdown"
        )
        context.user_data['waiting_for_email'] = True

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    country = context.user_data.get('country', 'GL')
    
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    
    header = get_text(lang, 'dashboard_header')
    body = get_text(lang, 'dashboard_body').format(tokens=tokens, usd=usd, country=country)
    
    txt = f"{header}\n{body}"
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'menu_fintech'), callback_data="fintech_vault")], 
        [InlineKeyboardButton(get_text(lang, 'menu_jackpot'), callback_data="jackpot_zone")], 
        [InlineKeyboardButton(get_text(lang, 'menu_work'), callback_data="work_zone")], 
        [InlineKeyboardButton(get_text(lang, 'menu_passive'), callback_data="passive_income")], 
        [InlineKeyboardButton(get_text(lang, 'menu_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'menu_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'menu_profile'), callback_data="my_profile")]
    ]
    if update.callback_query: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def jackpot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    txt = get_text(lang, 'jackpot_title')
    
    kb = [
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def work_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    txt = get_text(lang, 'work_title')
    
    # 10 PLATAFORMAS DE TRABAJO (2 COLUMNAS)
    kb = [
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("🖥️ COINPAYU", url=LINKS['COINPAYU'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("⏱ TIMEBUCKS", url=LINKS['TIMEBUCKS'])],
        [InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS']), InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🔄 EVERVE", url=LINKS['EVERVE'])],
        [InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO']), InlineKeyboardButton("🐦 TESTBIRDS", url=LINKS['TESTBIRDS'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def fintech_vault_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    txt = get_text(lang, 'fintech_title')
    
    # 8 PLATAFORMAS FINTECH
    kb = [
        [InlineKeyboardButton("📈 BYBIT", url=LINKS['BYBIT']), InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT'])],
        [InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO']), InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER'])],
        [InlineKeyboardButton("📊 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def passive_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.from_user.language_code
    txt = get_text(lang, 'passive_title')
    
    # 4 PLATAFORMAS DE MINERÍA
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN'])],
        [InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS.APP", url=LINKS['PAWNS'])],
        [InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"👥 **GESTIÓN DE EQUIPO**\n\n👑 **Referidos Activos:** `{ref_count}`\n🔗 **Enlace de Nodo:**\n`{link}`" 
    kb = [[InlineKeyboardButton("📤 Compartir Enlace", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton(get_text(query.from_user.language_code, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "jackpot_zone": await jackpot_menu(update, context) 
    elif data == "work_zone": await work_menu(update, context) 
    elif data == "passive_income": await passive_menu(update, context)
    elif data == "fintech_vault": await fintech_vault_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    elif data == "my_profile":
        kb = [[InlineKeyboardButton(get_text(query.from_user.language_code, 'btn_back'), callback_data="go_dashboard")]]
        await query.message.edit_text(f"👤 **PERFIL DE USUARIO**\n\nID: `{query.from_user.id}`\nNombre: {query.from_user.first_name}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "withdraw": 
        await query.answer("🔒 Locked", show_alert=True)
        await query.message.reply_text(get_text(query.from_user.language_code, 'withdraw_lock'), parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return 
    message = " ".join(context.args)
    if message: await update.message.reply_text(f"📢 **COMUNICADO DE RED:**\n\n{message}", parse_mode="Markdown")

# Commands
async def help_command(u, c): await u.message.reply_text("Comandos: /start")
async def invite_command(u, c): await u.message.reply_text("Use el menú Equipo")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Sistema Reiniciado.")
