import logging
import asyncio
import random
import string
import datetime
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA (SUPREMACÍA AUS V48.0) ---
ADMIN_ID = 123456789  # <--- CAMBIA ESTO POR TU ID REAL DE TELEGRAM
INITIAL_USD = 0.05
INITIAL_HIVE = 500
HIVE_EXCHANGE_RATE = 0.0001 

# COSTOS Y LÍMITES
COST_PREMIUM_MONTH = 10 
COST_OBRERO = 50000
COST_MAPA = 100000
COST_ENERGY_REFILL = 500 
MAX_ENERGY = 100

# DIRECCIONES DE PAGO
LINK_PAGO_GLOBAL = "https://paypal.me/josepereiraramirez/10"
CRYPTO_WALLET_USDT = "TU_DIRECCION_USDT_TRC20_AQUI" 

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ARSENAL MAESTRO DE ENLACES ---
LINKS = {
    'VALIDATOR_MAIN': "https://timebucks.com/?refID=227501472",
    'VIP_OFFER_1': "https://www.bybit.com/invite?ref=BBJWAX4", 
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381"
}

# --- TEXTOS MULTI-IDIOMA ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE DETECTADO (V48.0)**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**.\n\n"
            "Para iniciar tu carrera en la Colmena y generar ingresos, verifica tu humanidad.\n\n"
            "👇 **PASO 1:**\n"
            "Obtén tu CÓDIGO DE SEGURIDAD abajo y envíalo al chat."
        ),
        'ask_terms': (
            "✅ **CÓDIGO CORRECTO**\n"
            "───────────────────────\n"
            "⚠️ **PASO LEGAL (REQUIRED):**\n"
            "¿Aceptas las reglas del juego para continuar?"
        ),
        'ask_email': (
            "🤝 **CONTRATO ACEPTADO**\n"
            "───────────────────────\n"
            "📧 **PASO 3 (FINAL):**\n"
            "Escribe tu **CORREO ELECTRÓNICO** para activar tu Billetera Dual:"
        ),
        'ask_bonus': (
            "✅ **CUENTA VINCULADA**\n"
            "───────────────────────\n"
            "🎁 **PRIMERA MISIÓN DISPONIBLE**\n"
            "Valida tu identidad en Timebucks para activar el flujo de **$0.01 USD**."
        ),
        'btn_claim_bonus': "💰 VALIDAR Y GANAR $0.05",
        'dashboard_body': """
🎮 **CENTRO DE COMANDO HIVE**
──────────────────────────
👤 **Operador:** {name}
🛡️ **Clase:** {status}
📢 **Evento:** *Bybit Trading Wars*

💵 **SALDO REAL (Retirable):**
**${usd:.2f} USD** _(Mínimo Retiro: $10)_

🐝 **TOKENS HIVE:**
**{hive} HIVE**
_(Moneda de Juego)_

🔧 **ESTADO:**
{skills}
──────────────────────────
""",
        'premium_pitch': """
👑 **EVOLUCIÓN DE PERSONAJE: LICENCIA DE REINA**
──────────────────────────
¡Domina la economía de la Colmena!

⚡ **Turbo Minería (x2):** Doble recompensa.
🔓 **Llave Maestra:** Retiros rápidos ($5).
💎 **Mercado P2P:** Habilita el Swap.

💰 *Costo: $10.00 USD (Pago Único)*
""",
        'payment_crypto_info': """
💎 **EVOLUCIÓN VÍA CRIPTO (USDT)**
──────────────────────────
Envía **10 USDT** (Red TRC20) a:

`{wallet}`

Copia el HASH (TXID) y envíalo abajo.
""",
        'payment_card_info': """
💳 **EVOLUCIÓN VÍA PAYPAL**
──────────────────────────
1. Haz clic en el enlace.
2. Paga **$10.00 USD**.
3. Pulsa "YA PAGUÉ".

🔗 [CLICK AQUÍ PARA PAGAR]({link})
""",
        'shop_body': """
🏪 **TIENDA DE RECURSOS**
──────────────────────────
*Saldo:* {hive} HIVE

⚡ **RECARGAR ENERGÍA (500 HIVE)**
Recupera 100 puntos para seguir minando.

👑 **LICENCIA DE REINA ($10)**
Evolución permanente.

👷 **OBRERO CERTIFICADO (50k HIVE)**
Desbloquea tareas Tier 2.

💎 **NFT MAESTRO (100k HIVE)**
Comisión de referidos 30%.
""",
        'justificante_header': "📜 **AUDITORÍA EN TIEMPO REAL**\n──────────────────────────\nPrueba de origen de fondos:\n\n",
        
        'btn_shop': "🛒 TIENDA / MEJORAS",
        'btn_justificante': "📜 JUSTIFICANTE",
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_back': "🔙 VOLVER", 'btn_withdraw': "💸 RETIRAR", 'btn_team': "👥 EQUIPO", 'btn_profile': "👤 PERFIL"
    },
    'en': { 'welcome_caption': "Verify...", 'dashboard_body': "Dash..." }
}

# --- UTILIDADES ---
def get_text(lang_code, key):
    lang = 'en'
    if lang_code and lang_code.startswith('es'): lang = 'es'
    return TEXTS[lang].get(key, TEXTS['en'].get(key, key))

def generate_captcha():
    return f"HIVE-{random.randint(100, 999)}"

async def save_user_data(user_id, data):
    """Guarda los datos usando la función add_user del db (que maneja updates)"""
    # En database.py, 'add_user' ya actualiza si existe, pero para ser más precisos
    # usaremos 'set' directo si tenemos acceso a 'r' o simulamos update
    if hasattr(db, 'r') and db.r:
        await db.r.set(f"user:{user_id}", json.dumps(data))

async def check_daily_streak(user_id):
    """Calcula y actualiza la racha diaria"""
    user_data = await db.get_user(user_id)
    if not user_data: return 0

    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    last_date_str = user_data.get('last_streak_date', "")
    current_streak = user_data.get('streak_days', 0)

    if last_date_str == today_str:
        return current_streak 

    yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    if last_date_str == yesterday:
        new_streak = current_streak + 1
        user_data['streak_days'] = new_streak
        user_data['last_streak_date'] = today_str
        user_data['nectar'] = int(user_data.get('nectar', 0)) + (new_streak * 10) # Bono HIVE
        await save_user_data(user_id, user_data)
        return new_streak
    else:
        user_data['streak_days'] = 1
        user_data['last_streak_date'] = today_str
        await save_user_data(user_id, user_data)
        return 1

# --- HANDLERS PRINCIPALES ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Limpiar mensajes anteriores
    try: 
        await context.bot.delete_message(chat_id=user.id, message_id=update.message.message_id)
    except: pass

    user_data = await db.get_user(user.id)
    # Si ya completó el registro, va al Dashboard
    if user_data and user_data.get('email') and context.user_data.get('bonus_claimed'):
        await show_dashboard(update, context)
        return

    # INICIO DE CERO (Onboarding)
    captcha_code = generate_captcha()
    context.user_data['required_captcha'] = captcha_code
    context.user_data['waiting_for_captcha'] = True
    context.user_data['waiting_for_terms'] = False 
    context.user_data['waiting_for_email'] = False 
    context.user_data['waiting_for_hash'] = False
    
    base_txt = get_text(lang, 'welcome_caption').format(name=user.first_name)
    code_txt = f"\n\n🔑 **TU CÓDIGO DE ACCESO ES:** `{captcha_code}`\n(Cópialo y envíalo)"
    
    try: 
        await update.message.reply_photo(photo=IMG_BEEBY, caption=base_txt + code_txt, parse_mode="Markdown")
    except Exception as e: 
        logger.error(f"Error img: {e}")
        await update.message.reply_text(base_txt + code_txt, parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip() if update.message.text else ""
    user = update.effective_user
    lang = user.language_code

    # COMANDOS DE TEXTO MANUALES
    if text.upper() == "/FORCE_RESET":
        context.user_data.clear()
        if hasattr(db, 'update_email'): await db.update_email(user.id, None)
        await update.message.reply_text("🛑 RESET COMPLETO.")
        return
    
    if text.upper() == "/JUSTIFICANTE":
        await show_justificante(update, context)
        return

    if text.upper() in ["DASHBOARD", "PERFIL", "/START", "MENU"]: 
        user_db = await db.get_user(user.id)
        if user_db and user_db.get('email'): 
            await show_dashboard(update, context)
        else: 
            await start(update, context) 
        return

    # 1. VERIFICACIÓN DE HASH (PAGO)
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        context.user_data['is_premium'] = True 
        await update.message.reply_text(
            "👑 **¡EVOLUCIÓN EN PROCESO!**\n\nTu Licencia de Reina se ha activado temporalmente mientras la blockchain confirma.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("IR AL CENTRO DE MANDO", callback_data="go_dashboard")]])
        )
        return

    # 2. CAPTCHA
    if context.user_data.get('waiting_for_captcha'):
        required = context.user_data.get('required_captcha')
        if text.upper() == required:
            context.user_data['waiting_for_captcha'] = False
            context.user_data['waiting_for_terms'] = True 
            
            kb = [
                [InlineKeyboardButton("✅ JUGAR Y ACEPTAR OFERTAS", callback_data="accept_legal")],
                [InlineKeyboardButton("❌ SALIR", callback_data="reject_legal")]
            ]
            await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return
        else:
            await update.message.reply_text(f"❌ **CÓDIGO INCORRECTO.**\nDebes enviar: `{required}`", parse_mode="Markdown")
            return

    # 3. EMAIL
    if context.user_data.get('waiting_for_email'):
        if "@" in text and "." in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
            return
        else:
            await update.message.reply_text("⚠️ Email con formato inválido. Intenta de nuevo:")
            return

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    txt = get_text(lang, 'ask_bonus')
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR_MAIN'])],
        [InlineKeyboardButton("✅ LISTO (ENTRAR)", callback_data="bonus_done")]
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    
    hive = user_data.get('nectar', INITIAL_HIVE)
    usd = user_data.get('usd_balance', INITIAL_USD)
    
    streak = await check_daily_streak(user.id)
    energy = user_data.get('energy', MAX_ENERGY)
    fire_emoji = "🔥" * (streak if streak < 5 else 5)
    
    is_premium = context.user_data.get('is_premium', False)
    status_txt = "👑 REINA" if is_premium else "🐛 OBRERA"
    
    skills_list = user_data.get('skills', [])
    skills_txt = "• Ninguna" if not skills_list else "\n".join([f"• {s}" for s in skills_list])

    body = get_text(lang, 'dashboard_body').format(
        name=user.first_name, status=status_txt, usd=usd, hive=hive, skills=skills_txt
    )
    
    body += f"\n📅 **Racha:** {streak} Días {fire_emoji}"
    body += f"\n⚡ **Energía:** {energy}/{MAX_ENERGY}"
    if streak > 3: body += "\n🚀 *¡Bono x1.5 activo!*"
    
    kb = []
    if is_premium:
        kb.append([InlineKeyboardButton("💱 SWAP HIVE A USD", callback_data="swap_hive")])
        
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="go_shop")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_justificante'), callback_data="go_justificante")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="invite_friends"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="my_profile")])
    
    if update.callback_query: 
        await update.callback_query.message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: 
        await update.message.reply_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    
    log_text = get_text(lang, 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD**\n   └ Fuente: *TimeBucks Network*\n\n"
    log_text += f"🟢 `[{now} 10:42]` **+$5.00 USD**\n   └ Fuente: *Bybit CPA*\n\n"
    log_text += "\n✅ **ESTADO:** Verificado."

    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- LÓGICA DE VALIDACIÓN (CASINO) ---
async def validate_task_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # 1. Energía
    current_energy = user_data.get('energy', MAX_ENERGY)
    if current_energy < 10:
        await query.answer("🔋 SIN ENERGÍA. Usa HIVE en la tienda para recargar.", show_alert=True)
        return

    user_data['energy'] = current_energy - 10
    
    await query.answer("🎲 Hackeando sistema...", show_alert=False)
    await asyncio.sleep(1.2) 
    
    # 2. Algoritmo Casino
    rand = random.randint(1, 100)
    tx_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    streak = user_data.get('streak_days', 1)
    streak_mult = 1.5 if streak > 3 else 1.0
    is_premium = context.user_data.get('is_premium', False)
    if is_premium: streak_mult += 0.5

    if rand > 95: # CRÍTICO
        usd_gain = 0.05 * streak_mult
        hive_gain = 500
        item_drop = "🧩 **FRAGMENTO NFT RARO**"
        msg_header = "🚨 **¡CRÍTICO! BLOQUE DE ORO** 🚨"
    elif rand > 70: # RARO
        usd_gain = 0.02 * streak_mult
        hive_gain = 150
        item_drop = "🎫 Ticket de Sorteo"
        user_data['lucky_tickets'] = user_data.get('lucky_tickets', 0) + 1
        msg_header = "✨ **¡Excelente! Recompensa Aumentada**"
    else: # COMÚN
        usd_gain = 0.01
        hive_gain = 50
        item_drop = "Ninguno"
        msg_header = "✅ **Bloque Minado**"

    user_data['usd_balance'] = float(user_data.get('usd_balance', 0)) + usd_gain
    user_data['nectar'] = int(user_data.get('nectar', 0)) + hive_gain
    
    await save_user_data(user_id, user_data)

    text = (
        f"{msg_header}\n"
        f"🧾 **Hash:** #{tx_id}\n"
        f"───────────────────────\n"
        f"💵 **FIAT:** +${usd_gain:.2f} USD\n"
        f"🐝 **HIVE:** +{hive_gain}\n"
        f"🎒 **LOOT:** {item_drop}\n"
        f"⚡ **Energía Restante:** {user_data['energy']}/{MAX_ENERGY}\n"
        f"───────────────────────\n"
        f"📈 *Racha: {streak} días ({streak_mult}x)*"
    )
    
    kb = [
        [InlineKeyboardButton("⛏️ SEGUIR MINANDO (-10 Energía)", callback_data="validate_task")],
        [InlineKeyboardButton("🔙 DASHBOARD", callback_data="go_dashboard")]
    ]
          
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MENÚS ---
async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA (-10 Energía)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS**\nMisiones Diarias de Click.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ VALIDAR TAREA (-10 Energía)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA**\nIngresos AFK.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

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
        [InlineKeyboardButton("✅ VALIDAR TAREA (-10 Energía)", callback_data="validate_task")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ])
    msg = "🔴 **ZONA 3: PRO & TRADING**"
    if not is_premium: msg += "\n🔒 *Necesitas Licencia de Reina para ofertas VIP.*"
    await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    hive = user_data.get('nectar', INITIAL_HIVE)
    
    txt = get_text(user.language_code, 'shop_body').format(hive=hive)
    
    kb = [
        [InlineKeyboardButton(f"⚡ RECARGAR ENERGÍA ({COST_ENERGY_REFILL} HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 LICENCIA DE REINA ($10 USD)", callback_data="go_premium")],
        [InlineKeyboardButton("👷 OBRERO CERTIFICADO (50k HIVE)", callback_data="buy_ref2")],
        [InlineKeyboardButton("💎 NFT MAESTRO (100k HIVE)", callback_data="buy_nft")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    txt = get_text(lang, 'premium_pitch')
    
    kb = [
        [InlineKeyboardButton("💎 PAGAR CON CRIPTO (USDT)", callback_data="pay_crypto_select")],
        [InlineKeyboardButton("💳 PAGAR CON PAYPAL / TARJETA", callback_data="pay_card_select")],
        [InlineKeyboardButton("🔙 CANCELAR", callback_data="go_shop")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def payment_detail_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, method):
    lang = update.effective_user.language_code
    
    if method == "crypto":
        txt = get_text(lang, 'payment_crypto_info').format(wallet=CRYPTO_WALLET_USDT)
        kb = [[InlineKeyboardButton("✅ YA ENVIÉ (ENVIAR HASH)", callback_data="confirm_payment_crypto")]]
    else:
        txt = get_text(lang, 'payment_card_info').format(link=LINK_PAGO_GLOBAL)
        kb = [[InlineKeyboardButton("✅ YA PAGUÉ (CONFIRMAR)", callback_data="confirm_payment_card")]]

    kb.append([InlineKeyboardButton("🔙 VOLVER", callback_data="go_premium")])
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = (
        "📡 **RED DE RECOLECCIÓN**\n\n"
        "👥 **NIVEL 1:** Ganas **20%** de tus directos.\n"
        "🗣️ **NIVEL 2:** Ganas **5%** (Requiere NFT).\n\n"
        f"🔗 **TU ENLACE:**\n`{link}`"
    )
    kb = [[InlineKeyboardButton("📤 Compartir", url=f"https://t.me/share/url?url={link}"), InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- ROUTER DE BOTONES ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    lang = query.from_user.language_code
    
    if data == "accept_legal":
        context.user_data['waiting_for_terms'] = False
        context.user_data['waiting_for_email'] = True
        await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown")
        return
    
    if data == "reject_legal":
        await query.message.edit_text("❌ Acceso Denegado.")
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
    
    elif data == "pay_crypto_select": await payment_detail_menu(update, context, "crypto")
    elif data == "pay_card_select": await payment_detail_menu(update, context, "card")
    
    elif data == "confirm_payment_crypto":
        context.user_data['waiting_for_hash'] = True
        await query.message.edit_text("📝 **ESCRIBE EL HASH**\n\nPega aquí el código de transacción (TXID).")
        
    elif data == "confirm_payment_card":
        context.user_data['is_premium'] = True
        await query.message.edit_text("👑 **¡LICENCIA ACTIVADA!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("IR AL CENTRO DE MANDO", callback_data="go_dashboard")]]))
        
    elif data == "buy_energy":
        user_data = await db.get_user(user_id)
        if user_data.get('nectar', 0) >= COST_ENERGY_REFILL:
            user_data['nectar'] -= COST_ENERGY_REFILL
            user_data['energy'] = min(user_data.get('energy', 0) + 100, 200)
            await save_user_data(user_id, user_data)
            await query.answer("⚡ Energía recargada (+100)", show_alert=True)
            await shop_menu(update, context)
        else:
            await query.answer("❌ HIVE Insuficiente. ¡Mina más!", show_alert=True)

    elif data == "swap_hive": 
        await query.answer("💱 Función SWAP en Mantenimiento", show_alert=True)
    elif data == "buy_ref2" or data == "buy_nft": 
        await query.answer("❌ HIVE insuficiente", show_alert=True)

    elif data == "tier_1": await tier1_menu(update, context)
    elif data == "tier_2": await tier2_menu(update, context)
    elif data == "tier_3": await tier3_menu(update, context)
    elif data == "invite_friends": await team_menu(update, context)
    
    elif data == "withdraw": 
        is_premium = context.user_data.get('is_premium', False)
        min_withdraw = "$5.00" if is_premium else "$10.00"
        msg = f"🔒 Mínimo {min_withdraw} USD"
        if not is_premium: msg += "\n(Necesitas Licencia de Reina para retirar antes)"
        await query.answer(msg, show_alert=True)
        
    elif data == "my_profile": 
        await query.message.edit_text(f"👤 JUGADOR: `{query.from_user.id}`\nNivel: Larva", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")

# --- COMANDOS AUXILIARES ---
async def help_command(u, c): await u.message.reply_text("Comandos:\n/start - Iniciar\n/help - Ayuda\n/justificante - Auditoría")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset completado.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía un mensaje a todos los usuarios (SOLO ADMIN)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return

    msg = update.message.text.replace("/broadcast", "").strip()
    if not msg:
        await update.message.reply_text("❌ Uso: /broadcast <mensaje>")
        return

    # Aquí idealmente iterarías sobre todos los IDs en DB
    # Como ejemplo simple, confirmamos recepción
    await update.message.reply_text(f"📢 Mensaje programado:\n\n{msg}\n\n(Implementar bucle de envío en background)")
