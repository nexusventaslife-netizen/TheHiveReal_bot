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
INITIAL_BONUS = 500  # Bono de Bienvenida ($6.00 USD)
ADMIN_ID = 123456789 

# TU WEBAPP (Render) - Asegúrate de que esta URL sea la tuya
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# IMAGEN DE BIENVENIDA
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-1.jpg"

# --- ☢️ ARSENAL MAESTRO DE ENLACES (LISTA EXTENDIDA Y COMPLETA) ---
# Incluye exactamente los que me pasaste más los complementarios.
LINKS = {
    # --- SECCIÓN 1: CASINO & SUERTE (JACKPOTS) ---
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29", # Web
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
    
    # --- SECCIÓN 5: HERRAMIENTAS IA & MARKETING ---
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d"
}

# --- TEXTOS LEGALES ---
LEGAL_TEXT = """
📜 **TÉRMINOS DE SERVICIO Y POLÍTICA DE PRIVACIDAD**
─────────────────────────────────
**1. Aceptación del Servicio**
Al iniciar y utilizar el bot THEONE HIVE, usted acepta incondicionalmente estos términos.

**2. Naturaleza del Servicio**
Este bot actúa exclusivamente como un **intermediario de afiliación**. 
- No somos empleadores.
- Las ganancias dependen 100% del esfuerzo del usuario en las plataformas externas.

**3. Privacidad de Datos**
Recopilamos estrictamente: ID de Telegram y Email (para validación).
**NO** compartimos, vendemos ni alquilamos sus datos.

**4. Política de Pagos**
Mínimo de retiro: $10.00 USD. Prohibido multicuentas.
"""

# --- TEXTOS E IDIOMAS ---
TEXTS = {
    'es': {
        # MENSAJE 1: BIENVENIDA (FORZAR VERIFICACIÓN)
        'welcome': (
            "🧬 **SISTEMA HIVE DETECTADO**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**, tu IA de gestión.\n\n"
            "⚠️ **SINCRONIZACIÓN REQUERIDA:**\n"
            "Tu nodo Larva está desconectado. Para acceder a la Colmena y recibir tu bono, activa la conexión segura ahora.\n\n"
            "👇 **PASO 1: PULSA EL BOTÓN PARA ACTIVAR**"
        ),
        'btn_verify_webapp': "⚡ CONECTAR NODO (Verificar)",
        
        # MENSAJE 2: SOLICITUD DE EMAIL (AQUÍ FALLABA ANTES)
        'ask_email': (
            "✅ **CONEXIÓN ESTABLECIDA EXITOSAMENTE**\n"
            "───────────────────────\n"
            "La verificación biométrica ha sido aprobada.\n\n"
            "📧 **PASO 2 (FINAL):**\n"
            "Por favor, **escribe tu dirección de Correo Electrónico** para vincular tu billetera y asegurar tus fondos.\n\n"
            "_(Ejemplo: usuario@gmail.com)_"
        ),

        'dashboard_body': """
🎮 **CENTRO DE COMANDO HIVE**
──────────────────────────
👤 **Piloto:** {name}
🛡️ **Rango:** {rank}
✅ **Estado:** CONECTADO

💰 **TU SALDO (MIEL):**
**${usd:.2f} USD** 

💠 **TUS TOKENS (XP):**
**{tokens} HVT**

📊 **EVOLUCIÓN:**
`[█████░░░░░] 50%`
──────────────────────────
""",
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Auto)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_help': "📜 Ayuda", 'btn_team': "📡 Equipo", 'btn_profile': "⚙️ Perfil", 'btn_withdraw': "🏧 Retirar",
        't1_title': "🟢 **ZONA 1**", 't2_title': "🟡 **ZONA 2**", 't3_title': "🔴 **ZONA 3**",
        'btn_back': "🔙 VOLVER", 'withdraw_lock': "🔒 **BLOQUEADO** ($10 min)"
    },
    'en': { 'welcome': "Connect Node...", 'btn_verify_webapp': "Connect", 'ask_email': "Send Email", 'dashboard_body': "Dashboard", 'btn_back': "Back" }
}

def get_text(lang_code, key):
    lang = 'en'
    if lang_code and lang_code.startswith('es'): lang = 'es'
    return TEXTS[lang].get(key, TEXTS['en'][key])

# --- LÓGICA PRINCIPAL (CORREGIDA) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """INICIO DEL BOT"""
    user = update.effective_user
    lang = user.language_code
    args = context.args
    ref_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): await db.add_user(user.id, user.first_name, user.username, ref_id)

    # Limpieza
    msg = await update.message.reply_text("🔄 ...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5) 
    try: await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
    except: pass

    # CHEQUEO DE ESTADO:
    # 1. Si ya tiene Email verificado -> Dashboard
    user_data = await db.get_user(user.id)
    if user_data and user_data.get('email'): 
        context.user_data['email_registered'] = True
        context.user_data['verified'] = True
        await show_dashboard(update, context)
        return

    # 2. Si ya verificó WebApp pero falta mail -> Pedir Mail
    if context.user_data.get('verified') and not context.user_data.get('email_registered'):
        await ask_email_step(update, context)
        return

    # 3. Si no ha hecho nada -> Botón WebApp
    txt = get_text(lang, 'welcome').format(name=user.first_name)
    kb = [[InlineKeyboardButton(
        get_text(lang, 'btn_verify_webapp'), 
        web_app=WebAppInfo(url=RENDER_URL)
    )]]
    
    try: await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MANEJADOR DE MENSAJES Y WEBAPP"""
    
    # --- A. RESPUESTA DE LA WEBAPP (AQUÍ ESTÁ LA CORRECCIÓN) ---
    if update.message.web_app_data:
        if update.message.web_app_data.data == "VERIFIED_OK":
            context.user_data['verified'] = True
            
            # ¡IMPORTANTE! NO MOSTRAMOS DASHBOARD AÚN.
            # LLAMAMOS A LA FUNCIÓN QUE PIDE EL EMAIL.
            await ask_email_step(update, context)
            return

    text = update.message.text.strip() if update.message.text else ""

    # --- B. CAPTURA DEL EMAIL ---
    if context.user_data.get('waiting_for_email'):
        # Validar si parece un email
        if "@" in text and "." in text:
            # Guardar en DB
            if hasattr(db, 'update_email'): await db.update_email(update.effective_user.id, text)
            
            # Actualizar estado
            context.user_data['waiting_for_email'] = False
            context.user_data['email_registered'] = True
            
            await update.message.reply_text("✅ **EMAIL REGISTRADO.** Accediendo...")
            await asyncio.sleep(1)
            await show_dashboard(update, context)
            return
        else:
            await update.message.reply_text("⚠️ **ERROR:** Formato inválido. Por favor escribe un email real (ej: juan@gmail.com)")
            return

    # --- C. COMANDOS NORMALES ---
    if text.upper() == "/RESET": 
        context.user_data.clear(); await update.message.reply_text("Reset OK."); return
    if text.upper() in ["DASHBOARD", "PERFIL", "/START"]: 
        await show_dashboard(update, context); return

async def ask_email_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función auxiliar para pedir el email y activar el flag de espera"""
    lang = update.effective_user.language_code
    
    # ACTIVAMOS LA BANDERA PARA QUE EL PRÓXIMO MENSAJE SE LEA COMO EMAIL
    context.user_data['waiting_for_email'] = True
    
    txt = get_text(lang, 'ask_email')
    await update.message.reply_text(txt, parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PANEL PRINCIPAL"""
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE
    ref_count = len(user_data.get('referrals', [])) if user_data else 0
    
    rank = "🐛 LARVA"
    if ref_count >= 5: rank = "🐝 OBRERA"
    if ref_count >= 20: rank = "👑 REINA"

    body = get_text(lang, 'dashboard_body').format(name=user.first_name, rank=rank, usd=usd, tokens=tokens)
    
    # MENÚ COMPLETO (SIN RECORTES)
    kb = [
        # BOTÓN DE MONETIZACIÓN INTEGRADO
        [InlineKeyboardButton("🎁 ACTIVAR BONO EXTRA (COINPAYU)", url=LINKS['COINPAYU'])],
        
        [InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")],
        [InlineKeyboardButton(get_text(lang, 'btn_help'), callback_data="help_guide")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")],
        [InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")]
    ]
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MENÚS DE LOS 3 TIERS (TODOS LOS LINKS DE TU LISTA) ---
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
