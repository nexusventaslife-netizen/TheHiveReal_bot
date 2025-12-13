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
INITIAL_BONUS = 500  # Actualizado a 500 como querías en la gamificación
ADMIN_ID = 123456789 

# --- ENLACES DE SISTEMA ---
RENDER_URL = "https://thehivereal-bot.onrender.com" 
# Eliminamos LINK_ENTRY_DETECT porque ya no usamos redirección externa, usamos WebApp

# IMAGEN DE BIENVENIDA
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-1.jpg"

# --- ☢️ ARSENAL MAESTRO DE ENLACES (LISTA EXTENDIDA ORIGINAL) ---
LINKS = {
    # --- SECCIÓN 1: CASINO & SUERTE (JACKPOTS) ---
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29", # Corregido a Web Directa segura
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    
    # --- SECCIÓN 2: FINTECH & TRADING (ALTO VALOR) ---
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    
    # --- SECCIÓN 3: MINERÍA PASIVA (NODOS) ---
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    
    # --- SECCIÓN 4: TRABAJO ACTIVO & FREELANCE ---
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
    
    # --- SECCIÓN 5: HERRAMIENTAS IA & MARKETING (NUEVOS) ---
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    
    # --- SECCIÓN 6: OFERTAS CPA ---
    'FREECASH': "https://freecash.com/r/XYN98"
}

# --- TEXTOS LEGALES (TU VERSIÓN COMPLETA) ---
LEGAL_TEXT = """
📜 **TÉRMINOS DE SERVICIO Y POLÍTICA DE PRIVACIDAD**
─────────────────────────────────

**1. Aceptación del Servicio**
Al iniciar y utilizar el bot THEONE HIVE, usted acepta incondicionalmente estos términos y condiciones.

**2. Naturaleza del Servicio**
Este bot actúa exclusivamente como un **intermediario de afiliación**. Proporcionamos acceso organizado a plataformas de terceros. 
- No somos empleadores.
- No garantizamos ingresos fijos.
- Las ganancias dependen 100% del esfuerzo del usuario en las plataformas externas.

**3. Descargo de Responsabilidad (Disclaimer)**
No nos hacemos responsables por:
- Pagos retrasados de plataformas externas (ej: Freebitcoin, Bybit).
- Cambios en las políticas de dichas plataformas.
- Pérdidas derivadas de inversiones en trading o apuestas.

**4. Privacidad de Datos**
Recopilamos estrictamente:
- Su ID numérico de Telegram.
- Su nombre de usuario público.
- Su correo electrónico (para validación de cuenta).
**NO** compartimos, vendemos ni alquilamos sus datos a terceros.

**5. Política de Pagos del Bot**
Los retiros de "Miel" (Saldo interno) están sujetos a una auditoría antifraude. El mínimo de retiro es de $10.00 USD. Cualquier intento de usar bots, scripts o multicuentas resultará en un baneo permanente.

_Última actualización: Diciembre 2025_
"""

# --- TEXTOS: INTERFAZ "HIVE MIND" (TU VERSIÓN COMPLETA) ---
TEXTS = {
    'es': {
        # MODIFICADO: Ahora usa la WebApp para verificación automática
        'welcome': (
            "🐝 **SISTEMA HIVE DETECTADO**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**, tu IA de gestión.\n\n"
            "🔐 **PROTOCOLO DE INICIO:**\n"
            "El sistema ha detectado que tu nodo Larva no está sincronizado. Para acceder a la Colmena y recibir tu **BONO DE BIENVENIDA**, necesitamos validar tu humanidad.\n\n"
            "👇 **PULSA EL BOTÓN PARA ACTIVAR:**"
        ),
        'btn_verify_webapp': "🧬 VALIDAR HUMANIDAD (AUTO)",
        
        # DASHBOARD COMPLETO CON GAMIFICACIÓN
        'dashboard_body': """
🎮 **HIVE COMMAND CENTER**
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
        'btn_t1': "🟢 ZONA 1 (Farming Rápido)",
        'btn_t2': "🟡 ZONA 2 (Automatización)",
        'btn_t3': "🔴 ZONA 3 (Alta Rentabilidad)",
        
        'btn_help': "📜 Códice (Ayuda)",
        'btn_team': "📡 Expandir Red (Invitar)",
        'btn_profile': "⚙️ Inventario & Stats",
        'btn_withdraw': "🏧 Bridge (Retirar)",
        
        # TEXTO DE AYUDA EXTENDIDO
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
    # IDIOMAS ADICIONALES (MANTENIDOS)
    'en': { 
        'welcome': "🐝 **SYSTEM DETECTED**\nVerify humanity to proceed.", 
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

# --- LÓGICA PRINCIPAL DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función de inicio: Muestra WebApp si no está verificado."""
    user = update.effective_user
    lang = user.language_code
    
    args = context.args
    referrer_id = None
    if args and str(args[0]) != str(user.id): referrer_id = args[0]
        
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Limpieza visual
    msg = await update.message.reply_text("🔄 Inicializando sistemas...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # --- LÓGICA DE VERIFICACIÓN ---
    # 1. ¿Ya tiene email registrado y verificado? -> Dashboard
    if context.user_data.get('verified') and context.user_data.get('email_registered'):
        await show_dashboard(update, context)
        return

    # 2. Si NO está verificado -> WebApp (Render)
    txt = get_text(lang, 'welcome').format(name=user.first_name)
    
    kb = [[InlineKeyboardButton(
        get_text(lang, 'btn_verify_webapp'), 
        web_app=WebAppInfo(url=RENDER_URL)
    )]]
    
    try:
        await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja WebApp Data y Texto normal (Incluyendo Email)"""
    
    # --- 1. RECEPCIÓN DE LA SEÑAL WEBAPP (VERIFICACIÓN) ---
    if update.message.web_app_data:
        data = update.message.web_app_data.data
        if data == "VERIFIED_OK":
            context.user_data['verified'] = True
            
            # --- AQUÍ ESTÁ LA FUNCIÓN QUE FALTABA ---
            # Activamos la bandera para pedir el email inmediatamente
            context.user_data['waiting_for_email'] = True
            
            await update.message.reply_text(
                "✅ **VERIFICACIÓN HUMANA EXITOSA.**\n\n"
                "📧 **ÚLTIMO PASO:**\n"
                "Por favor, ingresa tu dirección de **Correo Electrónico** para vincular tu billetera y recibir el bono:",
                parse_mode="Markdown"
            )
            return

    # --- 2. MANEJO DE TEXTO NORMAL ---
    text = update.message.text.strip() if update.message.text else ""
    user = update.effective_user

    # --- 3. LÓGICA DE CAPTURA DE EMAIL (CRÍTICO) ---
    if context.user_data.get('waiting_for_email'):
        # Validación básica de email
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['waiting_for_email'] = False
            context.user_data['email_registered'] = True
            
            # Guardamos en la base de datos
            if hasattr(db, 'update_email'): 
                await db.update_email(user.id, text)
            
            await update.message.reply_text(
                "✅ **REGISTRO COMPLETADO.**\n"
                "Tus datos han sido encriptados y tu nodo está activo.",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)
            await show_dashboard(update, context)
            return
        else:
            await update.message.reply_text("⚠️ **ERROR:** Formato de correo inválido. Inténtalo de nuevo:")
            return

    # Comandos de Sistema
    if text.upper() == "/RESET":
        context.user_data.clear()
        await update.message.reply_text("🔄 Sistema Reiniciado. Escribe /start")
        return

    if text.upper() in ["DASHBOARD", "PERFIL", "/START"]: 
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
    
    # Cálculo de Rangos (Gamificación)
    rank = "🐛 LARVA (Nvl 1)"
    if ref_count >= 5: rank = "🐝 OBRERA (Nvl 10)"
    if ref_count >= 20: rank = "👑 REINA (Nvl 50)"
    
    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, tokens=tokens, usd=usd, rank=rank, refs=ref_count
    )
    
    # Menú Principal
    kb = [
        # AQUÍ ESTÁ EL BOTÓN DE MONETIZACIÓN INTEGRADO EN EL DASHBOARD (PARA QUE NO MOLESTE AL ENTRAR)
        [InlineKeyboardButton("🎁 RECLAMAR BONO EXTRA (COINPAYU)", url=LINKS['COINPAYU'])],
        
        [InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")],
        
        [InlineKeyboardButton(get_text(lang, 'btn_help'), callback_data="help_guide")],
        
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MENÚS DE LOS 3 TIERS (TODOS LOS LINKS DE TU CÓDIGO ORIGINAL) ---

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
    await query.message.edit_text(get_text(lang, 'help_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); ref_count = len(user_data.get('referrals', [])) if user_data else 0; link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = f"📡 **RED**\n👑 Nodos: `{ref_count}`\n🔗 `{link}`" 
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
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
