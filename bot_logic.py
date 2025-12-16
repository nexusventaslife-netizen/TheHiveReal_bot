import logging
import asyncio
import random
import string
import datetime
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA (SUPREMACÍA AUS V50.0) ---

# 1. SEGURIDAD: Obtenemos IDs y Wallets de Render (Variables de Entorno)
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    ADMIN_ID = 0

# BILLETERA CRIPTO (USDT TRC20)
# Si no está en Render, mostrará un aviso de "Configurar" en lugar de fallar
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")

# LINK DE PAGO PAYPAL (NCP)
LINK_PAGO_GLOBAL = "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC"

# 2. ECONOMÍA & SALDOS
# El usuario empieza en 0. El bono se gana.
INITIAL_USD = 0.00      
INITIAL_HIVE = 500      
BONUS_REWARD = 0.05     # Recompensa por la primera tarea

# 3. COSTOS Y LÍMITES
COST_PREMIUM_MONTH = 10 
COST_OBRERO = 50000
COST_MAPA = 100000
COST_ENERGY_REFILL = 500 
MAX_ENERGY = 100

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

# --- TEXTOS MULTI-IDIOMA (MEJORADOS) ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🚀 **BIENVENIDO A THE ONE HIVE: TU PRIMER ACTIVO DIGITAL**\n"
            "──────────────────────────\n\n"
            "Hola, **{name}**. Has encontrado algo diferente. Esto no es un juego de tocar la pantalla sin sentido. **Esto es una Colmena de Ingresos.**\n\n"
            "🧬 **¿CÓMO FUNCIONA EL SISTEMA DUAL?**\n\n"
            "1️⃣ **Dinero Real ($USD):** Completas micro-tareas verificadas y ganas dólares retirables a tu Wallet o PayPal.\n"
            "2️⃣ **Néctar (HIVE):** Acumulas el token interno para subir de nivel y comprar **Licencias** que multiplican tus ganancias.\n\n"
            "🛡️ **TU PRIMERA MISIÓN:**\n"
            "Para activar tu billetera y asegurar que eres humano, necesitamos establecer un enlace seguro.\n\n"
            "👇 **COPIA TU CÓDIGO DE SEGURIDAD Y ENVÍALO AL CHAT:**"
        ),
        'ask_terms': (
            "✅ **ENLACE ESTABLECIDO**\n"
            "───────────────────────\n"
            "Antes de asignarte tu primera tarea pagada, acepta el **Protocolo de la Colmena**:\n\n"
            "• Usarás datos reales.\n"
            "• No usarás VPNs ni multicuentas.\n"
            "• Entiendes que el esfuerzo genera la recompensa.\n\n"
            "¿Aceptas el desafío?"
        ),
        'ask_email': (
            "🤝 **PROTOCOLO ACEPTADO**\n"
            "───────────────────────\n"
            "📧 **ÚLTIMO PASO DE CONFIGURACIÓN:**\n\n"
            "Escribe tu **CORREO ELECTRÓNICO** principal.\n"
            "*(Lo usaremos para notificarte cuando recibas un pago o un Airdrop)*."
        ),
        'ask_bonus': (
            "🎉 **¡CUENTA 100% ACTIVA!**\n"
            "───────────────────────\n"
            "Tu saldo actual es: **$0.00 USD**\n\n"
            "🎁 **TU PRIMERA TAREA PAGADA (BONO):**\n"
            "Hemos reservado un bono de **${bonus} USD** para ti. Para desbloquearlo, debes validar tu identidad en nuestro partner principal.\n\n"
            "1. Entra al enlace.\n"
            "2. Regístrate o valida.\n"
            "3. Pulsa 'YA LA COMPLETÉ' para recibir tus primeros $0.05."
        ),
        'btn_claim_bonus': "🚀 IR A LA MISIÓN (GANAR ${bonus})",
        
        'dashboard_body': """
📊 **PANEL DE CONTROL: {name}**
──────────────────────────
🏆 **Rango:** {status}
🔥 **Racha:** {streak} Días
⚡ **Energía:** {energy}/{max_energy}

💰 **BILLETERA REAL:**
**${usd:.2f} USD** _(Disponible para retirar)_

🐝 **BÓVEDA DE NÉCTAR:**
**{hive} HIVE**
_(Úsalo en la Tienda)_

🛠️ **INVENTARIO:**
{skills}
──────────────────────────
""",
        'premium_pitch': """
👑 **LICENCIA DE REINA: EL PODER TOTAL**
──────────────────────────
Deja de ser un obrero. Conviértete en la Realeza de la Colmena.

✅ **x2 en Todas las Tareas:** Gana el doble por el mismo esfuerzo.
✅ **Retiros Prioritarios:** Tus pagos salen primero.
✅ **Acceso al Mercado P2P:** Intercambia HIVE por USD con otros usuarios.

💎 **INVERSIÓN ÚNICA: $10.00 USD**
""",
        'payment_crypto_info': """
💎 **PAGO VÍA CRIPTO (USDT TRC20)**
──────────────────────────
Para activar tu licencia automáticamente, envía **10 USDT** a la siguiente dirección oficial:

`{wallet}`

⚠️ **IMPORTANTE:**
1. Usa solo la red **TRC20**.
2. Copia el **Hash de Transacción (TXID)** después de enviar.
3. Pégalo aquí abajo para validar.
""",
        'payment_card_info': """
💳 **PASARELA DE PAGO SEGURA (PAYPAL)**
──────────────────────────
**Estás comprando: Licencia de Reina (Vitalicia)**

El pago se procesa en una ventana segura de PayPal. TheOneHive no ve tus datos bancarios.

👇 **Pulsa el botón "PAGAR AHORA" para abrir la pasarela:**
""",
        'shop_body': """
🏪 **MERCADO DE RECURSOS**
──────────────────────────
*Saldo:* {hive} HIVE

⚡ **RECARGAR ENERGÍA (500 HIVE)**
Recupera 100 puntos para seguir minando hoy.

👑 **LICENCIA DE REINA ($10 USD)**
Multiplicador x2 permanente y retiros rápidos.

👷 **CERTIFICADO DE MAESTRO (50k HIVE)**
Desbloquea tareas de alto valor (Tier 2).

💎 **NFT DE LA COLMENA (100k HIVE)**
Te otorga 30% de comisión de referidos de por vida.
""",
        'justificante_header': "📜 **HISTORIAL DE INGRESOS (TRANSPARENCIA)**\n──────────────────────────\nAuditoría en tiempo real de la Colmena:\n\n",
        
        'btn_shop': "🛒 TIENDA / MEJORAS",
        'btn_justificante': "📜 TRANSPARENCIA",
        'btn_t1': "🟢 TAREAS (Clicks)", 'btn_t2': "🟡 PASIVO (AFK)", 'btn_t3': "🔴 PRO (Trading)",
        'btn_back': "🔙 VOLVER", 'btn_withdraw': "💸 RETIRAR SALDO", 'btn_team': "👥 MI EQUIPO", 'btn_profile': "👤 MI PERFIL"
    },
    'en': { 'welcome_caption': "Verify...", 'dashboard_body': "Dash..." }
}

# --- UTILIDADES ---
def get_text(lang_code, key, **kwargs):
    lang = 'en'
    if lang_code and lang_code.startswith('es'): lang = 'es'
    text = TEXTS[lang].get(key, TEXTS['en'].get(key, key))
    try:
        return text.format(**kwargs)
    except:
        return text

def generate_captcha():
    return f"HIVE-{random.randint(100, 999)}"

async def save_user_data(user_id, data):
    """Guarda los datos usando la función add_user del db (que maneja updates)"""
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
    
    # Mensaje de bienvenida detallado
    full_caption = get_text(lang, 'welcome_caption', name=user.first_name)
    code_txt = f"\n\n🔑 **CÓDIGO:** `{captcha_code}`"
    
    try: 
        await update.message.reply_photo(photo=IMG_BEEBY, caption=full_caption + code_txt, parse_mode="Markdown")
    except Exception as e: 
        logger.error(f"Error img: {e}")
        await update.message.reply_text(full_caption + code_txt, parse_mode="Markdown")

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
            "👑 **¡PAGO RECIBIDO!**\n\nTu Licencia de Reina se está validando en la Blockchain. Se activará en breve.",
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
                [InlineKeyboardButton("✅ ACEPTO EL PROTOCOLO", callback_data="accept_legal")],
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
    # Saldo es 0 hasta que completen esto
    txt = get_text(lang, 'ask_bonus', bonus=BONUS_REWARD)
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_claim_bonus', bonus=BONUS_REWARD), url=LINKS['VALIDATOR_MAIN'])],
        [InlineKeyboardButton("✅ YA LA COMPLETÉ", callback_data="bonus_done")]
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    
    hive = user_data.get('nectar', INITIAL_HIVE)
    usd = user_data.get('usd_balance', INITIAL_USD)
    
    streak = await check_daily_streak(user.id)
    energy = user_data.get('energy', MAX_ENERGY)
    
    is_premium = context.user_data.get('is_premium', False)
    status_txt = "👑 REINA" if is_premium else "🐛 OBRERA"
    
    skills_list = user_data.get('skills', [])
    skills_txt = "• Ninguna" if not skills_list else "\n".join([f"• {s}" for s in skills_list])

    body = get_text(lang, 'dashboard_body', 
        name=user.first_name, 
        status=status_txt, 
        usd=usd, 
        hive=hive, 
        skills=skills_txt,
        streak=streak,
        energy=energy,
        max_energy=MAX_ENERGY
    )
    
    if streak > 3: body += "\n🚀 *¡Bono de Racha x1.5 activo!*"
    
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
        [InlineKeyboardButton("💹 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
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
        [InlineKeyboardButton("💳 PAGAR CON PAYPAL", callback_data="pay_card_select")],
        [InlineKeyboardButton("🔙 CANCELAR", callback_data="go_shop")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def payment_detail_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, method):
    lang = update.effective_user.language_code
    
    if method == "crypto":
        # Usamos la variable de entorno o el mensaje de error si no existe
        txt = get_text(lang, 'payment_crypto_info').format(wallet=CRYPTO_WALLET_USDT)
        kb = [[InlineKeyboardButton("✅ YA ENVIÉ (ENVIAR HASH)", callback_data="confirm_payment_crypto")]]
    else:
        # PAGO CON BOTÓN NATIVO PAYPAL
        txt = get_text(lang, 'payment_card_info')
        
        kb = [
            # Botón con URL directa (Abre navegador del usuario, seguro y limpio)
            [InlineKeyboardButton("💳 PAGAR AHORA (SECURE CHECKOUT)", url=LINK_PAGO_GLOBAL)],
            [InlineKeyboardButton("✅ YA PAGUÉ (CONFIRMAR)", callback_data="confirm_payment_card")]
        ]

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

    # Lógica de BONO MEJORADA: Suma el dinero en tiempo real
    if data == "bonus_done":
        user_data = await db.get_user(user_id)
        if not context.user_data.get('bonus_claimed'):
            context.user_data['bonus_claimed'] = True
            # Sumar el dinero real
            new_balance = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
            user_data['usd_balance'] = new_balance
            await save_user_data(user_id, user_data)
            
            await query.answer(f"✅ ¡Bono de ${BONUS_REWARD} acreditado a tu billetera!", show_alert=True)
        else:
            await query.answer("⚠️ Ya reclamaste este bono.", show_alert=True)
            
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

    await update.message.reply_text(f"📢 Mensaje programado:\n\n{msg}\n\n(Implementar bucle de envío en background)")
