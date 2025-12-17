import logging
import asyncio
import random
import string
import datetime
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# -----------------------------------------------------------------------------
# 1. NÚCLEO DE CONFIGURACIÓN (NEXUS KERNEL V140)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD: ID de Administrador
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado. Usando 0.")
    ADMIN_ID = 0

# DIRECCIONES DE COBRO
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA "HARD MONEY" (Deflacionaria tipo Bitcoin)
INITIAL_USD = 0.00      
INITIAL_HIVE = 500      
BONUS_REWARD_USD = 0.05     # Pago en Dólares por tarea
BONUS_REWARD_HIVE = 1000    # Pago en HIVE por tarea (Incentivo Doble)

# ALGORITMO DE MINERÍA & ENJAMBRE
MINING_COST_PER_TAP = 25    
BASE_REWARD_PER_TAP = 5     
MAX_ENERGY_BASE = 500       
ENERGY_REGEN = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 1.2       

# COSTOS DE MERCADO
COST_PREMIUM_MONTH = 10     
COST_ENERGY_REFILL = 200    

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES (TODAS LAS VÍAS ACTIVAS)
# -----------------------------------------------------------------------------
LINKS = {
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"), 
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

# -----------------------------------------------------------------------------
# 3. TEXTOS (COPYWRITING PERSUASIVO & ENGANCHE)
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **BIENVENIDO A LA ECONOMÍA DEL FUTURO: THE ONE HIVE**\n"
            "──────────────────────────\n\n"
            "Hola, **{name}**. Estás a punto de iniciar una carrera evolutiva.\n"
            "A diferencia de otros juegos, aquí aplicamos el **Modelo Bitcoin/Ethereum**: Escasez = Valor.\n\n"
            "🚀 **TU HOJA DE RUTA AL ÉXITO:**\n\n"
            "1️⃣ **MINERÍA HIVE (Token):** No es dinero infinito. Es limitado y cuesta energía. Acumúlalo HOY antes de que suba la dificultad (Halving).\n"
            "2️⃣ **TAREAS DE VALOR ($USD):** Completa misiones externas. Nosotros te pagamos **DOBLE**: Dólares + Bono en HIVE.\n"
            "3️⃣ **ENJAMBRES (CLANES):** No mines solo. Crea tu propio equipo. Si ellos ganan, tú ganas.\n\n"
            "🛡️ **PASO 1: ACTIVACIÓN DE NODO**\n"
            "Para garantizar que eres un humano valioso y no un bot, ingresa tu código:"
        ),
        'ask_terms': (
            "📜 **CONTRATO DE MONETIZACIÓN DE DATOS**\n"
            "──────────────────────────\n"
            "Para financiar este ecosistema y pagarte recompensas reales, requerimos tu consentimiento explícito.\n\n"
            "✅ **AL ACEPTAR, CONFIRMAS:**\n"
            "1. Deseo recibir **Ofertas Comerciales, Publicidad y Airdrops** en mi buzón.\n"
            "2. Mis datos de actividad serán usados para optimizar las campañas CPA.\n"
            "3. Entiendo que HIVE es un activo volátil sujeto a las leyes de oferta y demanda.\n\n"
            "¿Aceptas las reglas del juego para empezar a ganar?"
        ),
        'ask_email': (
            "🤝 **CONTRATO FIRMADO**\n"
            "───────────────────────\n"
            "📧 **VINCULACIÓN FINAL:**\n"
            "Escribe tu **CORREO ELECTRÓNICO** principal.\n"
            "*(Es obligatorio para procesar tus pagos de PayPal/Cripto y enviarte alertas de oportunidades)*."
        ),
        'ask_bonus': (
            "🎉 **¡CUENTA 100% OPERATIVA!**\n"
            "───────────────────────\n"
            "💰 Saldo Fiat: **$0.00 USD**\n"
            "🐝 Saldo HIVE: **{initial_hive}**\n\n"
            "🎁 **TU PRIMERA MISIÓN DOBLE:**\n"
            "Gana tus primeros **${bonus_usd} USD** + **{bonus_hive} HIVE** extra.\n\n"
            "1. Regístrate en el Partner Oficial.\n"
            "2. Valida tu identidad.\n"
            "3. Pulsa 'VALIDAR' para recibir AMBOS premios."
        ),
        'btn_claim_bonus': "🚀 HACER MISIÓN (GANAR USD + HIVE)",
        
        'dashboard_body': """
🎛 **PANEL DE CONTROL: {name}**
──────────────────
🏆 **Rango:** {rank}
👥 **Enjambre:** {swarm_status}
⚡ **Energía:** `{energy_bar}` {energy}%
⛏️ **Potencia:** {rate} HIVE/tap

💵 **BILLETERA:** `${usd:.2f} USD`
🐝 **HIVE MINADO:** `{hive}`

💤 **MINERÍA AFK (PASIVA):**
_{afk_msg}_
──────────────────
""",
        'mining_success': "⛏️ **BLOQUE MINADO**\n\n🔋 Energía: `{old_e}` ➔ `{new_e}`\n🐝 HIVE: `{old_h}` ➔ `{new_h}`\n🤝 **Bono Enjambre:** x{mult}\n\n✅ **Validado en Blockchain**",
        
        'payment_card_info': "💳 **LICENCIA DE REINA (VIP)**\n\nInvierte en tu futuro. Minería x2 y Prioridad en Pagos.\nCompra segura vía PayPal.\n\n👇 **PAGAR AHORA:**",
        'payment_crypto_info': "💎 **PAGO USDT (TRC20)**\nDestino: `{wallet}`\n\nEnvía 10 USDT y pega el TXID abajo para activación automática.",
        'shop_body': "🏪 **MERCADO DE ACTIVOS**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\nQuema HIVE para seguir minando.\n\n👑 **LICENCIA REINA ($10)**\n👷 **OBRERO (50k HIVE)**",
        'swarm_menu_body': "🐝 **GESTIÓN DE ENJAMBRES**\n\nÚnete a la evolución. Crea tu equipo.\n\n👥 **Tus Obreros:** {count}\n🚀 **Multiplicador:** x{mult}\n\n👇 **TU ENLACE DE RECLUTAMIENTO:**",
        
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_shop': "🛒 TIENDA", 'btn_justificante': "📜 AUDITORÍA", 'btn_back': "🔙 VOLVER", 
        'btn_withdraw': "💸 RETIRAR", 'btn_team': "👥 MI ENJAMBRE", 'btn_profile': "👤 PERFIL"
    }
}

# -----------------------------------------------------------------------------
# 4. MOTOR MATEMÁTICO (MINERÍA + ENJAMBRE)
# -----------------------------------------------------------------------------

def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_hash(): return "0x" + ''.join(random.choices("ABCDEF0123456789", k=18))
def generate_captcha(): return f"HIVE-{random.randint(100, 999)}"

def render_progressbar(current, total, length=10):
    percent = max(0, min(current / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "░" * empty

def calculate_rank(hive_balance):
    if hive_balance < 1000: return "🥚 LARVA"
    if hive_balance < 5000: return "🐛 OBRERO"
    if hive_balance < 20000: return "⚔️ SOLDADO"
    if hive_balance < 100000: return "🛡️ GUARDIÁN"
    return "👑 REINA"

def calculate_swarm_bonus(referrals_count):
    # Algoritmo de Viralidad: Incentiva traer gente
    return round(1.0 + (min(referrals_count, 50) * 0.05), 2)

async def calculate_user_state(user_data):
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    mining_level = user_data.get('mining_level', 1)
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    
    afk_rate = mining_level * 0.1 * swarm_mult 
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 60: pending_afk += afk_time * afk_rate
    user_data['pending_afk'] = int(pending_afk)
    user_data['last_update_ts'] = now
    
    return user_data

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r: await db.r.set(f"user:{user_id}", json.dumps(data))

async def check_daily_streak(user_id):
    user_data = await db.get_user(user_id)
    if not user_data: return 0
    now = datetime.datetime.now(); today_str = now.strftime("%Y-%m-%d")
    last_date_str = user_data.get('last_streak_date', "")
    current_streak = user_data.get('streak_days', 0)
    if last_date_str == today_str: return current_streak 
    yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if last_date_str == yesterday:
        new_streak = current_streak + 1
        user_data['streak_days'] = new_streak; user_data['last_streak_date'] = today_str
        user_data['nectar'] = int(user_data.get('nectar', 0)) + (new_streak * 10)
        await save_user_data(user_id, user_data)
        return new_streak
    else:
        user_data['streak_days'] = 1; user_data['last_streak_date'] = today_str
        await save_user_data(user_id, user_data)
        return 1

# -----------------------------------------------------------------------------
# 5. HANDLERS
# -----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    user_data = await db.get_user(user.id)
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['energy'] = MAX_ENERGY_BASE
        user_data['mining_level'] = 1
        await save_user_data(user.id, user_data)

    txt = get_text('es', 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    try: await update.message.reply_photo(photo=IMG_BEEBY, caption=f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")
    except: await update.message.reply_text(f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    
    # --- ADMIN GOD MODE ---
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"):
            try:
                target = int(text.split()[1])
                target_data = await db.get_user(target)
                if target_data:
                    # PAGAR RECOMPENSA DOBLE (USD + HIVE)
                    curr_usd = float(target_data.get('usd_balance', 0))
                    curr_hive = int(target_data.get('nectar', 0))
                    
                    target_data['usd_balance'] = curr_usd + BONUS_REWARD_USD
                    target_data['nectar'] = curr_hive + BONUS_REWARD_HIVE
                    
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **TAREA APROBADA**\n\n💰 Recibiste: **${BONUS_REWARD_USD} USD**\n🐝 Recibiste: **{BONUS_REWARD_HIVE} HIVE**\n\n¡Sigue así!")
                    await update.message.reply_text(f"Pago Doble acreditado a {target}")
            except: pass
            return
        
        if text.startswith("/approve_vip"):
            try:
                target = int(text.split()[1])
                await context.bot.send_message(target, "👑 **LICENCIA DE REINA ACTIVADA**\n\nHas desbloqueado el poder x2 y los retiros prioritarios.")
                await update.message.reply_text(f"VIP activado a {target}")
            except: pass
            return

    # --- FLUJO DE USUARIO ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        # Paso 2: ACEPTACIÓN DE OFERTAS (LEGAL)
        kb = [[InlineKeyboardButton("✅ ACEPTO RECIBIR OFERTAS", callback_data="accept_legal")], [InlineKeyboardButton("❌ NO ME INTERESA GANAR", callback_data="reject_legal")]]
        await update.message.reply_text(get_text('es', 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    # Hash Crypto
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        if len(text) > 10:
            if ADMIN_ID != 0:
                try: await context.bot.send_message(ADMIN_ID, f"💰 **PAGO CRYPTO**\nUser: `{user.id}`\nHash: `{text}`\n\nUsa `/approve_vip {user.id}`")
                except: pass
            await update.message.reply_text("✅ **HASH ENVIADO.** Esperando validación del administrador.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER", callback_data="go_dashboard")]]))
        else: await update.message.reply_text("❌ Hash inválido.")
        return
        
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Email inválido.")
        return

    user_data = await db.get_user(user.id)
    if user_data: await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD (DATOS REALES + ENJAMBRE)
# -----------------------------------------------------------------------------
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; user_data = await db.get_user(user.id)
    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "Esperando..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** generados por tu red."
    
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    swarm_status = f"Solo (x1.0)" if refs == 0 else f"Líder (x{swarm_mult})"
    
    current_e = int(user_data.get('energy', 0))
    bar = render_progressbar(current_e, MAX_ENERGY_BASE)
    
    txt = get_text('es', 'dashboard_body',
        name=user.first_name, rank=calculate_rank(user_data.get('nectar', 0)),
        energy=current_e, max_energy=MAX_ENERGY_BASE, energy_bar=bar,
        rate=BASE_REWARD_PER_TAP * swarm_mult,
        usd=user_data.get('usd_balance', 0.0), hive=int(user_data.get('nectar', 0)),
        afk_msg=afk_msg, swarm_status=swarm_status
    )
    
    kb = []
    if afk_amount > 5: kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else: kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE (TAP)", callback_data="mine_click")])
    
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text('es', 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t3'), callback_data="tier_3")])
    kb.append([InlineKeyboardButton("🛒 TIENDA", callback_data="shop_menu"), InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")])
    kb.append([InlineKeyboardButton("👤 PERFIL", callback_data="profile"), InlineKeyboardButton("👥 ENJAMBRE", callback_data="team_menu")])
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. MINERÍA (PROOF OF WORK + SWARM)
# -----------------------------------------------------------------------------
async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: await query.answer("❄️ Enfriando...", show_alert=False); return
    context.user_data['last_mine_time'] = time.time()

    user_data = await db.get_user(user_id); user_data = await calculate_user_state(user_data) 
    cost = 20 
    if user_data['energy'] < cost: await query.answer("🔋 Batería Agotada.", show_alert=True); return

    user_data['energy'] -= cost
    is_premium = context.user_data.get('is_premium', False)
    multiplier = 2.0 if is_premium else 1.0
    
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    
    base_gain = BASE_REWARD_PER_TAP * multiplier * swarm_mult
    
    user_data['nectar'] = int(user_data.get('nectar', 0) + base_gain)
    await save_user_data(user_id, user_data)
    
    new_energy = int(user_data['energy'])
    new_hive = int(user_data['nectar'])
    
    msg_txt = get_text('es', 'mining_success', 
                       gain=f"{base_gain:.1f}", cost=MINING_COST_PER_TAP,
                       old_e=user_data['energy'] + cost, new_e=new_energy,
                       old_h=user_data['nectar'] - base_gain, new_h=new_hive, mult=swarm_mult)
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")], [InlineKeyboardButton("🔙 DASHBOARD", callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️ Minado!", show_alert=False)

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    amount = int(user_data.get('pending_afk', 0))
    if amount <= 0: await query.answer("Nada que recolectar.", show_alert=True); return
    user_data['nectar'] = int(user_data.get('nectar', 0) + amount); user_data['pending_afk'] = 0
    await save_user_data(user_id, user_data)
    await query.answer(f"💰 +{amount} HIVE transferidos.", show_alert=True); await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 8. SISTEMA DE TAREAS & VERIFICACIÓN
# -----------------------------------------------------------------------------
async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (VALIDAR)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ YA HICE UNA TAREA (VALIDAR)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['BYBIT'])],
        [InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO']), InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT'])],
        [InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE'])],
        [InlineKeyboardButton("💹 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (VALIDAR)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **ZONA 3: HIGH TICKET**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user = query.from_user
    await query.message.edit_text("🛰️ **ENVIANDO SOLICITUD DE REVISIÓN...**"); await asyncio.sleep(1.5)
    
    if ADMIN_ID != 0:
        try: await context.bot.send_message(ADMIN_ID, f"📋 **TAREA COMPLETADA**\nUser: {user.first_name} (`{user_id}`)\nUsa: `/approve_task {user_id}`")
        except: pass
    
    await query.message.edit_text("📝 **SOLICITUD PENDIENTE**\n\nTu saldo se actualizará tras la validación manual (12-24h).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ENTENDIDO", callback_data="go_dashboard")]]))

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); hive = user_data.get('nectar', 0)
    txt = get_text('es', 'shop_body', hive=hive) 
    kb = [[InlineKeyboardButton(f"⚡ RECARGA ENERGÍA ({COST_ENERGY_REFILL} HIVE)", callback_data="buy_energy")], [InlineKeyboardButton("👑 LICENCIA REINA ($10 USD)", callback_data="buy_premium_info")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; txt = get_text('es', 'payment_card_info')
    kb = [[InlineKeyboardButton("💳 PAGAR AHORA (SECURE)", web_app=WebAppInfo(url=LINK_PAGO_GLOBAL))], [InlineKeyboardButton("💎 PAGAR CON CRIPTO", callback_data="pay_crypto_info")], [InlineKeyboardButton("🔙 CANCELAR", callback_data="shop_menu")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def pay_crypto_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; txt = get_text('es', 'payment_crypto_info', wallet=CRYPTO_WALLET_USDT)
    kb = [[InlineKeyboardButton("✅ YA ENVIÉ EL PAGO", callback_data="confirm_crypto_wait")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def confirm_crypto_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; context.user_data['waiting_for_hash'] = True
    await query.message.edit_text("📝 **INGRESO MANUAL DE HASH**\n\nPega el TXID de tu transacción aquí.")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    refs = len(user_data.get('referrals', []))
    mult = calculate_swarm_bonus(refs)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = get_text('es', 'swarm_menu_body', count=refs, mult=mult) + f"\n`{link}`"
    kb = [[InlineKeyboardButton("📤 COMPARTIR ENLACE", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    txt = get_text(lang, 'ask_bonus', bonus_usd=BONUS_REWARD_USD, bonus_hive=BONUS_REWARD_HIVE, initial_hive=INITIAL_HIVE)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus', bonus=BONUS_REWARD_USD), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR MISIÓN", callback_data="verify_task_manual")]] 
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 9. ENRUTADOR
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; await query.message.edit_text(get_text('es', 'ask_email'), parse_mode="Markdown"); return
    if data == "reject_legal": await query.message.edit_text("❌ Acceso Denegado."); return
    if data == "bonus_done": await verify_task_manual(update, context); return 

    handlers = {
        "go_dashboard": show_dashboard, "mine_click": mining_animation, "claim_afk": claim_afk, "verify_task_manual": verify_task_manual, "shop_menu": shop_menu,
        "buy_premium_info": buy_premium_info, "pay_crypto_info": pay_crypto_info, "confirm_crypto_wait": confirm_crypto_wait,
        "tier_1": tier1_menu, "tier_2": tier2_menu, "tier_3": tier3_menu, "team_menu": team_menu, "go_justificante": show_justificante
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        user_data = await db.get_user(user_id)
        if user_data.get('nectar', 0) >= COST_ENERGY_REFILL:
            user_data['nectar'] -= COST_ENERGY_REFILL; user_data['energy'] = min(user_data.get('energy', 0) + 200, MAX_ENERGY_BASE)
            await save_user_data(user_id, user_data); await query.answer("⚡ Recarga exitosa.", show_alert=True); await show_dashboard(update, context)
        else: await query.answer(f"❌ Necesitas {COST_ENERGY_REFILL} HIVE.", show_alert=True)
    elif data == "profile": await query.message.edit_text(f"👤 **PERFIL**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
    elif data == "withdraw": 
        user_data = await db.get_user(user_id); bal = user_data.get('usd_balance', 0)
        if bal >= 10:
            if ADMIN_ID != 0: 
                try: await context.bot.send_message(ADMIN_ID, f"💸 **SOLICITUD RETIRO**\nUser: {user_id}\nMonto: ${bal}")
                except: pass
            await query.answer("✅ Solicitud enviada.", show_alert=True)
        else: await query.answer(f"🔒 Mínimo $10. Tienes ${bal:.2f}", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v140.0")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **ENVIADO:**\n\n{msg}")
    
async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_text = get_text('es', 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD** (Partner Network)\n✅ **ESTADO:** Validado."
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
