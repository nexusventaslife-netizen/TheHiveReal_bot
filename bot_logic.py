import logging
import re
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA ---
HIVE_PRICE = 0.012 
INITIAL_BONUS = 500 # Bono visual de bienvenida
ADMIN_ID = 123456789 

# TU WEB DE RENDER (Donde está el index.html de la verificación)
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# IMAGEN DE BIENVENIDA (TU FOTO DE BEEBY)
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-1.jpg"

# --- ☢️ ARSENAL MAESTRO DE ENLACES (MISIONES COMPLETAS) ---
# No he quitado ni uno solo. Aquí están todos tus activos.
LINKS = {
    # --- TIER 1: FARMING RÁPIDO ---
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINPAYU': "https://www.coinpayu.com/?r=TheSkywalker", # Usado también para la verificación
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'EVERVE': "https://everve.net/ref/1950045/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29", # Web Directa (Segura)
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    
    # --- TIER 2: AUTOMATIZACIÓN (BOTS) ---
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

    # --- TIER 3: HIGH TICKET (BANCOS) ---
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

# --- TEXTOS LEGALES (COMPLETOS) ---
LEGAL_TEXT = """
📜 **PROTOCOLO DE SEGURIDAD Y PRIVACIDAD - THEONE HIVE**
─────────────────────────────────
**1. Consenso de Red (DAO):**
Al operar este nodo (bot), aceptas participar en nuestra organización autónoma descentralizada. Tu actividad contribuye al crecimiento de la colmena.

**2. Naturaleza de la Minería:**
Actuamos como un Hub de conexión (Layer 2). Las recompensas en USD dependen de la "Prueba de Trabajo" (PoW) que realices en las plataformas externas vinculadas.

**3. Soberanía de Datos:**
Tu ID de Telegram y correo electrónico son procesados bajo encriptación SHA-256. No vendemos, alquilamos ni exponemos tu identidad a corporaciones de terceros.

**4. Política de Retiros:**
El puente de salida (Bridge) se activa al alcanzar el umbral de $10.00 USD. Cualquier intento de Sybil Attack (multicuentas) resultará en el baneo permanente del nodo.

_Versión del Protocolo: v19.1 (Omega)_
"""

# --- TEXTOS: INTERFAZ GAMIFICADA (NARRATIVA COMPLETA) ---
TEXTS = {
    'es': {
        # BIENVENIDA CON VERIFICACIÓN OBLIGATORIA
        'welcome': (
            "🐝 **¡SISTEMA HIVE DETECTADO!**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**, tu IA de gestión.\n\n"
            "🔐 **PROTOCOLO DE SEGURIDAD:**\n"
            "El sistema ha detectado una nueva conexión. Para proteger la economía de la Colmena y evitar bots masivos, necesitamos validar tu **Humanidad**.\n\n"
            "👇 **INSTRUCCIONES:**\n"
            "1. Pulsa el botón **🧬 VALIDAR HUMANIDAD**.\n"
            "2. Se abrirá el escáner seguro (Web App).\n"
            "3. Pulsa 'Activar Nodo' dentro de la web.\n"
            "4. Tu acceso será concedido automáticamente."
        ),
        'btn_verify_webapp': "🧬 VALIDAR HUMANIDAD (WEB)",
        
        # DASHBOARD PRO GAMIFICADO
        'dashboard_body': """
🎮 **HIVE COMMAND CENTER** 💠
──────────────────────────
👤 **Operador:** {name}
🛡️ **Rango Actual:** {rank}
🔗 **Red Neural:** {refs} Nodos conectados

💰 **ALMACÉN DE MIEL (USD):**
**${usd:.2f}** _(Saldo Líquido)_

💠 **POLEN (HIVE TOKENS):**
**{tokens} HVT** 
_(Staking Automático Activo)_

📊 **PROGRESO DE EVOLUCIÓN:**
`[█████░░░░░] 50%`
──────────────────────────
⚔️ **SELECCIONA TU MISIÓN:**
""",
        # BOTONES
        'btn_t1': "🟢 ZONA 1: Recolección (Easy Farm)",
        'btn_t2': "🟡 ZONA 2: Automatización (Bots)",
        'btn_t3': "🔴 ZONA 3: Contratos Élite (High $)",
        
        'btn_help': "📜 Códice (Ayuda)",
        'btn_team': "📡 Expandir Red (Invitar)",
        'btn_profile': "⚙️ Inventario & Stats",
        'btn_withdraw': "🏧 Bridge (Retirar)",
        
        # TEXTO DE AYUDA INMERSIVO
        'help_text': (
            "🤖 **CÓDICE DE LA COLMENA - GUÍA OPERATIVA**\n"
            "───────────────────────\n\n"
            "**🟢 NIVEL 1: FARMING RÁPIDO**\n"
            "Acciones de bajo coste energético. Recolecta satoshis y puntos viendo publicidad o jugando. Es el 'grindeo' inicial necesario para subir de nivel.\n\n"
            "**🟡 NIVEL 2: DESPLIEGUE DE BOTS**\n"
            "Instala software de minería pasiva en tus dispositivos. Ellos trabajarán en segundo plano mientras tú duermes. Ingreso 100% pasivo.\n\n"
            "**🔴 NIVEL 3: GRANDES CONTRATOS**\n"
            "Firmar contratos con Bancos y Exchanges. Aquí es donde se gana la verdadera Miel Líquida. Bonos de $10 a $50 USD por acción.\n\n"
            "💎 **TOKENOMICS:** Acumula HVT (Polen) para futuros Airdrops y gobernanza."
        ),

        't1_title': "🟢 **ZONA DE FARMING (NIVEL 1)**\nEjecuta estas tareas simples para acumular recursos básicos:",
        't2_title': "🟡 **ZONA DE AUTOMATIZACIÓN (NIVEL 2)**\nDespliega estos nodos en tu hardware y gana pasivamente:",
        't3_title': "🔴 **ZONA DE ALTO RENDIMIENTO (NIVEL 3)**\nContratos financieros de alto valor (High Ticket):",
        
        'btn_back': "🔙 REGRESAR A LA BASE",
        'btn_legal': "⚖️ Protocolos Legales",
        'withdraw_lock': "🔒 **ACCESO DENEGADO**\n\nNivel de autorización insuficiente.\nRequieres acumular $10.00 en Miel para desbloquear el puente de retiro."
    },
    'en': { 
        'welcome': "🐝 **SYSTEM DETECTED**\nHuman verification required.", 
        'btn_verify_webapp': "🧬 VERIFY HUMANITY",
        'dashboard_body': "🎮 **COMMAND CENTER**\nPlayer: {name}\n💰 Honey: ${usd:.2f}",
        'btn_t1': "🟢 LVL 1", 'btn_t2': "🟡 LVL 2", 'btn_t3': "🔴 LVL 3",
        'btn_help': "📜 Codex", 'btn_team': "📡 Expand", 'btn_profile': "⚙️ Inventory", 'btn_withdraw': "🏧 Bridge",
        'help_text': "Guide...", 
        't1_title': "🟢 LVL 1", 't2_title': "🟡 LVL 2", 't3_title': "🔴 LVL 3",
        'btn_back': "🔙 BASE", 'btn_legal': "⚖️ Protocols", 'withdraw_lock': "🔒 LOCKED"
    },
    'pt': { 
        'welcome': "🐝 **SISTEMA DETECTADO**\nVerificação necessária.", 
        'btn_verify_webapp': "🧬 VERIFICAR HUMANIDADE",
        'dashboard_body': "🎮 **CENTRO DE COMANDO**\nJogador: {name}\n💰 Mel: ${usd:.2f}",
        'btn_t1': "🟢 LVL 1", 'btn_t2': "🟡 LVL 2", 'btn_t3': "🔴 LVL 3",
        'btn_help': "📜 Códice", 'btn_team': "📡 Expandir", 'btn_profile': "⚙️ Inventário", 'btn_withdraw': "🏧 Ponte",
        'help_text': "Guia...",
        't1_title': "🟢 LVL 1", 't2_title': "🟡 LVL 2", 't3_title': "🔴 LVL 3",
        'btn_back': "🔙 BASE", 'btn_legal': "⚖️ Protocolos", 'withdraw_lock': "🔒 BLOQUEADO"
    }
}

def get_text(lang_code, key):
    lang = 'en'
    if lang_code:
        if lang_code.startswith('es'): lang = 'es'
        elif lang_code.startswith('pt'): lang = 'pt'
    return TEXTS[lang].get(key, TEXTS['en'][key])

def generate_captcha():
    """Genera una operación matemática aleatoria (Fallback)."""
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 10)
    op = random.choice(['+', '-'])
    
    if op == '+': 
        result = num1 + num2
        text = f"{num1} + {num2}"
    else: 
        if num1 < num2: num1, num2 = num2, num1 
        result = num1 - num2
        text = f"{num1} - {num2}"
        
    return text, str(result)

# --- LÓGICA DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    
    args = context.args
    referrer_id = None
    if args and str(args[0]) != str(user.id): referrer_id = args[0]
        
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Simulación de carga "Hacker/RPG"
    msg = await update.message.reply_text("🔄 Inicializando Protocolo Hive...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.7) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # --- LÓGICA DE VERIFICACIÓN ---
    # Si el usuario NO está verificado, le mostramos el botón que abre la Web App (Tu página trampa en Render)
    if not context.user_data.get('verified'):
        txt = get_text(lang, 'welcome').format(name=user.first_name)
        
        # AQUÍ ESTÁ EL TRUCO: WebAppInfo abre tu HTML dentro de Telegram
        # El HTML en Render es el que contiene el enlace a COINPAYU escondido
        kb = [[InlineKeyboardButton(
            get_text(lang, 'btn_verify_webapp'), 
            web_app=WebAppInfo(url=RENDER_URL)
        )]]
        
        try:
            await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        # Si ya está verificado, entra directo al Dashboard
        await show_dashboard(update, context)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja datos recibidos de la Web App o texto normal."""
    
    # --- MANEJO DE DATOS DE LA WEB APP ---
    if update.message.web_app_data:
        data = update.message.web_app_data.data
        if data == "VERIFIED_OK":
            context.user_data['verified'] = True
            # Mensaje de éxito
            await update.message.reply_text("✅ **VERIFICACIÓN HUMANA EXITOSA.**\n\nSincronizando nodos...", parse_mode="Markdown")
            await asyncio.sleep(1)
            await show_dashboard(update, context)
            return

    # --- MANEJO DE TEXTO NORMAL ---
    text = update.message.text.strip().upper() if update.message.text else ""
    user = update.effective_user
    
    if text == "/RESET":
        context.user_data.clear()
        await update.message.reply_text("🔄 **REINICIO DE SISTEMA.**\nPerfil borrado de caché. Escribe /start")
        return

    if text in ["DASHBOARD", "PERFIL", "/START"]: 
        await show_dashboard(update, context)
        return
    
    # Si sigue habiendo un captcha pendiente (Fallback manual)
    if context.user_data.get('waiting_for_captcha'):
        correct_answer = context.user_data.get('captcha_result')
        if text == correct_answer:
            context.user_data['waiting_for_captcha'] = False
            context.user_data['verified'] = True
            await update.message.reply_text("✅ **VERIFICACIÓN EXITOSA.**\nEntrando...")
            await show_dashboard(update, context)
        else:
            quest, res = generate_captcha()
            context.user_data['captcha_result'] = res
            await update.message.reply_text(f"❌ **ERROR.** Intente de nuevo: {quest}")
        return
    
    # Backdoor Admin (Huevo de pascua)
    if text.startswith("HIVE-777"):
        await update.message.reply_text("🔓 **BACKDOOR ACTIVADO.**\nBienvenido Admin.", parse_mode="Markdown")
        context.user_data['verified'] = True
        await show_dashboard(update, context)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PANEL PRINCIPAL GAMIFICADO"""
    user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    
    # RANGOS TIPO RPG (SISTEMA DE PROGRESO)
    rank = "🐛 LARVA (Nvl 1)"
    if ref_count >= 5: rank = "🐝 OBRERA (Nvl 10)"
    if ref_count >= 20: rank = "👑 REINA (Nvl 50)"
    if ref_count >= 50: rank = "🛡️ GUARDIANA (Nvl 99)"
    
    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, 
        tokens=tokens, 
        usd=usd, 
        rank=rank, 
        refs=ref_count
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")],
        
        [InlineKeyboardButton(get_text(lang, 'btn_help'), callback_data="help_guide")],
        
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MENÚS DE MISIONES (TIERS) ---

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("📺 COINPAYU (Ads)", url=LINKS['COINPAYU']), InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN'])],
        [InlineKeyboardButton("🎮 GAMEHAG (Juegos)", url=LINKS['GAMEHAG']), InlineKeyboardButton("🤖 POLLO AI (Video)", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("🎰 BETFURY (Web)", url=LINKS['BETFURY']), InlineKeyboardButton("👍 EVERVE (Social)", url=LINKS['EVERVE'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't1_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN (Auto)", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM (Auto)", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("📱 PAIDWORK (App)", url=LINKS['PAIDWORK']), InlineKeyboardButton("⏱ TIMEBUCKS", url=LINKS['TIMEBUCKS'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("📶 TRAFFMONETIZER (Auto)", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("♟️ PAWNS (Auto)", url=LINKS['PAWNS']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("🐦 TESTBIRDS", url=LINKS['TESTBIRDS']), InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text(get_text(lang, 't2_title'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("📈 BYBIT (Bonus)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO (Yield)", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT (Bank)", url=LINKS['REVOLUT']), InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER'])],
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
    txt = f"📡 **EXPANSIÓN DE RED**\n─────────────────\n👑 **Nodos Conectados:** `{ref_count}`\n💰 **Recompensa de Bloque:** 10%\n\n🔗 **ENLACE DE RECLUTAMIENTO:**\n`{link}`" 
    kb = [[InlineKeyboardButton("📤 Difundir Señal", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def legal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [[InlineKeyboardButton("🔙 VOLVER A INVENTARIO", callback_data="my_profile")]]
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
            [InlineKeyboardButton("⚖️ Protocolos Legales", callback_data="legal_terms")],
            [InlineKeyboardButton("🔙 Volver a la Base", callback_data="go_dashboard")]
        ]
        await query.message.edit_text(f"👤 **INVENTARIO DE JUGADOR**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "withdraw": 
        await query.answer("🔒 BLOQUEADO POR PROTOCOLO", show_alert=True)
        await query.message.reply_text(get_text(query.from_user.language_code, 'withdraw_lock'), parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return 
    message = " ".join(context.args)
    if message: await update.message.reply_text(f"📢 **TRANSMISIÓN GLOBAL:**\n{message}", parse_mode="Markdown")

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Use el menú Equipo")
async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Sistema Reiniciado.")
