import logging
import re
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 100 
ADMIN_ID = 123456789  # <--- TU ID

# --- LINKS MAESTROS (Render URL para Webhook) ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"

# --- ☢️ ARSENAL GLOBAL (V7.5 RELEASE - FULL AFFILIATE) ---
LINKS = {
    # 💎 JACKPOT & DIVIDENDOS
    'BETFURY': "https://t.me/misterFury_bot/app?startapp=tgReLUser7012661", 
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    
    # ☁️ MINERÍA PASIVA
    'PACKETSTREAM': "https://packetstream.io/?psr=7hMP",
    'HONEYGAIN': "Https://join.honeygain.com/ALEJOE9F32",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    
    # 📱 TRABAJO & JUEGOS
    'COINPAYU': "Https://www.coinpayu.com/?r=TheSkywalker", 
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    
    # ⚡ MICRO-SOCIAL
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'EVERVE': "https://everve.net/ref/1950045/",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    
    # 🏦 FINTECH (HIGH TICKET)
    'REVOLUT': "Https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "Https://wise.com/invite/ahpc/josealejandrop73",
    'NEXO': "Https://nexo.com/ref/rbkekqnarx?src=android-link",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend?rut=h8PD43j-9dcCVPPfHr_f2zLxqmzKRUTScleOD8oAZSE-pAHDARwjOkXTHl-g1mYquw2T7jX52xizXxIfl-M1yj60UHCryGcRnaSDPtNmD341",
    'AIRTM': "Https://app.airtm.com/ivt/jos3vkujiyj",
    'FREECASH': "https://freecash.com/r/XYN98",
    
    # 📈 EXCHANGE
    'BYBIT': "Https://www.bybit.com/invite?ref=BBJWAX4"
}

# --- TEXTOS MULTILENGUAJE ---
TEXTS = {
    'es': {
        'welcome': "🐝 **THE ONE HIVE** `v7.5`\n👤 Agente: `{name}`\n\n📜 **TÉRMINOS:** Al continuar, aceptas recibir notificaciones comerciales, ofertas de terceros y actualizaciones del sistema en tu email y Telegram.\n\n💎 **PROTOCOLO ACTIVO:**\nAds, CPA y Minería Pasiva.\n\n👇 Inicia validación:",
        'btn_start': "🛡️ ACEPTAR Y CONECTAR",
        'dashboard_title': "⬛⬛⬛ **PANEL DE MANDO** ⬛⬛⬛",
        'metrics': "📊 **TU COLMENA**",
        'wallet': "💰 **TESORERÍA**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'rank': "🎖 Rango: **{rank}**",
        'balance_usd': "💵 **${usd:.2f} USD** (Estimado)",
        'menu_fintech': "🏦 BÓVEDA $50+ (VIP)",
        'menu_jackpot': "💎 JACKPOT DIARIO",
        'menu_work': "📱 TRABAJO & ADS",
        'menu_passive': "☁️ MINERÍA AUTO (x4)",
        'menu_team': "👥 MI EQUIPO",
        'menu_withdraw': "🏧 RETIRAR",
        'menu_profile': "⚙️ PERFIL",
        'fintech_title': "🏦 **BÓVEDA FINANCIERA (VIP)**\n━━━━━━━━━━\nLas ofertas que más pagan. Regístrate y valida identidad.\n\n1️⃣ **Revolut:** [Bono Tarjeta]({link_r})\n2️⃣ **Nexo:** [Interés Crypto]({link_n})\n3️⃣ **YouHodler:** [Yield Farming]({link_y})\n4️⃣ **Plus500:** [Trading CFD]({link_plus})\n5️⃣ **Wise:** [Cuenta Global]({link_w})\n6️⃣ **Bybit:** [Exchange TOP]({link_by})",
        'jackpot_title': "💎 **ZONA DE SUERTE & CRIPTO**\n━━━━━━━━━━\n1️⃣ **FreeBitco.in**\n🔗 [Activar Interés 4.08%]({link_fb})\n\n2️⃣ **BetFury**\n🔗 [Minar Dividendos BFG]({link_bf})\n\n3️⃣ **Cointiply**\n🔗 [Faucet BTC & Chat]({link_ct})",
        'work_title': "📱 **TRABAJO DIGITAL & ADS**\n━━━━━━━━━━\n1️⃣ **Paidwork:** [App Móvil]({link_p})\n2️⃣ **Gamehag:** [Jugar y Ganar]({link_g})\n3️⃣ **CoinPayU:** [Ver Anuncios]({link_c})\n4️⃣ **SproutGigs:** [Micro-Tareas]({link_s})",
        'passive_title': "☁️ **MINERÍA SILENCIOSA (x4)**\n━━━━━━━━━━\nInstala las 4 apps y gana en automático:\n\n1️⃣ **PacketStream:** [Instalar]({link_ps})\n2️⃣ **Traffmonetizer:** [Instalar]({link_t})\n3️⃣ **Honeygain:** [Instalar]({link_h})\n4️⃣ **Pawns.app:** [Instalar]({link_pa})",
        'btn_back': "🔙 VOLVER",
        'withdraw_lock': "⚠️ **BLOQUEADO**\nAcumula $10.00 USD para desbloquear retiros."
    },
    'en': {
        'welcome': "🐝 **THE ONE HIVE** `v7.5`\n👤 Agent: `{name}`\n\n📜 **TERMS:** By continuing, you agree to receive commercial notifications and third-party offers.\n\n👇 Start validation:",
        'btn_start': "🛡️ ACCEPT & CONNECT",
        'dashboard_title': "⬛⬛⬛ **COMMAND CENTER** ⬛⬛⬛",
        'metrics': "📊 **YOUR HIVE**",
        'wallet': "💰 **TREASURY**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'rank': "🎖 Rank: **{rank}**",
        'balance_usd': "💵 **${usd:.2f} USD** (Est)",
        'menu_fintech': "🏦 VAULT $50+ (VIP)",
        'menu_jackpot': "💎 DAILY JACKPOT",
        'menu_work': "📱 WORK & ADS",
        'menu_passive': "☁️ AUTO MINING (x4)",
        'menu_team': "👥 MY TEAM",
        'menu_withdraw': "🏧 WITHDRAW",
        'menu_profile': "⚙️ PROFILE",
        'fintech_title': "🏦 **FINANCIAL VAULT (VIP)**\n━━━━━━━━━━\n1️⃣ **Revolut:** [Bonus]({link_r})\n2️⃣ **Nexo:** [Bonus]({link_n})\n3️⃣ **YouHodler:** [Yield]({link_y})\n4️⃣ **Plus500:** [Trading]({link_plus})\n5️⃣ **Wise:** [Account]({link_w})\n6️⃣ **Bybit:** [Exchange]({link_by})",
        'jackpot_title': "💎 **LUCK & CRYPTO ZONE**\n━━━━━━━━━━\n1️⃣ **FreeBitco.in**\n🔗 [Enable 4.08% APY]({link_fb})\n\n2️⃣ **BetFury**\n🔗 [Mine BFG]({link_bf})\n\n3️⃣ **Cointiply**\n🔗 [Rain Pool]({link_ct})",
        'work_title': "📱 **DIGITAL WORK**\n━━━━━━━━━━\n1️⃣ **Paidwork:** [App]({link_p})\n2️⃣ **Gamehag:** [Play]({link_g})\n3️⃣ **CoinPayU:** [Ads]({link_c})\n4️⃣ **SproutGigs:** [Tasks]({link_s})",
        'passive_title': "☁️ **SILENT MINING**\n━━━━━━━━━━\n1️⃣ **PacketStream:** [Install]({link_ps})\n2️⃣ **Traffmonetizer:** [Install]({link_t})\n3️⃣ **Honeygain:** [Install]({link_h})\n4️⃣ **Pawns.app:** [Install]({link_pa})",
        'btn_back': "🔙 BACK",
        'withdraw_lock': "⚠️ **LOCKED**\nReach $10.00 USD."
    },
    'pt': {
        'welcome': "🐝 **THE ONE HIVE** `v7.5`\n👤 Agente: `{name}`\n\n👇 Iniciar validação:",
        'btn_start': "🛡️ CONECTAR NÓ",
        'dashboard_title': "⬛⬛⬛ **PAINEL DE COMANDO** ⬛⬛⬛",
        'metrics': "📊 **SUA COLMEIA**",
        'wallet': "💰 **TESOURARIA**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'rank': "🎖 Rank: **{rank}**",
        'balance_usd': "💵 **${usd:.2f} USD** (Est)",
        'menu_fintech': "🏦 COFRE $50+ (VIP)",
        'menu_jackpot': "💎 JACKPOT DIÁRIO",
        'menu_work': "📱 TRABALHO & ADS",
        'menu_passive': "☁️ MINERAÇÃO AUTO (x4)",
        'menu_team': "👥 MINHA EQUIPE",
        'menu_withdraw': "🏧 SACAR",
        'menu_profile': "⚙️ PERFIL",
        'fintech_title': "🏦 **COFRE FINANCEIRO**\n━━━━━━━━━━\n1️⃣ **Revolut:** [Bônus]({link_r})\n2️⃣ **Nexo:** [Bônus]({link_n})\n3️⃣ **YouHodler:** [Yield]({link_y})\n4️⃣ **Plus500:** [Trading]({link_plus})\n5️⃣ **Wise:** [Conta]({link_w})\n6️⃣ **Bybit:** [Bônus]({link_by})",
        'jackpot_title': "💎 **SORTE & CRIPTO**\n━━━━━━━━━━\n1️⃣ **FreeBitco.in**\n🔗 [Juros]({link_fb})\n\n2️⃣ **BetFury**\n🔗 [Minera BFG]({link_bf})\n\n3️⃣ **Cointiply**\n🔗 [Chuva BTC]({link_ct})",
        'work_title': "📱 **TRABALHO DIGITAL**\n━━━━━━━━━━\n1️⃣ **Paidwork:** [App]({link_p})\n2️⃣ **Gamehag:** [Jogar]({link_g})\n3️⃣ **CoinPayU:** [Anúncios]({link_c})\n4️⃣ **SproutGigs:** [Tarefas]({link_s})",
        'passive_title': "☁️ **MINERAÇÃO SILENCIOSA**\n━━━━━━━━━━\n1️⃣ **PacketStream:** [Instalar]({link_ps})\n2️⃣ **Traffmonetizer:** [Instalar]({link_t})\n3️⃣ **Honeygain:** [Instalar]({link_h})\n4️⃣ **Pawns.app:** [Instalar]({link_pa})",
        'btn_back': "🔙 VOLTAR",
        'withdraw_lock': "⚠️ **BLOQUEADO**\nAcumule $10.00 USD."
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
        else: await update.message.reply_text("❌ Error. Email required.")
    
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        context.user_data['country'] = parts[2] if len(parts) >= 3 else 'GL'
        await update.message.reply_text(f"🌍 **Conexión Segura**\n\n📥 **PASO FINAL:** Ingresa tu correo electrónico para activar tu cuenta y recibir novedades.", parse_mode="Markdown")
        context.user_data['waiting_for_email'] = True

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    country = context.user_data.get('country', 'GL')
    
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    rank = user_data.get('rank', 'Larva 🐛') 
    usd = tokens * HIVE_PRICE
    
    txt = (
        f"{get_text(lang, 'dashboard_title')}\n"
        f"🆔 `{user.id}` | 📍 `{country}`\n"
        f"{get_text(lang, 'rank').format(rank=rank)}\n\n"
        f"{get_text(lang, 'metrics')}\n"
        f"➤ ▮▮▮▮▮▮▮▮▯▯ 80%\n\n"
        f"{get_text(lang, 'wallet')}\n"
        f"{get_text(lang, 'balance_hive').format(tokens=tokens)}\n"
        f"{get_text(lang, 'balance_usd').format(usd=usd)}\n"
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'menu_fintech'), callback_data="fintech_vault")], 
        [InlineKeyboardButton(get_text(lang, 'menu_jackpot'), callback_data="jackpot_zone")], 
        [InlineKeyboardButton(get_text(lang, 'menu_work'), callback_data="work_zone"), InlineKeyboardButton(get_text(lang, 'menu_passive'), callback_data="passive_income")], 
        [InlineKeyboardButton(get_text(lang, 'menu_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'menu_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'menu_profile'), callback_data="my_profile")]
    ]
    if update.callback_query: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def jackpot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    txt = get_text(lang, 'jackpot_title').format(link_fb=LINKS['FREEBITCOIN'], link_bf=LINKS['BETFURY'], link_ct=LINKS['COINTIPLY'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def work_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    txt = get_text(lang, 'work_title').format(link_p=LINKS['PAIDWORK'], link_g=LINKS['GAMEHAG'], link_c=LINKS['COINPAYU'], link_s=LINKS['SPROUTGIGS'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def fintech_vault_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    txt = get_text(lang, 'fintech_title').format(link_n=LINKS['NEXO'], link_y=LINKS['YOUHODLER'], link_r=LINKS['REVOLUT'], link_plus=LINKS['PLUS500'], link_w=LINKS['WISE'], link_by=LINKS['BYBIT'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def passive_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.from_user.language_code
    txt = get_text(lang, 'passive_title').format(link_ps=LINKS['PACKETSTREAM'], link_t=LINKS['TRAFFMONETIZER'], link_h=LINKS['HONEYGAIN'], link_pa=LINKS['PAWNS'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"👥 **EQUIPO**\n\n👑 Referidos: {ref_count}\n🔗 `{link}`" 
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
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
        kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
        await query.message.edit_text(f"👤 {query.from_user.first_name}", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "withdraw": 
        await query.answer("⚠️ Locked", show_alert=True)
        await query.message.reply_text(get_text(query.from_user.language_code, 'withdraw_lock'), parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return 
    message = " ".join(context.args)
    if message: await update.message.reply_text(f"📢 **BROADCAST:**\n\n{message}", parse_mode="Markdown")

# Commands
async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Invite...")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset done.")
