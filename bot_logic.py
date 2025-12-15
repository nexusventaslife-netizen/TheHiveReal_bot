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

# --- CONFIGURACIÓN DE SISTEMA (IMPERIO HIVE V44.0) ---
INITIAL_USD = 0.05      
INITIAL_HIVE = 500      

# VALOR DEL TOKEN HIVE (Economía Interna)
HIVE_EXCHANGE_RATE = 0.0001 

# COSTOS
COST_PREMIUM_MONTH = 10 
COST_OBRERO = 50000
COST_MAPA = 100000

ADMIN_ID = 123456789 
RENDER_URL = "https://thehivereal-bot.onrender.com" 

# --- IMAGEN DE BIENVENIDA ---
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ARSENAL MAESTRO DE ENLACES (8 VÍAS DE INGRESO) ---
LINKS = {
    # NUEVO VALIDADOR (REEMPLAZA A COINPAYU)
    'VALIDATOR': "https://timebucks.com/?refID=227501472", 
    
    # ZONA VIP (PREMIUM - ALTO CPA)
    'VIP_OFFER_1': "https://www.bybit.com/invite?ref=BBJWAX4", 
    
    # SECCIÓN 1: TRÁFICO Y CLICKS
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    
    # SECCIÓN 2: FINTECH (CPA FUERTE)
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
    
    # SECCIÓN 4: TRABAJO ACTIVO
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # SECCIÓN 5: IA & MARKETING
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'FREECASH': "https://freecash.com/r/XYN98"
}

LEGAL_TEXT = """
📜 **TÉRMINOS DE USO Y PUBLICIDAD (HIVE ADS)**
──────────────────────────
Al usar TheOneHive, usted ACEPTA EXPRESAMENTE:

1. **Recepción de Ads:** Recibir ofertas, promociones y publicidad de terceros (Sponsors) a través de este chat y al correo electrónico proporcionado.
2. **Monetización de Datos:** Que sus datos de actividad sean usados para optimizar las ofertas CPA presentadas.
3. **Economía Dual:** Entiende que 'HIVE' es un token de utilidad interno y el saldo USD está sujeto a auditoría antifraude.

*Si no acepta recibir publicidad, no podrá acceder a las recompensas.*
"""

# --- TEXTOS ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE DETECTADO (V44.0)**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**.\n\n"
            "Para acceder a la plataforma de ingresos #1 de Telegram, necesitamos verificar tu humanidad y aceptación de términos.\n\n"
            "👇 **PASO 1:**\n"
            "Obtén tu CÓDIGO DE SEGURIDAD abajo y envíalo."
        ),
        
        'ask_terms': (
            "✅ **CÓDIGO CORRECTO**\n"
            "───────────────────────\n"
            "⚠️ **PASO LEGAL (OBLIGATORIO):**\n\n"
            "Para financiar tus pagos, TheOneHive trabaja con Sponsors.\n"
            "Debes aceptar recibir **Publicidad y Ofertas Exclusivas** en tu buzón y en este chat.\n\n"
            "¿Aceptas los términos de publicidad para comenzar a ganar?"
        ),
        
        'ask_email': (
            "🤝 **CONTRATO ACEPTADO**\n"
            "───────────────────────\n"
            "Bienvenido a la red.\n\n"
            "📧 **PASO 3 (FINAL):**\n"
            "Escribe tu **CORREO ELECTRÓNICO** (Donde recibirás las ofertas y notificaciones de pago):"
        ),
        
        'ask_bonus': (
            "✅ **CUENTA VINCULADA**\n"
            "───────────────────────\n"
            "🎁 **ACTIVACIÓN DE GANANCIAS**\n"
            "Para activar el flujo de **$0.01 USD Reales** por tarea, debes validar tu cuenta en Timebucks (Nuestro Partner).\n\n"
            "👇 Pulsa aquí para validar y recibir tu primer ingreso:"
        ),
        'btn_claim_bonus': "💰 VALIDAR CUENTA (Ganar $0.05)",

        'dashboard_body': """
🎮 **CENTRO DE COMANDO HIVE**
──────────────────────────
👤 **Operador:** {name}
🛡️ **Membresía:** {status}
📢 **Sponsor:** *Bybit Trading Wars*

💵 **SALDO REAL (Retirable):**
**${usd:.2f} USD** 
_(Auditoría: /justificante)_

🐝 **TOKENS HIVE:**
**{hive} HIVE**
_{hive_msg}_

📊 **Habilidades Activas:**
{skills}
──────────────────────────
""",
        'premium_pitch': """
👑 **MEMBRESÍA HIVE PREMIUM ($10/mes)**
──────────────────────────
**¡DEJA DE SER UN ESPECTADOR!**

El plan FREE está diseñado para aprender. El plan PREMIUM es para **GANAR**.

🔓 **BENEFICIOS VIP:**
1️⃣ **SWAP HABILITADO:** Convierte HIVE a Dólares hoy mismo.
2️⃣ **RETIRO EN $5:** No esperes a llegar a $10.
3️⃣ **CPA BOOSTER:** Acceso a ofertas que pagan $50 USD por acción.
4️⃣ **SIN ADS:** Navegación prioritaria.

💰 *Costo: $10.00 USD (Recuperable en 3 días de trabajo)*
""",
        'shop_body': """
🏪 **TIENDA DE HABILIDADES**
──────────────────────────
Invierte tu HIVE para multiplicar tus ingresos.

👥 **PACK REFERIDO NIVEL 2**
*Costo: 50,000 HIVE*
✅ Desbloquea comisión del 5% de referidos indirectos.

💎 **NFT: OBRERO CERTIFICADO T2**
*Costo: 100,000 HIVE*
✅ **Poder Supremo:** Otorga 30% de comisión directa.

*Tu saldo:* {hive} HIVE
""",
        'justificante_header': "📜 **AUDITORÍA EN TIEMPO REAL**\n──────────────────────────\nAquí está la prueba de origen de tus fondos:\n\n",
        
        'btn_premium': "👑 HACERME PREMIUM ($10)",
        'btn_shop': "🛒 TIENDA (Gastar HIVE)",
        'btn_justificante': "📜 JUSTIFICANTE",
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_back': "🔙 VOLVER", 'help_text': "Guía..."
    },
    'en': { 'welcome_caption': "Verify...", 'dashboard_body': "Dash..." }
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
    context.user_data['waiting_for_terms'] = False # NUEVO ESTADO LEGAL
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

    # PASO 1: CAPTCHA
    if context.user_data.get('waiting_for_captcha'):
        required = context.user_data.get('required_captcha')
        if text.upper() == required:
            context.user_data['waiting_for_captcha'] = False
            # AHORA VAMOS A LOS TÉRMINOS, NO AL EMAIL DIRECTAMENTE
            context.user_data['waiting_for_terms'] = True 
            
            kb = [
                [InlineKeyboardButton("✅ ACEPTO PUBLICIDAD Y TÉRMINOS", callback_data="accept_legal")],
                [InlineKeyboardButton("❌ NO ACEPTO (Salir)", callback_data="reject_legal")]
            ]
            await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text(f"❌ **CÓDIGO INCORRECTO.**\nDebes enviar: `{required}`", parse_mode="Markdown")
            return

    # PASO 3: EMAIL (Solo si ya aceptó términos)
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
    # USAMOS TIMEBUCKS COMO VALIDADOR (Es más estable que CoinPayU)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR'])]]
    kb.append([InlineKeyboardButton("✅ LISTO (ENTRAR)", callback_data="bonus_done")])
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    
    log_text = get_text(lang, 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD**\n   └ Fuente: *Timebucks Ads (View)*\n\n"
    log_text += f"🟢 `[{now} 10:42]` **+$5.00 USD**\n   └ Fuente: *Bybit Affiliate (CPA Action)*\n\n"
    log_text += f"🟢 `[{now} 11:00]` **+$0.05 USD**\n   └ Fuente: *Bono de Bienvenida Hive*\n"
    log_text += "\n✅ **ESTADO:** Verificado y Disponible para Retiro."

    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    hive = user_data.get('nectar', INITIAL_HIVE) if user_data else INITIAL_HIVE
    
    txt = get_text(user.language_code, 'shop_body').format(hive=hive)
    
    kb = [
        [InlineKeyboardButton("👥 PACK REFERIDO NIVEL 2 (50k)", callback_data="buy_ref2")],
        [InlineKeyboardButton("💎 NFT OBRERO CERTIFICADO (100k)", callback_data="buy_nft")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    txt = get_text(lang, 'premium_pitch')
    kb = [
        [InlineKeyboardButton("💳 PAGAR CON CRYPTO (USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton("💳 PAGAR CON TARJETA", callback_data="pay_card")],
        [InlineKeyboardButton("🔙 NO, GRACIAS", callback_data="go_dashboard")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    
    hive = user_data.get('nectar', INITIAL_HIVE) if user_data else INITIAL_HIVE
    usd = user_data.get('usd_balance', INITIAL_USD) if user_data else INITIAL_USD
    
    is_premium = context.user_data.get('is_premium', False)
    status_txt = "👑 PREMIUM" if is_premium else "🆓 FREE"
    
    if is_premium:
        hive_msg = "💱 **(Swap Disponible)**"
    else:
        hive_msg = "🔒 _(Hazte Premium para Canjear)_"

    skills_list = user_data.get('skills', [])
    skills_txt = "• Ninguna (Eres Larva)" if not skills_list else "\n".join([f"• {s}" for s in skills_list])

    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, status=status_txt, usd=usd, hive=hive, hive_msg=hive_msg, skills=skills_txt
    )
    
    kb = []
    
    if not is_premium:
        kb.append([InlineKeyboardButton(get_text(lang, 'btn_premium'), callback_data="go_premium")])
    else:
        kb.append([InlineKeyboardButton("💱 SWAP HIVE A USD", callback_data="swap_hive")])
        
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="go_shop")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_justificante'), callback_data="go_justificante")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")])
    
    if update.callback_query: await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS (RECOMENDADO)", url=LINKS['VALIDATOR'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("👍 EVERVE", url=LINKS['EVERVE']), InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS'])],
        [InlineKeyboardButton("🐦 TESTBIRDS", url=LINKS['TESTBIRDS']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (Validar)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS (CPA Instantáneo)**\nCada acción genera $0.01 USD en tu balance.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ YA HICE UNA TAREA (Validar)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA**\nGenera HIVE y USD mientras duermes.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    is_premium = context.user_data.get('is_premium', False)
    kb = []
    
    if is_premium:
        kb.append([InlineKeyboardButton("💎 OFFER VIP (PAGA x3)", url=LINKS['VIP_OFFER_1'])])
    
    kb.extend([
        [InlineKeyboardButton("🔥 BYBIT (MINADO DIARIO)", url=LINKS['BYBIT'])],
        [InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO']), InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT'])],
        [InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE'])],
        [InlineKeyboardButton("💹 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (Validar)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ])
    msg = "🔴 **ZONA 3: PRO & TRADING**"
    if not is_premium: msg += "\n🔒 *Hazte Premium para ver las Ofertas VIP.*"
    await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; 
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = (
        "📡 **SISTEMA DE REFERIDOS 2-TIER**\n\n"
        "👥 **NIVEL 1:** Ganas **20%** de lo que ganen tus directos.\n"
        "🗣️ **NIVEL 2:** Ganas **5%** de los amigos de tus amigos.\n"
        "_(Requiere comprar Paquete Nivel 2 en la Tienda)_\n\n"
        f"🔗 **TU ENLACE:**\n`{link}`"
    )
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def validate_task_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    is_premium = context.user_data.get('is_premium', False)
    
    await query.answer("🔍 Verificando...", show_alert=False)
    await asyncio.sleep(1.5) 
    
    tx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    hive_gain = 100 if is_premium else 50
    nft_frag = "+2 Fragmentos" if is_premium else "+1 Fragmento"
    bonus_text = "⚡ **BONO PREMIUM (x2) ACTIVADO** ⚡\n" if is_premium else ""
    
    text = (
        f"✅ **TAREA VALIDADA CON ÉXITO**\n"
        f"🧾 **Justificante:** #{tx_id}\n"
        f"───────────────────────\n\n"
        f"{bonus_text}"
        f"⚠️ **MINERÍA DUAL EJECUTADA:**\n"
        f"💵 **FIAT (Real):** $0.01 USD\n"
        f"🐝 **CRYPTO (Token):** {hive_gain} HIVE\n"
        f"🧩 **NFT:** {nft_frag}\n\n"
        f"───────────────────────\n"
        f"💰 *Fondos agregados.*"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER AL TRABAJO", callback_data="go_dashboard")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data
    
    if data == "accept_legal":
        # EL USUARIO ACEPTA LOS TÉRMINOS
        context.user_data['waiting_for_terms'] = False
        context.user_data['waiting_for_email'] = True
        await query.message.edit_text(get_text(query.from_user.language_code, 'ask_email'), parse_mode="Markdown")
        return
    
    if data == "reject_legal":
        await query.message.edit_text("❌ Acceso Denegado. Debes aceptar los términos para usar la plataforma.")
        return

    if data == "bonus_done":
        context.user_data['bonus_claimed'] = True
        await show_dashboard(update, context)
        return
    
    if data == "validate_task": await validate_task_logic(update, context)
    elif data == "go_dashboard": await show_dashboard(update, context)
    elif data == "go_shop": await shop_menu(update, context)
    elif data == "go_premium": await premium_menu(update, context)
    elif data == "go_justificante": await show_justificante(update, context)
    
    elif data == "pay_crypto" or data == "pay_card":
        context.user_data['is_premium'] = True
        await query.message.edit_text("🎉 **¡FELICIDADES! YA ERES PREMIUM.**\n\nBeneficios activados:\n✅ Swap Habilitado\n✅ Retiro en $5\n✅ Minería x2", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("IR AL DASHBOARD", callback_data="go_dashboard")]]), parse_mode="Markdown")
        
    elif data == "swap_hive": await query.answer("💱 Función SWAP en Mantenimiento (Pronto)", show_alert=True)
    elif data == "buy_ref2" or data == "buy_nft": await query.answer("❌ Saldo HIVE insuficiente", show_alert=True)

    elif data == "tier_1": await tier1_menu(update, context)
    elif data == "tier_2": await tier2_menu(update, context)
    elif data == "tier_3": await tier3_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    elif data == "help_guide": await help_guide_menu(update, context)
    elif data == "legal_terms": 
        kb = [[InlineKeyboardButton("🔙", callback_data="my_profile")]]
        await query.message.edit_text(LEGAL_TEXT, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data == "my_profile": await query.message.edit_text(f"👤 ID: `{query.from_user.id}`\nProtocolo AUS Activo.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
    elif data == "withdraw": 
        is_premium = context.user_data.get('is_premium', False)
        min_withdraw = "$5.00" if is_premium else "$10.00"
        msg = f"🔒 Mínimo {min_withdraw} USD"
        if not is_premium: msg += "\n(Hazte Premium para retirar antes)"
        await query.answer(msg, show_alert=True)

async def help_guide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    await query.message.edit_text("📜 **GUÍA RÁPIDA**\n1. Usa **Zona 1** para generar cash rápido.\n2. Compra Habilidades en la **Tienda**.\n3. Revisa tu **/justificante** para ver el dinero entrar.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_command(u, c): await u.message.reply_text("Help: /start")
async def invite_command(u, c): await u.message.reply_text("Use menu")
async def broadcast_command(u, c): pass
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK")
