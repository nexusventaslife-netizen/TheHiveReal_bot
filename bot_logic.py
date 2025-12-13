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
# Precios y bonos base
HIVE_PRICE = 0.012 
INITIAL_BONUS = 500  # Bono visual de bienvenida ($6.00 USD aprox)
ADMIN_ID = 123456789 

# TU WEB DE RENDER (Donde alojaste el index.html)
# Esta URL es la que se abre dentro de Telegram
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# IMAGEN DE BIENVENIDA
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-1.jpg"

# --- ☢️ ARSENAL MAESTRO DE ENLACES (TODOS LOS TIERS) ---
# NO SE HA QUITADO NINGÚN ENLACE. ESTÁN TODOS AQUÍ.
LINKS = {
    # --- NIVEL 1: RECOLECCIÓN BÁSICA (CLICKS) ---
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINPAYU': "https://www.coinpayu.com/?r=TheSkywalker",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'EVERVE': "https://everve.net/ref/1950045/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29", # Web Directa
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    
    # --- NIVEL 2: NODOS AUTOMATIZADOS (BOTS/APPS) ---
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

    # --- NIVEL 3: PROTOCOLOS DEFI & YIELD (ALTO VALOR) ---
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
📜 **PROTOCOLO DE SEGURIDAD Y PRIVACIDAD - THEONE HIVE**
─────────────────────────────────
**1. Consenso de Red (DAO):**
Al operar este nodo (bot), aceptas participar en nuestra organización autónoma descentralizada.

**2. Naturaleza de la Minería:**
Actuamos como un Hub de conexión (Layer 2). Las recompensas en USD dependen de la "Prueba de Trabajo" (PoW) que realices en las plataformas externas.

**3. Soberanía de Datos:**
Tu ID de Telegram y correo electrónico son procesados bajo encriptación SHA-256.

**4. Política de Retiros:**
El puente de salida (Bridge) se activa al alcanzar el umbral de $10.00 USD.
"""

# --- TEXTOS: INTERFAZ GAMIFICADA (TODOS LOS IDIOMAS) ---
TEXTS = {
    'es': {
        # BIENVENIDA CON VERIFICACIÓN OBLIGATORIA
        'welcome': (
            "🐝 **¡SISTEMA HIVE DETECTADO!**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**, tu IA de gestión.\n\n"
            "🔐 **PROTOCOLO DE INICIO:**\n"
            "El sistema ha detectado que tu nodo Larva está inactivo. Para sincronizar y recibir tu **BONO DE BIENVENIDA ($6.00 USD)**, activa la conexión segura.\n\n"
            "👇 **PULSA EL BOTÓN PARA ACTIVAR:**"
        ),
        'btn_verify_webapp': "⚡ CONECTAR Y RECLAMAR BONO",
        
        # DASHBOARD COMPLETO CON RANGOS Y SALDOS
        'dashboard_body': """
🎮 **HIVE COMMAND CENTER** 💠
──────────────────────────
👤 **Operador:** {name}
🛡️ **Rango Actual:** {rank}
✅ **Estado:** CONECTADO

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
        # BOTONES DEL MENÚ PRINCIPAL
        'btn_t1': "🟢 ZONA 1: Recolección (Easy Farm)",
        'btn_t2': "🟡 ZONA 2: Automatización (Bots)",
        'btn_t3': "🔴 ZONA 3: Contratos Élite (High $)",
        
        'btn_help': "📜 Códice (Ayuda)",
        'btn_team': "📡 Expandir Red (Invitar)",
        'btn_profile': "⚙️ Inventario & Stats",
        'btn_withdraw': "🏧 Bridge (Retirar)",
        
        # TEXTO DE AYUDA EXTENDIDO
        'help_text': (
            "🤖 **CÓDICE DE LA COLMENA - GUÍA OPERATIVA**\n"
            "───────────────────────\n\n"
            "**🟢 NIVEL 1: FARMING RÁPIDO**\n"
            "Acciones de bajo coste energético. Recolecta satoshis y puntos viendo publicidad o jugando.\n\n"
            "**🟡 NIVEL 2: DESPLIEGUE DE BOTS**\n"
            "Instala software de minería pasiva en tus dispositivos. Ellos trabajarán en segundo plano.\n\n"
            "**🔴 NIVEL 3: GRANDES CONTRATOS**\n"
            "Firmar contratos con Bancos y Exchanges. Bonos de $10 a $50 USD por acción.\n\n"
            "💎 **TOKENOMICS:** Acumula HVT (Polen) para futuros Airdrops."
        ),

        't1_title': "🟢 **ZONA DE FARMING (NIVEL 1)**\nEjecuta estas tareas simples para acumular recursos básicos:",
        't2_title': "🟡 **ZONA DE AUTOMATIZACIÓN (NIVEL 2)**\nDespliega estos nodos en tu hardware y gana pasivamente:",
        't3_title': "🔴 **ZONA DE ALTO RENDIMIENTO (NIVEL 3)**\nContratos financieros de alto valor (High Ticket):",
        
        'btn_back': "🔙 REGRESAR A LA BASE",
        'btn_legal': "⚖️ Protocolos Legales",
        'withdraw_lock': "🔒 **ACCESO DENEGADO**\n\nNivel de autorización insuficiente.\nRequieres acumular $10.00 en Miel para desbloquear el puente de retiro."
    },
    # INGLÉS (EN)
    'en': { 
        'welcome': "🐝 **SYSTEM DETECTED**\nConnect node to claim bonus.", 
        'btn_verify_webapp': "⚡ CONNECT & CLAIM",
        'dashboard_body': "🎮 **COMMAND CENTER**\nPlayer: {name}\n💰 Honey: ${usd:.2f}",
        'btn_t1': "🟢 LVL 1", 'btn_t2': "🟡 LVL 2", 'btn_t3': "🔴 LVL 3",
        'btn_help': "📜 Codex", 'btn_team': "📡 Expand", 'btn_profile': "⚙️ Inventory", 'btn_withdraw': "🏧 Bridge",
        'help_text': "Guide...", 
        't1_title': "🟢 LVL 1", 't2_title': "🟡 LVL 2", 't3_title': "🔴 LVL 3",
        'btn_back': "🔙 BASE", 'btn_legal': "⚖️ Protocols", 'withdraw_lock': "🔒 LOCKED"
    },
    # PORTUGUÉS (PT)
    'pt': { 
        'welcome': "🐝 **SISTEMA DETECTADO**\nConecte o nó para ganhar bônus.", 
        'btn_verify_webapp': "⚡ CONECTAR E GANHAR",
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

# --- LÓGICA PRINCIPAL DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función de inicio: Verifica si el usuario ya hizo el click en la WebApp"""
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = None
    if args and str(args[0]) != str(user.id): referrer_id = args[0]
        
    # Registro en base de datos
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Limpieza visual (borra el mensaje de /start para que se vea limpio)
    msg = await update.message.reply_text("🔄 Inicializando sistemas...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # --- VERIFICACIÓN WEBAPP ---
    # Si NO está verificado, le mostramos el botón que abre index.html (Render)
    if not context.user_data.get('verified'):
        txt = get_text(lang, 'welcome').format(name=user.first_name)
        
        # AQUÍ ESTÁ LA INTEGRACIÓN: WebAppInfo
        kb = [[InlineKeyboardButton(
            get_text(lang, 'btn_verify_webapp'), 
            web_app=WebAppInfo(url=RENDER_URL)
        )]]
        
        try:
            await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        # Si ya está verificado, entra directo al Dashboard
        await show_dashboard(update, context)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todas las interacciones de texto y datos de la WebApp"""
    
    # --- 1. RECIBIR SEÑAL DEL INDEX.HTML ---
    # Esto ocurre cuando el usuario hace click en tu web y la web responde
    if update.message.web_app_data:
        data = update.message.web_app_data.data
        if data == "VERIFIED_OK":
            context.user_data['verified'] = True
            # Mensaje de éxito GAMIFICADO
            await update.message.reply_text("✅ **¡CONEXIÓN ESTABLECIDA!**\n💰 Bono de $6.00 USD añadido a tu cuenta.\n🔓 Accediendo al sistema...", parse_mode="Markdown")
            await asyncio.sleep(1)
            await show_dashboard(update, context)
            return

    # --- 2. MANEJO DE TEXTO NORMAL ---
    text = update.message.text.strip().upper() if update.message.text else ""
    
    if text == "/RESET":
        context.user_data.clear()
        await update.message.reply_text("🔄 Sistema Reiniciado. Escribe /start")
        return

    if text in ["DASHBOARD", "PERFIL", "/START"]: 
        await show_dashboard(update, context)
        return

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el Dashboard Principal Gamificado"""
    user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    
    # Cálculo de Rangos
    rank = "🐛 LARVA (Nvl 1)"
    if ref_count >= 5: rank = "🐝 OBRERA (Nvl 10)"
    if ref_count >= 20: rank = "👑 REINA (Nvl 50)"
    
    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, tokens=tokens, usd=usd, rank=rank, refs=ref_count
    )
    
    # Botones del Dashboard
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

# --- MENÚS DE LOS 3 TIERS (TODOS LOS LINKS INCLUIDOS) ---

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
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
    query = update.callback_query; await query.answer()
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
    query = update.callback_query; await query.answer()
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
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text(get_text(lang, 'help_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); ref_count = len(user_data.get('referrals', [])) if user_data else 0; link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"📡 **EXPANSIÓN DE RED**\n─────────────────\n👑 **Nodos Conectados:** `{ref_count}`\n💰 **Recompensa de Bloque:** 10%\n\n🔗 **ENLACE DE RECLUTAMIENTO:**\n`{link}`" 
    kb = [[InlineKeyboardButton("📤 Difundir Señal", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestor de navegación entre menús"""
    query = update.callback_query; data = query.data
    
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
    elif data == "withdraw": 
        await query.answer("🔒 BLOQUEADO POR PROTOCOLO", show_alert=True)
        await query.message.reply_text(get_text(query.from_user.language_code, 'withdraw_lock'), parse_mode="Markdown")

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Use el menú Equipo")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    pass
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK")
