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
ADMIN_ID = 123456789  # <--- COLOCA TU ID REAL

# --- ENLACES DE SISTEMA ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"

# --- ☢️ ARSENAL MAESTRO (19 VÍAS DE INGRESO VERIFICADAS) ---
LINKS = {
    # 🎰 CASINO & JACKPOTS
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://t.me/misterFury_bot/app?startapp=tgReLUser7012661", 
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    
    # 📈 FINTECH & TRADING (HIGH TICKET)
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    
    # ☁️ MINERÍA PASIVA
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hMP",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    
    # 📱 TRABAJO & ANUNCIOS
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'COINPAYU': "https://www.coinpayu.com/?r=TheSkywalker",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    
    # 🔄 OFERTAS CPA
    'FREECASH': "https://freecash.com/r/XYN98"
}

# --- TEXTOS: INTERFAZ "HIVE TERMINAL" (PROFESIONAL) ---
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
        # NOMBRES DE MENÚS SERIOS
        'menu_fintech': "🏦 BÓVEDA FINTECH (VIP)",
        'menu_jackpot': "💎 CRIPTO & DIVIDENDOS",
        'menu_work': "💼 TAREAS & ADS",
        'menu_passive': "☁️ MINERÍA EN NUBE",
        'menu_team': "👥 GESTIÓN DE EQUIPO",
        'menu_withdraw': "🏧 RETIRAR FONDOS",
        'menu_profile': "⚙️ CONFIGURACIÓN",
        
        # CONTENIDO DE MENÚS (CON TODOS LOS LINKS)
        'fintech_title': (
            "🏦 **BÓVEDA FINANCIERA (HIGH TICKET)**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Acceso a bonos institucionales y trading.\n\n"
            "1️⃣ **BYBIT:** [Exchange Pro + Bonos]({link_by})\n"
            "2️⃣ **PLUS500:** [Trading de CFDs]({link_plus})\n"
            "3️⃣ **NEXO:** [Interés en Cripto]({link_n})\n"
            "4️⃣ **REVOLUT:** [Banca Digital]({link_r})\n"
            "5️⃣ **WISE:** [Transferencias Globales]({link_w})\n"
            "6️⃣ **YOUHODLER:** [Préstamos & APY]({link_y})\n"
            "7️⃣ **AIRTM:** [Dólar Digital]({link_a})"
        ),
        
        'jackpot_title': (
            "💎 **CRIPTOACTIVOS & AZAR**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Generación de activos mediante probabilidad y staking.\n\n"
            "🎲 **BC.GAME:** [Casino & Lotería]({link_bc})\n"
            "🎰 **BETFURY:** [Dividendos BFG]({link_bf})\n"
            "🏦 **FREEBITCOIN:** [Interés Compuesto]({link_fb})\n"
            "🌧 **COINTIPLY:** [Pools de Bitcoin]({link_ct})"
        ),
        
        'work_title': (
            "💼 **MÓDULO DE TAREAS ACTIVAS**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Monetización directa por ejecución de tareas.\n\n"
            "📱 **PAIDWORK:** [Tareas App]({link_p})\n"
            "🎮 **GAMEHAG:** [Jugar por Gemas]({link_g})\n"
            "👁 **COINPAYU:** [Visualizar Ads]({link_c})\n"
            "⚡ **SPROUTGIGS:** [Micro-Trabajos]({link_s})\n"
            "🔄 **FREECASH:** [Ofertas CPA]({link_f})"
        ),
        
        'passive_title': (
            "☁️ **NODO DE MINERÍA PASIVA**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "Ingresos automáticos por ancho de banda.\n\n"
            "📡 **HONEYGAIN:** [Conectar Nodo]({link_h})\n"
            "📡 **PACKETSTREAM:** [Conectar Nodo]({link_ps})\n"
            "📡 **PAWNS.APP:** [Conectar Nodo]({link_pa})\n"
            "📡 **TRAFFMONETIZER:** [Conectar Nodo]({link_t})"
        ),
        
        'btn_back': "🔙 VOLVER AL PANEL",
        'withdraw_lock': "🔒 **TRANSACCIÓN DENEGADA**\n\n⚠️ **Error:** Saldo insuficiente.\n💰 **Requerido:** $10.00 USD.\n\n_El sistema desbloqueará esta función automáticamente al alcanzar la meta._"
    },
    'en': { # Configuración en inglés mantenida con el mismo estilo profesional
        'welcome': "💠 **HIVE FINANCIAL TERMINAL**\n───────────────────────\n🆔 **User:** `{name}`\n📡 **Status:** Secure\n\n👇 **SYSTEM ACCESS:**",
        'btn_start': "⚡ CONNECT NODE",
        'dashboard_header': "🎛️ **MAIN CONTROL PANEL**",
        'dashboard_body': "┌───────────────────────┐\n│ 💳 **ESTIMATED BALANCE** │\n│ `{tokens} HIVE`             │\n│ `≈ ${usd:.2f} USD`            │\n└───────────────────────┘",
        'menu_fintech': "🏦 FINTECH VAULT", 'menu_jackpot': "💎 CRYPTO & LUCK", 'menu_work': "💼 TASKS & ADS", 'menu_passive': "☁️ CLOUD MINING", 'menu_team': "👥 TEAM", 'menu_withdraw': "🏧 WITHDRAW", 'menu_profile': "⚙️ SETTINGS",
        'fintech_title': "🏦 **FINANCIAL VAULT**\n1️⃣ **BYBIT:** [Exchange]({link_by})\n2️⃣ **PLUS500:** [Trading]({link_plus})\n3️⃣ **NEXO:** [Interest]({link_n})\n4️⃣ **REVOLUT:** [Bank]({link_r})\n5️⃣ **WISE:** [Transfer]({link_w})\n6️⃣ **YOUHODLER:** [Yield]({link_y})\n7️⃣ **AIRTM:** [Wallet]({link_a})",
        'jackpot_title': "💎 **CRYPTO ASSETS**\n🎲 **BC.GAME:** [Casino]({link_bc})\n🎰 **BETFURY:** [Dividends]({link_bf})\n🏦 **FREEBITCOIN:** [Interest]({link_fb})\n🌧 **COINTIPLY:** [Pools]({link_ct})",
        'work_title': "💼 **ACTIVE TASKS**\n📱 **PAIDWORK:** [App]({link_p})\n🎮 **GAMEHAG:** [Play]({link_g})\n👁 **COINPAYU:** [Ads]({link_c})\n⚡ **SPROUTGIGS:** [Tasks]({link_s})\n🔄 **FREECASH:** [CPA]({link_f})",
        'passive_title': "☁️ **PASSIVE MINING**\n📡 **HONEYGAIN:** [Connect]({link_h})\n📡 **PACKETSTREAM:** [Connect]({link_ps})\n📡 **PAWNS:** [Connect]({link_pa})\n📡 **TRAFFMONETIZER:** [Connect]({link_t})",
        'btn_back': "🔙 BACK",
        'withdraw_lock': "🔒 **DENIED**\nRequired: $10.00 USD."
    },
    'pt': { # Portugués profesional
        'welcome': "💠 **TERMINAL FINANCEIRO HIVE**\n───────────────────────\n🆔 **Usuário:** `{name}`\n📡 **Status:** Seguro\n\n👇 **ACESSAR SISTEMA:**",
        'btn_start': "⚡ CONECTAR NÓ",
        'dashboard_header': "🎛️ **PAINEL DE CONTROLE**",
        'dashboard_body': "┌───────────────────────┐\n│ 💳 **SALDO ESTIMADO**    │\n│ `{tokens} HIVE`             │\n│ `≈ ${usd:.2f} USD`            │\n└───────────────────────┘",
        'menu_fintech': "🏦 COFRE FINTECH", 'menu_jackpot': "💎 CRIPTO & SORTE", 'menu_work': "💼 TAREFAS", 'menu_passive': "☁️ MINERAÇÃO", 'menu_team': "👥 EQUIPE", 'menu_withdraw': "🏧 SACAR", 'menu_profile': "⚙️ AJUSTES",
        'fintech_title': "🏦 **COFRE FINANCEIRO**\n1️⃣ **BYBIT:** [Exchange]({link_by})\n2️⃣ **PLUS500:** [Trading]({link_plus})\n3️⃣ **NEXO:** [Juros]({link_n})\n4️⃣ **REVOLUT:** [Banco]({link_r})\n5️⃣ **WISE:** [Conta]({link_w})\n6️⃣ **YOUHODLER:** [Yield]({link_y})\n7️⃣ **AIRTM:** [Carteira]({link_a})",
        'jackpot_title': "💎 **CRIPTO ATIVOS**\n🎲 **BC.GAME:** [Casino]({link_bc})\n🎰 **BETFURY:** [Dividendos]({link_bf})\n🏦 **FREEBITCOIN:** [Juros]({link_fb})\n🌧 **COINTIPLY:** [BTC]({link_ct})",
        'work_title': "💼 **TAREFAS ATIVAS**\n📱 **PAIDWORK:** [App]({link_p})\n🎮 **GAMEHAG:** [Jogar]({link_g})\n👁 **COINPAYU:** [Anúncios]({link_c})\n⚡ **SPROUTGIGS:** [Tarefas]({link_s})\n🔄 **FREECASH:** [CPA]({link_f})",
        'passive_title': "☁️ **MINERAÇÃO PASSIVA**\n📡 **HONEYGAIN:** [Conectar]({link_h})\n📡 **PACKETSTREAM:** [Conectar]({link_ps})\n📡 **PAWNS:** [Conectar]({link_pa})\n📡 **TRAFFMONETIZER:** [Conectar]({link_t})",
        'btn_back': "🔙 VOLTAR",
        'withdraw_lock': "🔒 **BLOQUEADO**\nMeta: $10.00 USD."
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
            # REGISTRO DE LEAD
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
        [InlineKeyboardButton(get_text(lang, 'menu_work'), callback_data="work_zone")], # TAREAS
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
    # AQUÍ ESTÁN TODOS LOS CASINOS
    txt = get_text(lang, 'jackpot_title').format(
        link_bc=LINKS['BCGAME'], 
        link_bf=LINKS['BETFURY'], 
        link_fb=LINKS['FREEBITCOIN'], 
        link_ct=LINKS['COINTIPLY']
    )
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def work_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    # AQUÍ ESTÁN TODAS LAS TAREAS
    txt = get_text(lang, 'work_title').format(
        link_p=LINKS['PAIDWORK'], 
        link_g=LINKS['GAMEHAG'], 
        link_c=LINKS['COINPAYU'], 
        link_s=LINKS['SPROUTGIGS'],
        link_f=LINKS['FREECASH']
    )
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def fintech_vault_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    # AQUÍ ESTÁN TODAS LAS FINTECH
    txt = get_text(lang, 'fintech_title').format(
        link_by=LINKS['BYBIT'],
        link_plus=LINKS['PLUS500'],
        link_n=LINKS['NEXO'], 
        link_r=LINKS['REVOLUT'], 
        link_w=LINKS['WISE'], 
        link_y=LINKS['YOUHODLER'],
        link_a=LINKS['AIRTM']
    )
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def passive_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.from_user.language_code
    # AQUÍ ESTÁN TODAS LAS MINERAS
    txt = get_text(lang, 'passive_title').format(
        link_ps=LINKS['PACKETSTREAM'], 
        link_t=LINKS['TRAFFMONETIZER'], 
        link_h=LINKS['HONEYGAIN'], 
        link_pa=LINKS['PAWNS']
    )
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"👥 **GESTIÓN DE EQUIPO**\n\n👑 **Referidos:** `{ref_count}`\n🔗 **Enlace de Nodo:**\n`{link}`" 
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
