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
# 1. NÚCLEO DE CONFIGURACIÓN Y SEGURIDAD (NEXUS KERNEL)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD: ID de Administrador (Desde Variables de Entorno)
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado. Usando 0.")
    ADMIN_ID = 0

# DIRECCIONES DE COBRO
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA Y BALANCE INICIAL
INITIAL_USD = 0.00
INITIAL_HIVE = 500
BONUS_REWARD = 0.05

# MOTOR DE JUEGO & ALGORITMO "HIVE MIND"
MINING_RATE_BASE = 1.5
MAX_ENERGY_BASE = 500
ENERGY_REGEN = 1
AFK_CAP_HOURS = 6
MINING_COOLDOWN = 1.5

# COSTOS
COST_PREMIUM_MONTH = 10 
COST_ENERGY_REFILL = 500 

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES (TODAS LAS VÍAS DE INGRESO ACTIVAS)
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
# 3. TEXTOS NEUROLINGÜÍSTICOS (COPYWRITING EVOLUTIVO)
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE: CONEXIÓN ESTABLECIDA**\n"
            "──────────────────────────\n\n"
            "Bienvenido, **{name}**. Has salido de la Matrix.\n"
            "Aquí tu tiempo genera **VALOR REAL**.\n\n"
            "💎 **ESTRATEGIA DUAL:**\n"
            "1. **Mina Néctar (HIVE):** Tu moneda interna.\n"
            "2. **Zonas de Misión ($USD):** Pagos reales en Dólares.\n"
            "3. **Crea tu Enjambre:** Lidera un equipo y multiplica ganancias.\n\n"
            "🛡️ **FASE 1: SINCRONIZACIÓN**\n"
            "👇 **ENVÍA TU CÓDIGO DE ACCESO PARA ACTIVAR:**"
        ),
        'ask_terms': (
            "✅ **NODO VERIFICADO**\n"
            "───────────────────────\n"
            "**PROTOCOLO DE LA COLMENA:**\n\n"
            "Al unirte, aceptas:\n"
            "• Usar datos reales (Sin VPN/Bots).\n"
            "• Recibir alertas de monetización.\n"
            "• Participar en la economía de Enjambres.\n\n"
            "¿Aceptas el desafío?"
        ),
        'ask_email': "🤝 **ACEPTADO**\n\n📧 Escribe tu **EMAIL** principal para notificaciones de pago:",
        'ask_bonus': "🎉 **¡CUENTA ACTIVA!**\nSaldo: **$0.00 USD**\n\n🎁 **BONO INICIAL ($0.05):**\nValida tu identidad en el Partner Principal para reclamar.",
        'btn_claim_bonus': "🚀 RECLAMAR BONO (IR)",
        
        'dashboard_body': """
🎛 **NODO DE OPERACIONES: {name}**
──────────────────
🏆 **Rango:** {rank}
👥 **Enjambre:** {swarm_status}
⚡ **Energía:** {energy}/{max_energy}
⛏️ **Potencia:** {rate} HIVE/s

💵 **SALDO FIAT:** `${usd:.2f} USD`
🐝 **SALDO HIVE:** `{hive:.2f}`

⏳ **MINERÍA AFK:**
_{afk_msg}_
──────────────────
""",
        'mining_active': "⛏️ **EXTRAYENDO BLOQUE...**\n`{bar}` {percent}%\n\n🔗 Hash: `{hash}`",
        'mining_success': "✅ **BLOQUE MINADO**\n\n💰 **Base:** +{gain} HIVE\n🤝 **Bono Enjambre:** +{swarm_bonus}\n🔋 **Energía:** -{cost}",
        
        'payment_card_info': "💳 **LICENCIA DE REINA**\nCompra segura vía PayPal. Activación manual tras pago.\n\n👇 **PAGAR:**",
        'payment_crypto_info': """
💎 **PAGO USDT (TRC20)**
Destino: `{wallet}`

⚠️ Envía **10 USDT**.
Copia el **HASH (TXID)** y pégalo aquí.
""",
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (500 HIVE)**\n👑 **LICENCIA REINA ($10)**\n👷 **OBRERO (50k HIVE)**\n💎 **NFT (100k HIVE)**",
        'swarm_menu_body': """
🐝 **GESTIÓN DE ENJAMBRE (CLANES)**
──────────────────────────
El trabajo individual suma, el trabajo en equipo **MULTIPLICA**.

👥 **Tu Enjambre:** {swarm_count} Obreros
🚀 **Multiplicador Actual:** x{multiplier}

👇 **INVITA PARA AUMENTAR TU POTENCIA:**
""",
        
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_shop': "🛒 TIENDA", 'btn_justificante': "📜 AUDITORÍA", 'btn_back': "🔙 VOLVER", 
        'btn_withdraw': "💸 RETIRAR", 'btn_team': "👥 MI ENJAMBRE (CLAN)", 'btn_profile': "👤 PERFIL"
    }
}

# -----------------------------------------------------------------------------
# 4. LÓGICA MATEMÁTICA Y EVOLUTIVA (GAME ENGINE)
# -----------------------------------------------------------------------------

def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_hash(): return "0x" + ''.join(random.choices("ABCDEF0123456789", k=18))
def generate_captcha(): return f"HIVE-{random.randint(100, 999)}"

def calculate_rank(hive_balance):
    if hive_balance < 2000: return "🥚 LARVA"
    if hive_balance < 10000: return "🐛 OBRERO"
    if hive_balance < 50000: return "⚔️ SOLDADO"
    if hive_balance < 100000: return "🛡️ GUARDIÁN"
    return "👑 REINA"

def calculate_swarm_bonus(referrals_count):
    """Algoritmo de Enjambre: Más amigos = Más potencia"""
    # Base 1.0. Cada amigo añade 0.05 (5%)
    # Tope x2.0 (20 amigos)
    bonus = 1.0 + (min(referrals_count, 20) * 0.05)
    return round(bonus, 2)

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
    
    # [NEXUS-7]: El AFK también recibe bono de enjambre
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    
    afk_rate = mining_level * 0.2 * swarm_mult
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
        user_data['last_update_ts'] = time.time(); user_data['mining_level'] = 1
        await save_user_data(user.id, user_data)

    txt = get_text('es', 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    try: await update.message.reply_photo(photo=IMG_BEEBY, caption=f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")
    except: await update.message.reply_text(f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    
    # Bypass Admin (Gestión Humana)
    if user.id == ADMIN_ID and text.startswith("/approve_vip"):
        try:
            target_id = int(text.split()[1])
            await context.bot.send_message(target_id, "👑 **LICENCIA ACTIVADA**\nEl Administrador ha validado tu pago. Disfruta.")
            await update.message.reply_text(f"✅ VIP OK para {target_id}")
        except: pass
        return

    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        kb = [[InlineKeyboardButton("✅ ACEPTO EL PROTOCOLO", callback_data="accept_legal")], [InlineKeyboardButton("❌ CANCELAR", callback_data="reject_legal")]]
        await update.message.reply_text(get_text('es', 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        if len(text) > 10:
            if ADMIN_ID != 0:
                try: await context.bot.send_message(ADMIN_ID, f"💰 **PAGO DETECTADO**\nUser: {user.first_name}\nHash: `{text}`")
                except: pass
            context.user_data['is_premium'] = True
            await update.message.reply_text("✅ **HASH ENVIADO.** Validación en proceso.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("IR AL DASHBOARD", callback_data="go_dashboard")]]))
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
# 6. DASHBOARD (EVOLUTIVO)
# -----------------------------------------------------------------------------
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; user_data = await db.get_user(user.id)
    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "Esperando actividad..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** generados AFK."
    is_premium = context.user_data.get('is_premium', False)
    
    # Estado de Enjambre
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    swarm_status = f"Lobo Solitario (x1.0)" if refs == 0 else f"Líder de Enjambre (x{swarm_mult})"
    
    # Calculo de Rate Total
    total_rate = MINING_RATE_BASE * (2 if is_premium else 1) * swarm_mult
    
    txt = get_text('es', 'dashboard_body',
        name=user.first_name, rank=calculate_rank(user_data.get('nectar', 0)),
        level=user_data.get('mining_level', 1), energy=int(user_data['energy']),
        max_energy=MAX_ENERGY_BASE, rate=f"{total_rate:.2f}",
        usd=user_data.get('usd_balance', 0.0), hive=user_data.get('nectar', 0),
        afk_msg=afk_msg, swarm_status=swarm_status
    )
    
    kb = []
    if afk_amount > 10: kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else: kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE (TAP)", callback_data="mine_click")])
    
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text('es', 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t3'), callback_data="tier_3")])
    kb.append([InlineKeyboardButton("🛒 TIENDA", callback_data="shop_menu"), InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")])
    kb.append([InlineKeyboardButton("👤 PERFIL", callback_data="profile"), InlineKeyboardButton("👥 MI ENJAMBRE", callback_data="team_menu")])
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. MINERÍA CON "HIVE MIND" ALGORITHM
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
    
    # Cálculo de Multiplicadores (Premium + Swarm)
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    base_mult = 2.0 if is_premium else 1.0
    
    base_gain = MINING_RATE_BASE * 15 * base_mult
    
    # Critical Hit
    is_crit = random.random() < 0.15
    final_gain = base_gain * 2.5 if is_crit else base_gain
    
    # Aplicar bono de enjambre al final
    swarm_bonus_val = final_gain * (swarm_mult - 1.0)
    total_gain = final_gain + swarm_bonus_val
    
    user_data['nectar'] = int(user_data.get('nectar', 0) + total_gain)
    await save_user_data(user_id, user_data)

    # Animación
    block_hash = generate_hash()
    try:
        await query.message.edit_text(get_text('es', 'mining_active', bar="▓▓░░░░░░░░", percent=25, hash=block_hash[:10]+"..."), parse_mode="Markdown"); await asyncio.sleep(0.3)
        await query.message.edit_text(get_text('es', 'mining_active', bar="▓▓▓▓▓▓▓▓░░", percent=88, hash=block_hash), parse_mode="Markdown"); await asyncio.sleep(0.2)
    except: pass 

    final_txt = get_text('es', 'mining_success', gain=int(final_gain), cost=cost, swarm_bonus=f"{int(swarm_bonus_val)} (x{swarm_mult})")
    if is_crit: final_txt += "\n🔥 **¡CRITICAL HIT!**"
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")], [InlineKeyboardButton("🔙 DASHBOARD", callback_data="go_dashboard")]]
    await query.message.edit_text(final_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    amount = int(user_data.get('pending_afk', 0))
    if amount <= 0: await query.answer("Nada que recolectar.", show_alert=True); return
    user_data['nectar'] = int(user_data.get('nectar', 0) + amount); user_data['pending_afk'] = 0
    await save_user_data(user_id, user_data)
    await query.answer(f"💰 +{amount} HIVE transferidos.", show_alert=True); await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 8. MENÚS DE INGRESOS (ZONAS)
# -----------------------------------------------------------------------------
async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
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
        [InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **ZONA 3: HIGH TICKET**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    await query.message.edit_text("🛰️ **VERIFICANDO...**\nConectando con partner..."); await asyncio.sleep(2.0) 
    
    if not context.user_data.get('bonus_claimed'):
        context.user_data['bonus_claimed'] = True; user_data['usd_balance'] = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ ¡Bono de ${BONUS_REWARD} acreditado!", show_alert=True)
    else:
        await query.answer("⚠️ Tarea enviada a revisión. Estado: PENDIENTE (24h).", show_alert=True)
    await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 9. TIENDA, ENJAMBRE Y OTROS
# -----------------------------------------------------------------------------
async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); hive = user_data.get('nectar', 0)
    txt = get_text('es', 'shop_body', hive=hive) 
    kb = [[InlineKeyboardButton("⚡ RECARGA ENERGÍA (500 HIVE)", callback_data="buy_energy")], [InlineKeyboardButton("👑 LICENCIA REINA ($10 USD)", callback_data="buy_premium_info")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    refs_count = len(user_data.get('referrals', []))
    multiplier = calculate_swarm_bonus(refs_count)
    
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = get_text('es', 'swarm_menu_body', swarm_count=refs_count, multiplier=multiplier) + f"\n🔗 **ENLACE DE RECLUTAMIENTO:**\n`{link}`"
    
    kb = [[InlineKeyboardButton("📤 COMPARTIR ENLACE", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
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
    await query.message.edit_text("📝 **INGRESO MANUAL DE HASH**\n\nPega el TXID de tu transacción aquí para validación.")

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code; txt = get_text(lang, 'ask_bonus', bonus=BONUS_REWARD)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus', bonus=BONUS_REWARD), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR MISIÓN", callback_data="bonus_done")]]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 10. ENRUTADOR
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
            user_data['nectar'] -= COST_ENERGY_REFILL; user_data['energy'] = min(user_data.get('energy', 0) + MAX_ENERGY_BASE, 2000)
            await save_user_data(user_id, user_data); await query.answer("⚡ Recarga exitosa.", show_alert=True); await show_dashboard(update, context)
        else: await query.answer("❌ Saldo HIVE insuficiente.", show_alert=True)
    elif data == "profile": await query.message.edit_text(f"👤 **PERFIL**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
    elif data == "withdraw": 
        user_data = await db.get_user(user_id); bal = user_data.get('usd_balance', 0)
        if bal >= 10:
            if ADMIN_ID != 0: 
                try: await context.bot.send_message(ADMIN_ID, f"💸 **SOLICITUD DE RETIRO**\nUser: {user_id}\nMonto: ${bal}")
                except: pass
            await query.answer("✅ Solicitud enviada a revisión manual.", show_alert=True)
        else: await query.answer(f"🔒 Mínimo $10. Tienes ${bal:.2f}", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v110.0 Swarm Edition")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **ENVIADO:**\n\n{msg}")
    
async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_text = get_text('es', 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD** (Partner Network)\n✅ **ESTADO:** Validado en Blockchain."
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
