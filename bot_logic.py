import logging
import re
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE ECONOMÍA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 100 

# --- TUS ENLACES DE RENDER ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"

# --- ☢️ ARSENAL DE MONETIZACIÓN (LINKS REALES) ---
LINKS = {
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381"
}

# --- ESTRATEGIA GEOGRÁFICA ---
OFFERS = {
    # TIER 1 (USA/EU): Testbirds y Freecash reinan aquí
    'US': {'link': LINKS['FREECASH'], 'name': '🇺🇸 VIP Task: Freecash ($5-10)'},
    'GB': {'link': LINKS['TESTBIRDS'], 'name': '🇬🇧 QA Tester Job (High Pay)'},
    'DE': {'link': LINKS['TESTBIRDS'], 'name': '🇩🇪 Software Tester (20€/Test)'},

    # TIER 2 (LATAM): Mix Balanceado
    'MX': {'link': LINKS['HONEYGAIN'], 'name': '🇲🇽 Ingreso Pasivo (Honeygain)'},
    'AR': {'link': LINKS['AIRTM'], 'name': '🇦🇷 Bono Bienvenida Airtm'},
    'CO': {'link': LINKS['PAWNS'], 'name': '🇨🇴 Gana por Compartir Internet'},
    'ES': {'link': LINKS['TESTBIRDS'], 'name': '🇪🇸 Probador de Apps (Pago en Euros)'},
    'BR': {'link': LINKS['HONEYGAIN'], 'name': '🇧🇷 Renda Passiva Brasil'},
    'VE': {'link': LINKS['AIRTM'], 'name': '🇻🇪 Libertad Financiera (Airtm)'},

    # DEFAULT / GLOBAL
    'DEFAULT': {
        'link': LINKS['TRAFFMONETIZER'], 
        'name': '🌍 GLOBAL PASSIVE INCOME (Install & Earn)'
    } 
}

# --- TEXTOS MULTILENGUAJE ---
TEXTS = {
    'es': {
        'welcome': "🐝 **THE ONE HIVE** `v4.0 Pro`\n👤 Agente: `{name}`\n\nBienvenido. IA detectó idioma: **Español**.\n\n🔒 **PASO 1:** Conectar Nodo.",
        'btn_start': "🛡️ INICIAR SISTEMA",
        'dashboard_title': "⬛⬛⬛ **PANEL DE MANDO** ⬛⬛⬛",
        'metrics': "📊 **RENDIMIENTO**",
        'wallet': "💰 **TESORERÍA**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'balance_usd': "💵 **${usd:.2f} USD** (Pendiente)",
        'menu_ai': "🧠 IA: BUSCAR TAREA",
        'menu_passive': "💤 MINERÍA AUTO", 
        'menu_test': "👨‍💻 TESTER PRO (20€)", # NUEVO BOTÓN
        'menu_team': "👥 EQUIPO",
        'menu_withdraw': "🏧 RETIRAR",
        'menu_profile': "⚙️ PERFIL",
        'ai_searching': ["🔄 Escaneando...", "🌍 Buscando mejor pago...", "✅ **¡TAREA ENCONTRADA!**"],
        'ai_found': "🎯 **MISIÓN ACTIVA #99**\n━━━━━━━━━━\nEl sistema eligió esto para tu país:\n\n🔥 **{offer_name}**\n🛡️ **Tipo:** Tarea de Alto Valor.\n💰 **Pago:** USD/Cripto.",
        'passive_found': "💤 **MODO MINERÍA AUTOMÁTICA**\n━━━━━━━━━━\nInstala y gana dinero sin hacer nada:\n\n🚀 **{offer_name}**\n(Honeygain/Pawns/Traffmonetizer)",
        'test_found': "👨‍💻 **TRABAJO DE QA TESTER**\n━━━━━━━━━━\nConviértete en probador de software certificado.\n\n✅ **Pagan hasta 20€ por error encontrado.**\n✅ Trabajo serio y profesional.\n✅ No requiere experiencia previa.\n\n🔗 [REGISTRO TESTBIRDS]({link})",
        'btn_accept': "🚀 ACEPTAR TRABAJO",
        'btn_back': "🔙 VOLVER",
        'withdraw_error': "⚠️ **RETIRO BLOQUEADO:**\nDebes completar 1 Misión para habilitar pagos.",
        'invite_text': "🔗 **LINK DE EQUIPO:**\n`{link}`\n\nGana 10% de tus referidos.",
        'profile': "👤 **PERFIL**\nNombre: {name}\nEmail: `{email}`\nIdioma: Español"
    },
    'en': {
        'welcome': "🐝 **THE ONE HIVE** `v4.0 Pro`\n👤 Agent: `{name}`\n\nWelcome. AI detected: **English**.\n\n🔒 **STEP 1:** Connect Node.",
        'btn_start': "🛡️ START SYSTEM",
        'dashboard_title': "⬛⬛⬛ **COMMAND CENTER** ⬛⬛⬛",
        'metrics': "📊 **PERFORMANCE**",
        'wallet': "💰 **TREASURY**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'balance_usd': "💵 **${usd:.2f} USD** (Pending)",
        'menu_ai': "🧠 AI: FIND TASK",
        'menu_passive': "💤 AUTO MINING",
        'menu_test': "👨‍💻 PRO TESTER (€20)",
        'menu_team': "👥 TEAM",
        'menu_withdraw': "🏧 WITHDRAW",
        'menu_profile': "⚙️ PROFILE",
        'ai_searching': ["🔄 Scanning...", "🌍 Finding best pay...", "✅ **TASK FOUND!**"],
        'ai_found': "🎯 **ACTIVE MISSION #99**\n━━━━━━━━━━\nSystem picked this for you:\n\n🔥 **{offer_name}**\n🛡️ **Type:** High Value Task.\n💰 **Pay:** USD/Crypto.",
        'passive_found': "💤 **AUTO MINING MODE**\n━━━━━━━━━━\nInstall and earn passive income:\n\n🚀 **{offer_name}**\n(Honeygain/Pawns/Traffmonetizer)",
        'test_found': "👨‍💻 **QA TESTER JOB**\n━━━━━━━━━━\nBecome a certified software tester.\n\n✅ **Pay up to €20 per bug found.**\n✅ Professional work.\n✅ No experience needed.\n\n🔗 [REGISTER TESTBIRDS]({link})",
        'btn_accept': "🚀 ACCEPT WORK",
        'btn_back': "🔙 BACK",
        'withdraw_error': "⚠️ **WITHDRAWAL LOCKED:**\nComplete 1 Mission to enable payments.",
        'invite_text': "🔗 **TEAM LINK:**\n`{link}`\n\nEarn 10% from referrals.",
        'profile': "👤 **PROFILE**\nName: {name}\nEmail: `{email}`\nLanguage: English"
    },
    'pt': {
        'welcome': "🐝 **THE ONE HIVE** `v4.0 Pro`\n👤 Agente: `{name}`\n\nBem-vindo. IA detectou: **Português**.\n\n🔒 **PASSO 1:** Conectar Nodo.",
        'btn_start': "🛡️ INICIAR SISTEMA",
        'dashboard_title': "⬛⬛⬛ **PAINEL DE COMANDO** ⬛⬛⬛",
        'metrics': "📊 **DESEMPENHO**",
        'wallet': "💰 **TESOURARIA**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'balance_usd': "💵 **${usd:.2f} USD** (Pendente)",
        'menu_ai': "🧠 IA: BUSCAR TAREFA",
        'menu_passive': "💤 MINERAÇÃO AUTO",
        'menu_test': "👨‍💻 TESTER PRO (20€)",
        'menu_team': "👥 EQUIPE",
        'menu_withdraw': "🏧 SACAR",
        'menu_profile': "⚙️ PERFIL",
        'ai_searching': ["🔄 Escaneando...", "🌍 Buscando melhor pgto...", "✅ **TAREFA ENCONTRADA!**"],
        'ai_found': "🎯 **MISSÃO ATIVA #99**\n━━━━━━━━━━\nO sistema escolheu isto:\n\n🔥 **{offer_name}**\n🛡️ **Tipo:** Alto Valor.\n💰 **Pagamento:** USD/Cripto.",
        'passive_found': "💤 **MODO MINERAÇÃO AUTO**\n━━━━━━━━━━\nInstale e ganhe renda passiva:\n\n🚀 **{offer_name}**\n(Honeygain/Pawns/Traffmonetizer)",
        'test_found': "👨‍💻 **TRABALHO QA TESTER**\n━━━━━━━━━━\nTorne-se um testador de software.\n\n✅ **Pagam até 20€ por erro.**\n✅ Trabalho profissional.\n✅ Sem experiência.\n\n🔗 [REGISTRO TESTBIRDS]({link})",
        'btn_accept': "🚀 ACEITAR TRABALHO",
        'btn_back': "🔙 VOLTAR",
        'withdraw_error': "⚠️ **SAQUE BLOQUEADO:**\nComplete 1 Missão para liberar.",
        'invite_text': "🔗 **LINK DA EQUIPE:**\n`{link}`\n\nGanhe 10% de comissão.",
        'profile': "👤 **PERFIL**\nNome: {name}\nEmail: `{email}`\nIdioma: Português"
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
    if hasattr(db, 'add_user'): await db.add_user(user.id, user.first_name, user.username)

    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    txt = get_text(lang, 'welcome').format(name=user.first_name)
    btn_txt = get_text(lang, 'btn_start')
    kb = [[InlineKeyboardButton(btn_txt, url=LINK_ENTRY_DETECT)]]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user
    if text in ["DASHBOARD", "PERFIL", "MINAR", "START", "/START"]: await show_dashboard(update, context); return
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            await show_dashboard(update, context)
            return
        else: await update.message.reply_text("❌ Error."); return
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        country = parts[2] if len(parts) >= 3 else 'GL'
        context.user_data['country'] = country
        await update.message.reply_text(f"🌍 **Connected: {country}**\n📥 Email:", parse_mode="Markdown")
        context.user_data['waiting_for_email'] = True
        return

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    country = context.user_data.get('country', 'GL')
    tokens = context.user_data.get('tokens', INITIAL_BONUS)
    usd_val = tokens * HIVE_PRICE
    
    t_title = get_text(lang, 'dashboard_title')
    t_metrics = get_text(lang, 'metrics')
    t_wallet = get_text(lang, 'wallet')
    t_h = get_text(lang, 'balance_hive').format(tokens=tokens)
    t_u = get_text(lang, 'balance_usd').format(usd=usd_val)
    
    dashboard_text = (
        f"{t_title}\n🆔 `{user.id}` | 📍 `{country}`\n\n"
        f"{t_metrics}\n➤ ▮▮▮▮▮▮▮▮▯▯ 80%\n\n"
        f"{t_wallet}\n{t_h}\n{t_u}\n"
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'menu_ai'), callback_data="ai_task_search")],
        [InlineKeyboardButton(get_text(lang, 'menu_test'), callback_data="pro_tester")], # NUEVO: Testbirds
        [InlineKeyboardButton(get_text(lang, 'menu_passive'), callback_data="passive_income")],
        [InlineKeyboardButton(get_text(lang, 'menu_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'menu_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'menu_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def ai_task_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    msgs = get_text(lang, 'ai_searching')
    for msg in msgs:
        try:
            await query.message.edit_text(f"🧠 **HIVE AI**\n\n{msg}", parse_mode="Markdown")
            await asyncio.sleep(0.8)
        except: pass

    country = context.user_data.get('country', 'DEFAULT')
    offer = OFFERS.get(country, OFFERS['DEFAULT']) # Fallback
    
    final_txt = get_text(lang, 'ai_found').format(offer_name=offer['name'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_accept'), url=offer['link'])], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(final_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def passive_income_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    passive_links = [
        {'name': 'Honeygain', 'link': LINKS['HONEYGAIN']},
        {'name': 'Pawns.app', 'link': LINKS['PAWNS']},
        {'name': 'Traffmonetizer', 'link': LINKS['TRAFFMONETIZER']}
    ]
    offer = random.choice(passive_links)
    
    txt = get_text(lang, 'passive_found').format(offer_name=offer['name'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_accept'), url=offer['link'])], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- FUNCIÓN NUEVA: PRO TESTER (TESTBIRDS) ---
async def pro_tester_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    txt = get_text(lang, 'test_found').format(link=LINKS['TESTBIRDS'])
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_accept'), url=LINKS['TESTBIRDS'])], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown", disable_web_page_preview=True)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.from_user.language_code
    data = query.data
    
    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "ai_task_search": await ai_task_search(update, context)
    elif data == "passive_income": await passive_income_menu(update, context)
    elif data == "pro_tester": await pro_tester_menu(update, context) # Nuevo Handler
    elif data == "my_profile":
        email = context.user_data.get('email', 'N/A')
        txt = get_text(lang, 'profile').format(name=query.from_user.first_name, email=email)
        kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
        await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "withdraw":
        await query.answer("⚠️ Locked", show_alert=True)
        await query.message.reply_text(get_text(lang, 'withdraw_error'), parse_mode="Markdown")
    elif data == "invite_friends":
        link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
        await query.answer()
        await query.message.reply_text(get_text(lang, 'invite_text').format(link=link), parse_mode="Markdown")

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Invite...")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset done.")
