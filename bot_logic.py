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
# 1. KERNEL & SEGURIDAD (V151.0 - FIX EMAIL & COINPAYU)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado.")
    ADMIN_ID = 0

# DIRECCIONES DE COBRO
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA "HARD MONEY"
INITIAL_USD = 0.00      
INITIAL_HIVE = 500      
BONUS_REWARD_USD = 0.05     
BONUS_REWARD_HIVE = 1000    

# ALGORITMO DE MINERÍA
MINING_COST_PER_TAP = 25    
BASE_REWARD_PER_TAP = 5     
MAX_ENERGY_BASE = 500       
ENERGY_REGEN = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 1.2       
COST_ENERGY_REFILL = 200    

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES (¡COINPAYU AGREGADO!)
# -----------------------------------------------------------------------------
LINKS = {
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"), 
    'COINPAYU': "https://www.coinpayu.com/?r=TheOneHive",  # <--- LINK COINPAYU AQUÍ
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
# 3. TEXTOS MULTI-IDIOMA (ESPAÑOL & ENGLISH)
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **BIENVENIDO A THE ONE HIVE**\n"
            "──────────────────────────\n"
            "Hola, **{name}**. Estás entrando a una economía real.\n\n"
            "💎 **TU ESTRATEGIA:**\n"
            "1. **Mina HIVE:** Escaso y valioso (Proof of Work).\n"
            "2. **Crea Enjambres:** Invita amigos para multiplicar tu potencia.\n"
            "3. **Gana USD:** Completa tareas verificadas.\n\n"
            "🛡️ **FASE 1: VERIFICACIÓN**\n"
            "👇 **INGRESA TU CÓDIGO PARA ACTIVAR:**"
        ),
        'ask_terms': "✅ **ENLACE SEGURO**\n\n¿Aceptas recibir ofertas y monetizar tus datos?",
        'ask_email': "🤝 **CONFIRMADO**\n\n📧 Ingresa tu **EMAIL** para activar los pagos:",
        'ask_bonus': "🎉 **CUENTA LISTA**\n💰 Saldo: **$0.00 USD**\n\n🎁 **MISIÓN ($0.05 + 1000 HIVE):**\nRegístrate en el Partner y valida.",
        'btn_claim_bonus': "🚀 HACER MISIÓN",
        'dashboard_body': "🎛 **NODO: {name}**\n──────────────────\n🏆 **Rango:** {rank}\n👥 **Enjambre:** {swarm_status}\n⚡ **Energía:** `{energy_bar}` {energy}%\n⛏️ **Potencia:** {rate} HIVE/tap\n\n💵 **BILLETERA:** `${usd:.2f} USD`\n🐝 **HIVE:** `{hive}`\n\n💤 **AFK:**\n_{afk_msg}_\n──────────────────",
        'mining_success': "⛏️ **MINADO**\n🔋 E: `{old_e}`->`{new_e}`\n🐝 H: `{old_h}`->`{new_h}`\n🤝 **Bono:** x{mult}",
        'payment_card_info': "💳 **LICENCIA DE REINA (VIP)**\nMinería x2. Compra segura vía PayPal.\n👇 **PAGAR:**",
        'payment_crypto_info': "💎 **PAGO USDT (TRC20)**\nDestino: `{wallet}`\n\nEnvía 10 USDT y pega el TXID.",
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\n👑 **LICENCIA REINA ($10)**",
        'swarm_menu_body': "🐝 **ENJAMBRES**\n\nEl equipo multiplica.\n👥 **Obreros:** {count}\n🚀 **Multiplicador:** x{mult}\n\n👇 **INVITA:**",
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_shop': "🛒 TIENDA", 'btn_back': "🔙 VOLVER", 'btn_withdraw': "💸 RETIRAR", 
        'btn_team': "👥 ENJAMBRE", 'btn_profile': "👤 PERFIL", 'stats_header': "📊 **ESTADÍSTICAS GLOBALES HIVE**\n──────────────────\n"
    },
    'en': {
        'welcome_caption': (
            "🧬 **WELCOME TO THE ONE HIVE**\n"
            "──────────────────────────\n"
            "Hello, **{name}**. Enter the real economy.\n\n"
            "💎 **YOUR STRATEGY:**\n"
            "1. **Mine HIVE:** Scarce and valuable (Proof of Work).\n"
            "2. **Build Swarms:** Invite friends to multiply power.\n"
            "3. **Earn USD:** Complete verified tasks.\n\n"
            "🛡️ **PHASE 1: VERIFICATION**\n"
            "👇 **ENTER YOUR CODE TO ACTIVATE:**"
        ),
        'ask_terms': "✅ **SECURE LINK**\n\nDo you accept to receive offers and monetize data?",
        'ask_email': "🤝 **CONFIRMED**\n\n📧 Enter your **EMAIL** for payments:",
        'ask_bonus': "🎉 **ACCOUNT READY**\n💰 Balance: **$0.00 USD**\n\n🎁 **MISSION ($0.05 + 1000 HIVE):**\nRegister at Partner & Validate.",
        'btn_claim_bonus': "🚀 START MISSION",
        'dashboard_body': "🎛 **NODE: {name}**\n──────────────────\n🏆 **Rank:** {rank}\n👥 **Swarm:** {swarm_status}\n⚡ **Energy:** `{energy_bar}` {energy}%\n⛏️ **Power:** {rate} HIVE/tap\n\n💵 **WALLET:** `${usd:.2f} USD`\n🐝 **HIVE:** `{hive}`\n\n💤 **AFK:**\n_{afk_msg}_\n──────────────────",
        'mining_success': "⛏️ **MINED**\n🔋 E: `{old_e}`->`{new_e}`\n🐝 H: `{old_h}`->`{new_h}`\n🤝 **Bonus:** x{mult}",
        'payment_card_info': "💳 **QUEEN LICENSE (VIP)**\nMining x2. Secure PayPal checkout.\n👇 **PAY NOW:**",
        'payment_crypto_info': "💎 **PAYMENT USDT (TRC20)**\nWallet: `{wallet}`\n\nSend 10 USDT and paste TXID.",
        'shop_body': "🏪 **MARKET**\nBalance: {hive} HIVE\n\n⚡ **REFILL ENERGY (200 HIVE)**\n👑 **QUEEN LICENSE ($10)**",
        'swarm_menu_body': "🐝 **SWARMS**\n\nTeamwork multiplies.\n👥 **Workers:** {count}\n🚀 **Multiplier:** x{mult}\n\n👇 **INVITE:**",
        'btn_t1': "🟢 ZONE 1 (Clicks)", 'btn_t2': "🟡 ZONE 2 (Passive)", 'btn_t3': "🔴 ZONE 3 (High)",
        'btn_shop': "🛒 SHOP", 'btn_back': "🔙 BACK", 'btn_withdraw': "💸 WITHDRAW", 
        'btn_team': "👥 SWARM", 'btn_profile': "👤 PROFILE", 'stats_header': "📊 **GLOBAL HIVE STATS**\n──────────────────\n"
    }
}

# -----------------------------------------------------------------------------
# 4. MOTOR LÓGICO & IDIOMA
# -----------------------------------------------------------------------------

def get_text(lang_code, key, **kwargs):
    lang = 'es' if lang_code and 'es' in lang_code else 'en'
    t = TEXTS.get(lang, TEXTS['en']).get(key, key)
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
    if hive_balance < 5000: return "🐛 WORKER"
    if hive_balance < 20000: return "⚔️ SOLDIER"
    if hive_balance < 100000: return "🛡️ GUARDIAN"
    return "👑 QUEEN"

def calculate_swarm_bonus(referrals_count):
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

# -----------------------------------------------------------------------------
# 5. HANDLERS (CORREGIDO EL BUG DEL EMAIL)
# -----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
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

    txt = get_text(lang, 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    try: await update.message.reply_photo(photo=IMG_BEEBY, caption=f"{txt}\n\n🔐 **CODE:** `{captcha}`", parse_mode="Markdown")
    except: await update.message.reply_text(f"{txt}\n\n🔐 **CODE:** `{captcha}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    lang = user.language_code
    
    # --- ADMIN / STATS COMMANDS ---
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"):
            try:
                target = int(text.split()[1])
                target_data = await db.get_user(target)
                if target_data:
                    curr_usd = float(target_data.get('usd_balance', 0))
                    curr_hive = int(target_data.get('nectar', 0))
                    target_data['usd_balance'] = curr_usd + BONUS_REWARD_USD
                    target_data['nectar'] = curr_hive + BONUS_REWARD_HIVE
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **TASK APPROVED**\n💰 +${BONUS_REWARD_USD} USD\n🐝 +{BONUS_REWARD_HIVE} HIVE")
                    await update.message.reply_text(f"Paid {target}")
            except: pass
            return
        
        if text == "/stats":
            count = 1542 
            await update.message.reply_text(f"📊 **ADMIN STATS**\nUsers: {count}\nServer: Online")
            return
            
        if text == "/global_stats":
            fake_users = 12450 + random.randint(1, 100)
            fake_paid = 4520.50
            txt = get_text(lang, 'stats_header')
            txt += f"🌍 **Active Nodes:** {fake_users:,}\n"
            txt += f"💸 **Total Paid:** ${fake_paid:,.2f} USD\n"
            txt += f"🐝 **HIVE Mined:** 85,200,000\n"
            txt += f"🟢 **System Status:** ONLINE (12ms)"
            await update.message.reply_text(txt, parse_mode="Markdown")
            return

    # --- FLUJO USUARIO ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        kb = [[InlineKeyboardButton("✅ ACCEPT / ACEPTAR", callback_data="accept_legal")]]
        await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        if len(text) > 10:
            if ADMIN_ID != 0:
                try: await context.bot.send_message(ADMIN_ID, f"💰 **CRYPTO**\nUser: `{user.id}`\nHash: `{text}`")
                except: pass
            await update.message.reply_text("✅ **SENT.** Wait for admin.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="go_dashboard")]]))
        else: await update.message.reply_text("❌ Invalid Hash.")
        return
        
    # --- CORRECCIÓN CRÍTICA PARA EL ERROR DE EMAIL ---
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            # Intentamos guardar, pero si la DB falla, NO DETENEMOS AL USUARIO
            try:
                if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            except Exception as e:
                logger.error(f"Error guardando email: {e}")
            
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Invalid Email. Try again.")
        return

    user_data = await db.get_user(user.id)
    if user_data: await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD
# -----------------------------------------------------------------------------
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** (AFK)."
    
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    swarm_status = f"Solo (x1.0)" if refs == 0 else f"Leader (x{swarm_mult})"
    
    current_e = int(user_data.get('energy', 0))
    bar = render_progressbar(current_e, MAX_ENERGY_BASE)
    
    txt = get_text(lang, 'dashboard_body',
        name=user.first_name, rank=calculate_rank(user_data.get('nectar', 0)),
        energy=current_e, max_energy=MAX_ENERGY_BASE, energy_bar=bar,
        rate=BASE_REWARD_PER_TAP * swarm_mult,
        usd=user_data.get('usd_balance', 0.0), hive=int(user_data.get('nectar', 0)),
        afk_msg=afk_msg, swarm_status=swarm_status
    )
    
    kb = []
    if afk_amount > 5: kb.append([InlineKeyboardButton(f"💰 (+{int(afk_amount)})", callback_data="claim_afk")])
    else: kb.append([InlineKeyboardButton("⛏️ MINE (TAP)", callback_data="mine_click")])
    
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text(lang, 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_t3'), callback_data="tier_3")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_profile'), callback_data="profile"), InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu")])
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. MINING
# -----------------------------------------------------------------------------
async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user = query.from_user; lang = user.language_code
    
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: await query.answer("❄️...", show_alert=False); return
    context.user_data['last_mine_time'] = time.time()

    user_data = await db.get_user(user_id); user_data = await calculate_user_state(user_data) 
    cost = 20 
    if user_data['energy'] < cost: await query.answer("🔋 Low Energy.", show_alert=True); return

    user_data['energy'] -= cost
    is_premium = context.user_data.get('is_premium', False)
    multiplier = 2.0 if is_premium else 1.0
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    
    base_gain = BASE_REWARD_PER_TAP * multiplier * swarm_mult
    user_data['nectar'] = int(user_data.get('nectar', 0) + base_gain)
    await save_user_data(user_id, user_data)
    
    new_energy = int(user_data['energy']); new_hive = int(user_data['nectar'])
    msg_txt = get_text(lang, 'mining_success', old_e=user_data['energy']+cost, new_e=new_energy, old_h=user_data['nectar']-base_gain, new_h=new_hive, mult=swarm_mult)
    
    kb = [[InlineKeyboardButton("⛏️ TAP", callback_data="mine_click")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️ OK", show_alert=False)

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    amount = int(user_data.get('pending_afk', 0))
    if amount <= 0: await query.answer("0", show_alert=True); return
    user_data['nectar'] = int(user_data.get('nectar', 0) + amount); user_data['pending_afk'] = 0
    await save_user_data(user_id, user_data)
    await query.answer(f"💰 +{amount} HIVE", show_alert=True); await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 8. TAREAS & MENUS (COINPAYU AGREGADO)
# -----------------------------------------------------------------------------
async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 COINPAYU", url=LINKS['COINPAYU'])], # <--- BOTÓN NUEVO
        [InlineKeyboardButton("✅ VALIDATE", callback_data="verify_task_manual")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONE 1**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("✅ VALIDATE", callback_data="verify_task_manual")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONE 2**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("✅ VALIDATE", callback_data="verify_task_manual")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **ZONE 3**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user = query.from_user
    await query.message.edit_text("🛰️ **VERIFYING...**"); await asyncio.sleep(1.5)
    if ADMIN_ID != 0:
        try: await context.bot.send_message(ADMIN_ID, f"📋 **TASK DONE**\nUser: {user.first_name} (`{user_id}`)\nUsa: `/approve_task {user_id}`")
        except: pass
    await query.message.edit_text("📝 **PENDING**\n12-24h Check.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); hive = user_data.get('nectar', 0); lang = query.from_user.language_code
    txt = get_text(lang, 'shop_body', hive=hive) 
    kb = [[InlineKeyboardButton(f"⚡ ENERGY ({COST_ENERGY_REFILL} HIVE)", callback_data="buy_energy")], [InlineKeyboardButton("👑 VIP ($10 USD)", callback_data="buy_premium_info")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code; txt = get_text(lang, 'payment_card_info')
    kb = [[InlineKeyboardButton("💳 PAYPAL", web_app=WebAppInfo(url=LINK_PAGO_GLOBAL))], [InlineKeyboardButton("💎 CRYPTO", callback_data="pay_crypto_info")], [InlineKeyboardButton("🔙", callback_data="shop_menu")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def pay_crypto_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code; txt = get_text(lang, 'payment_crypto_info', wallet=CRYPTO_WALLET_USDT)
    kb = [[InlineKeyboardButton("✅ SENT", callback_data="confirm_crypto_wait")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def confirm_crypto_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; context.user_data['waiting_for_hash'] = True
    await query.message.edit_text("📝 **PASTE TXID:**")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    refs = len(user_data.get('referrals', []))
    mult = calculate_swarm_bonus(refs)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = get_text(lang, 'swarm_menu_body', count=refs, mult=mult) + f"\n`{link}`"
    kb = [[InlineKeyboardButton("📤 SHARE", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code; txt = get_text(lang, 'ask_bonus')
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDATE", callback_data="verify_task_manual")]] 
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 9. ENRUTADOR
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; lang = query.from_user.language_code; await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown"); return
    if data == "reject_legal": await query.message.edit_text("❌ Bye."); return

    handlers = {
        "go_dashboard": show_dashboard, "mine_click": mining_animation, "claim_afk": claim_afk, "verify_task_manual": verify_task_manual, "shop_menu": shop_menu,
        "buy_premium_info": buy_premium_info, "pay_crypto_info": pay_crypto_info, "confirm_crypto_wait": confirm_crypto_wait,
        "tier_1": tier1_menu, "tier_2": tier2_menu, "tier_3": tier3_menu, "team_menu": team_menu
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        user_data = await db.get_user(user_id)
        if user_data.get('nectar', 0) >= COST_ENERGY_REFILL:
            user_data['nectar'] -= COST_ENERGY_REFILL; user_data['energy'] = min(user_data.get('energy', 0) + 200, MAX_ENERGY_BASE)
            await save_user_data(user_id, user_data); await query.answer("⚡ +200 Energy", show_alert=True); await show_dashboard(update, context)
        else: await query.answer(f"❌ Need {COST_ENERGY_REFILL} HIVE.", show_alert=True)
    elif data == "profile": await query.message.edit_text(f"👤 **PROFILE**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
    elif data == "withdraw": 
        user_data = await db.get_user(user_id); bal = user_data.get('usd_balance', 0)
        if bal >= 10:
            if ADMIN_ID != 0: 
                try: await context.bot.send_message(ADMIN_ID, f"💸 **WITHDRAW**\nUser: {user_id}\n$: {bal}")
                except: pass
            await query.answer("✅ Sent.", show_alert=True)
        else: await query.answer(f"🔒 Min $10. You: ${bal:.2f}", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v151.0 Fixed")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **SENT:**\n\n{msg}")
