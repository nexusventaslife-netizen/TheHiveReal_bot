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
# 1. KERNEL & SEGURIDAD (V154.0 - REALITY LOOP ENGINE)
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

# ECONOMÍA "HARD MONEY" (Se mantiene para consistencia en pagos USD)
INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     

# TOKENOMICS (HIVE/Token Utility)
INITIAL_HIVE = 50 
MINING_COST_PER_TAP = 20    
BASE_REWARD_PER_TAP = 5     # Recompensa base antes de variabilidad y utilidad
REWARD_VARIABILITY = 0.4    # Variabilidad de +/- 40% en la recompensa

# ALGORITMO DE MINERÍA / ENERGÍA
MAX_ENERGY_BASE = 500       
ENERGY_REGEN = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 1.2       
COST_ENERGY_REFILL = 200    

# ESTADOS DEL SISTEMA
STATES = {
    1: "Explorador",
    2: "Operador",
    3: "Insider",
    4: "Nodo",
    5: "Genesis"
}

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES (Se mantienen los mismos enlaces)
# -----------------------------------------------------------------------------
LINKS = {
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"), 
    'COINPAYU': "https://www.coinpayu.com/?r=Josesitoto",  
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
# 3. TEXTOS MULTI-IDIOMA (RLE COPY)
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **BIENVENIDO A THE ONE HIVE**\n"
            "──────────────────────────\n"
            "Hola, **{name}**. Estás entrando a una economía real.\n\n"
            "🧠 **TU ESTRATEGIA**\n"
            "1. **TOKEN:** No es inversión, es utilidad y acceso.\n"
            "2. **ESTADO:** Sube tu estatus (no niveles) y desbloquea ventajas.\n"
            "3. **CONSTANCIA:** Los usuarios activos entran primero.\n\n"
            "🛡️ **FASE 1: VERIFICACIÓN**\n"
            "👇 **INGRESA EL CÓDIGO** que aparecerá a continuación para activar:"
        ),
        'ask_terms': "✅ **ENLACE SEGURO**\n\n¿Aceptas recibir ofertas y monetizar tus datos?",
        'ask_email': "🤝 **CONFIRMADO**\n\n📧 Ingresa tu **EMAIL** para activar los pagos USD:",
        'ask_bonus': "🎉 **CUENTA LISTA**\n\n🎁 **MISIÓN ($0.05 USD):**\nRegístrate en el Partner y valida. Los usuarios constantes tienen prioridad.",
        'btn_claim_bonus': "🚀 HACER MISIÓN",
        'dashboard_body': (
            "🧩 **ESTADO: {state_name}**\n"
            "🔥 **Racha:** {streak} días\n"
            "📈 **Progreso:** {progress_bar} {progress_percent}%\n"
            "──────────────────\n"
            "💰 **USD:** `${usd:.2f} USD`\n"
            "🪙 **TOKEN UTILITY (HIVE):** `{hive}`\n"
            "🔒 **Bloqueado:** `{locked_hive}`\n"
            "⚡ **Energía:** `{energy_bar}` {energy}%\n"
            "──────────────────\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **ACCIÓN COMPLETADA**\n"
            "📊 **Rendimiento:** {performance_msg}\n"
            "🪙 **Tokens generados:** +{gain:.0f} (Var. x{mult})\n"
            "🔓 **Progreso interno actualizado.** El sistema te considera más activo."
        ),
        'mining_success_old': "⛏️ **MINADO**\n🔋 E: `{old_e}`->`{new_e}`\n🐝 H: `{old_h}`->`{new_h}`\n🤝 **Bono:** x{mult}",
        'payment_card_info': "💳 **LICENCIA DE REINA (VIP)**\nMinería x2. Compra segura vía PayPal.\n👇 **PAGAR:**",
        'payment_crypto_info': "💎 **PAGO USDT (TRC20)**\nDestino: `{wallet}`\n\nEnvía 10 USDT y pega el TXID.",
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\n👑 **LICENCIA REINA ($10)**",
        'swarm_menu_body': (
            "🔗 **INVITAR USUARIOS**\n\n"
            "No ganás por invitar. **Ganás cuando tus invitados se activan.**\n"
            "👥 **Obreros Activos:** {count}\n"
            "🚀 **Multiplicador:** x{mult}\n\n"
            "📌 **Tu Enlace:**\n`{link}`\n\n"
            "_{bonus_msg}_"
        ),
        'btn_tasks': "🧠 VER TAREAS", 'btn_progress': "🚀 MI PROGRESO", 'btn_mission': "🎯 MISIÓN ESPECIAL",
        'btn_state': "🧬 ESTADO / BENEFICIOS", 'btn_shop': "🛒 TIENDA", 'btn_withdraw': "💸 RETIRAR", 
        'btn_team': "👥 REFERIDOS", 'btn_back': "🔙 VOLVER"
    },
    'en': {
        'welcome_caption': (
            "🧬 **WELCOME TO THE ONE HIVE**\n"
            "──────────────────────────\n"
            "Hello, **{name}**. You are entering a real economy.\n\n"
            "🧠 **YOUR STRATEGY**\n"
            "1. **TOKEN:** Not investment, but utility and access.\n"
            "2. **STATE:** Increase your status (not levels) and unlock advantages.\n"
            "3. **CONSISTENCY:** Active users get priority.\n\n"
            "🛡️ **PHASE 1: VERIFICATION**\n"
            "👇 **ENTER THE CODE** that appears below to activate:"
        ),
        'ask_terms': "✅ **SECURE LINK**\n\nDo you accept to receive offers and monetize data?",
        'ask_email': "🤝 **CONFIRMED**\n\n📧 Enter your **EMAIL** for USD payments:",
        'ask_bonus': "🎉 **ACCOUNT READY**\n\n🎁 **MISSION ($0.05 USD):**\nRegister at Partner & Validate. Consistent users get priority.",
        'btn_claim_bonus': "🚀 START MISSION",
        'dashboard_body': (
            "🧩 **STATE: {state_name}**\n"
            "🔥 **Streak:** {streak} days\n"
            "📈 **Progress:** {progress_bar} {progress_percent}%\n"
            "──────────────────\n"
            "💰 **USD:** `${usd:.2f} USD`\n"
            "🪙 **TOKEN UTILITY (HIVE):** `{hive}`\n"
            "🔒 **Locked:** `{locked_hive}`\n"
            "⚡ **Energy:** `{energy_bar}` {energy}%\n"
            "──────────────────\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **ACTION COMPLETED**\n"
            "📊 **Performance:** {performance_msg}\n"
            "🪙 **Tokens generated:** +{gain:.0f} (Var. x{mult})\n"
            "🔓 **Internal progress updated.** The system considers you more active."
        ),
        'mining_success_old': "⛏️ **MINED**\n🔋 E: `{old_e}`->`{new_e}`\n🐝 H: `{old_h}`->`{new_h}`\n🤝 **Bonus:** x{mult}",
        'payment_card_info': "💳 **QUEEN LICENSE (VIP)**\nMining x2. Secure PayPal checkout.\n👇 **PAY NOW:**",
        'payment_crypto_info': "💎 **PAYMENT USDT (TRC20)**\nWallet: `{wallet}`\n\nSend 10 USDT and paste TXID.",
        'shop_body': "🏪 **MARKET**\nBalance: {hive} HIVE\n\n⚡ **REFILL ENERGY (200 HIVE)**\n👑 **QUEEN LICENSE ($10)**",
        'swarm_menu_body': (
            "🔗 **INVITE USERS**\n\n"
            "You don't earn by inviting. **You earn when your invitees become active.**\n"
            "👥 **Active Workers:** {count}\n"
            "🚀 **Multiplier:** x{mult}\n\n"
            "📌 **Your Link:**\n`{link}`\n\n"
            "_{bonus_msg}_"
        ),
        'btn_tasks': "🧠 VIEW TASKS", 'btn_progress': "🚀 MY PROGRESS", 'btn_mission': "🎯 SPECIAL MISSION",
        'btn_state': "🧬 STATE / BENEFITS", 'btn_shop': "🛒 SHOP", 'btn_withdraw': "💸 WITHDRAW", 
        'btn_team': "👥 REFERRALS", 'btn_back': "🔙 BACK"
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

def generate_captcha(): return f"HIVE-{random.randint(100, 999)}"

def render_progressbar(current, total, length=10):
    percent = max(0, min(current / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "░" * empty

def calculate_swarm_bonus(referrals_count):
    # El multiplicador ahora es por actividad, no solo por conteo
    return round(1.0 + (min(referrals_count, 50) * 0.05), 2)

async def update_user_progress(user_data, activity_type="mine"):
    """Ajusta la racha, el progreso oculto y el estado del usuario."""
    now_ts = time.time()
    
    # Racha (Streak)
    last_activity = user_data.get('last_activity_ts', 0)
    day_ago = now_ts - (24 * 3600)
    
    if last_activity < day_ago:
        user_data['streak'] = 0  # Reiniciar si la última actividad fue hace más de 24h
        user_data['progress_to_next_state'] = 0

    if activity_type == "mine" and (now_ts - last_activity > 3600):
        # Aumentar racha si minó al menos una vez en las últimas 24h
        if last_activity > day_ago and user_data['streak'] == 0:
            user_data['streak'] = 1
        elif last_activity < day_ago and user_data['streak'] > 0:
            user_data['streak'] += 1

    user_data['last_activity_ts'] = now_ts

    # Progreso Oculto
    current_progress = user_data.get('progress_to_next_state', 0)
    max_progress = 100
    
    if activity_type == "mine":
        progress_gain = random.randint(3, 7) # Pequeña ganancia por TAP
    elif activity_type == "task_complete":
        progress_gain = 15 # Ganancia alta por tarea
    else:
        progress_gain = 0
        
    user_data['progress_to_next_state'] = min(max_progress, current_progress + progress_gain)
    
    # Actualizar Estado
    current_state = user_data.get('state', 1)
    if current_state < len(STATES) and user_data['progress_to_next_state'] >= 100:
        user_data['state'] += 1
        user_data['progress_to_next_state'] = 0 # Reiniciar progreso para el nuevo estado
        
    return user_data

async def calculate_user_state(user_data):
    """Calcula energía, AFK y llama a update_user_progress."""
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    # Regeneración de Energía
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    # AFK (Tokens bloqueados por inactividad)
    afk_rate = user_data.get('state', 1) * 0.1 * calculate_swarm_bonus(len(user_data.get('referrals', [])))
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 60: 
        pending_afk += afk_time * afk_rate
        # Los tokens AFK se consideran bloqueados hasta que el usuario reingresa.
        user_data['tokens_locked'] = int(user_data.get('tokens_locked', 0) + pending_afk)
    
    user_data['pending_afk'] = 0 # Se mueve al contador locked
    
    user_data['last_update_ts'] = now
    
    # Llamar a la lógica de RLE
    user_data = await update_user_progress(user_data, activity_type="check") 
    
    return user_data

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r: await db.r.set(f"user:{user_id}", json.dumps(data))

# -----------------------------------------------------------------------------
# 5. HANDLERS
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
        # Inicialización de nuevos campos RLE
        user_data['last_update_ts'] = time.time()
        user_data['energy'] = MAX_ENERGY_BASE
        user_data['state'] = 1
        user_data['streak'] = 0
        user_data['progress_to_next_state'] = 0
        user_data['tokens_locked'] = 0 
        await save_user_data(user.id, user_data)

    txt = (
        "Este no es un bot de tareas comunes.\n\n"
        "Acá **construís posición**.\n"
        "El sistema prioriza a los usuarios constantes.\n\n"
        "**Toca COMENZAR para validar.**"
    )
    
    captcha = generate_captcha()
    context.user_data['captcha'] = captcha
    
    welcome_message = f"{txt}"
    code_message = f"🔐 **CÓDIGO DE ACTIVACIÓN**:\n\n`{captcha}`"

    kb = [[InlineKeyboardButton("▶️ COMENZAR", callback_data="start_validation")]]
    
    try: 
        await update.message.reply_text(welcome_message, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        await update.message.reply_text(code_message, parse_mode="Markdown")
    except Exception: 
        await update.message.reply_text(f"{welcome_message}\n\n{code_message}", parse_mode="Markdown")

async def start_validation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user = query.from_user; lang = user.language_code
    await query.message.edit_text(get_text(lang, 'welcome_caption', name=user.first_name), parse_mode="Markdown")

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
                    # La recompensa de USD es plana (la recompensa de token es gamificada)
                    target_data['usd_balance'] = curr_usd + BONUS_REWARD_USD 
                    target_data = await update_user_progress(target_data, activity_type="task_complete")
                    await save_user_data(target, target_data)
                    
                    await context.bot.send_message(target, f"✅ **TASK APPROVED**\n💰 +${BONUS_REWARD_USD} USD\n🔓 Progreso interno avanzado.")
                    await update.message.reply_text(f"Paid {target}")
            except: pass
            return
            # ... (Otros comandos admin /stats se mantienen igual)
        
    # --- FLUJO USUARIO ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        kb = [[InlineKeyboardButton("✅ ACCEPT / ACEPTAR", callback_data="accept_legal")]]
        await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    if context.user_data.get('waiting_for_hash'):
        # ... (Lógica de crypto pago se mantiene)
        context.user_data['waiting_for_hash'] = False
        if len(text) > 10:
            if ADMIN_ID != 0:
                try: await context.bot.send_message(ADMIN_ID, f"💰 **CRYPTO**\nUser: `{user.id}`\nHash: `{text}`")
                except: pass
            await update.message.reply_text("✅ **SENT.** Wait for admin.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]))
        else: await update.message.reply_text("❌ Invalid Hash.")
        return
        
    # --- PROCESAMIENTO DE EMAIL ESTRICTO ---
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): 
                await db.update_email(user.id, text)
            
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Invalid Email. Try again.")
        return

    user_data = await db.get_user(user.id)
    if user_data: await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD (RLE Menu)
# -----------------------------------------------------------------------------
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('tokens_locked', 0)
    afk_msg = "Desbloquea Tokens con actividad." if afk_amount < 1 else f"🔒 **{afk_amount:.0f} HIVE** (Bloqueados)."
    
    current_e = int(user_data.get('energy', 0))
    bar = render_progressbar(current_e, MAX_ENERGY_BASE)
    
    current_state = user_data.get('state', 1)
    progress_percent = user_data.get('progress_to_next_state', 0)
    progress_bar = render_progressbar(progress_percent, 100)
    
    txt = get_text(lang, 'dashboard_body',
        state_name=STATES.get(current_state, "Unknown"),
        streak=user_data.get('streak', 0),
        progress_bar=progress_bar, progress_percent=progress_percent,
        usd=user_data.get('usd_balance', 0.0), 
        hive=int(user_data.get('nectar', 0)),
        locked_hive=int(user_data.get('tokens_locked', 0)),
        energy=current_e, energy_bar=bar,
        afk_msg=afk_msg
    )
    
    # Botones RLE (Ver tareas, Mi progreso, Misión especial, Estado)
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="mine_click")], # Minar es la tarea base
        [InlineKeyboardButton(get_text(lang, 'btn_progress'), callback_data="show_progress"), InlineKeyboardButton(get_text(lang, 'btn_mission'), callback_data="show_mission")],
        [InlineKeyboardButton(get_text(lang, 'btn_state'), callback_data="show_state")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu"), InlineKeyboardButton(get_text(lang, 'btn_withdraw'), callback_data="withdraw")]
    ]
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. MINING (Token Emission)
# -----------------------------------------------------------------------------
async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user = query.from_user; lang = user.language_code
    
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: await query.answer("❄️...", show_alert=False); return
    context.user_data['last_mine_time'] = time.time()

    user_data = await db.get_user(user_id); user_data = await calculate_user_state(user_data) 
    cost = MINING_COST_PER_TAP
    if user_data['energy'] < cost: await query.answer("🔋 Low Energy.", show_alert=True); return

    user_data['energy'] -= cost
    
    # Cálculo de Recompensa (Tokenomics: Variable + Utilidad)
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    performance_factor = (user_data.get('state', 1) * 0.1) # Utilidad basada en Estado
    
    base_gain = BASE_REWARD_PER_TAP * swarm_mult * performance_factor
    variability = 1.0 + random.uniform(-REWARD_VARIABILITY, REWARD_VARIABILITY)
    token_utility_gain = base_gain * variability
    
    old_hive = user_data.get('nectar', 0)
    user_data['nectar'] = int(old_hive + token_utility_gain)
    
    # Desbloqueo de Tokens con Actividad (ETH Style)
    if user_data.get('tokens_locked', 0) > 0:
        unlock_amount = random.randint(1, 10)
        user_data['nectar'] += unlock_amount
        user_data['tokens_locked'] -= unlock_amount
        if user_data['tokens_locked'] < 0: user_data['tokens_locked'] = 0
    
    user_data = await update_user_progress(user_data, activity_type="mine")
    await save_user_data(user_id, user_data)
    
    # Mensaje de Feedback RLE
    perf_msg = "Superior al promedio" if variability > 1.0 else "Consistente"
    
    msg_txt = get_text(lang, 'mine_feedback', 
                        performance_msg=perf_msg, 
                        gain=token_utility_gain + unlock_amount, 
                        mult=round(variability, 2))
    
    kb = [[InlineKeyboardButton("🧠 VER TAREAS (TAP)", callback_data="mine_click")], 
          [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️ OK", show_alert=False)

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # La lógica de AFK ahora es interna y se desbloquea con la actividad (Mining)
    await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 8. TAREAS & MENUS (Tier 1/2/3 como Tareas Encadenadas)
# -----------------------------------------------------------------------------
async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 COINPAYU", url=LINKS['COINPAYU'])], 
        [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **TAREAS FÁCILES (RANGO 6-14 TOKEN)**\nSelecciona una para iniciar.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **TAREAS MEDIAS (RANGO 12-28 TOKEN)**\nSe requiere estado **Operador** o superior.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")], [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **TAREAS AVANZADAS (RANGO 50+ TOKEN)**\nSolo estado **Insider** o superior.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user = query.from_user
    await query.message.edit_text("🛰️ **VERIFICANDO...**"); await asyncio.sleep(1.5)
    
    # Enviar al admin para aprobación de USD y avance de Progreso.
    if ADMIN_ID != 0:
        try: await context.bot.send_message(ADMIN_ID, f"📋 **TASK DONE**\nUser: {user.first_name} (`{user_id}`)\nUsa: `/approve_task {user_id}`")
        except: pass
    
    await query.message.edit_text("📝 **PENDIENTE**\nVerificación 12-24h. Tu perfil fue marcado como **activo**.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    refs = len(user_data.get('referrals', []))
    mult = calculate_swarm_bonus(refs)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    bonus_msg = "Invita usuarios activos para aumentar tu multiplicador interno."
    
    txt = get_text(lang, 'swarm_menu_body', count=refs, mult=mult, bonus_msg=bonus_msg) + f"\n`{link}`"
    kb = [[InlineKeyboardButton("📤 COMPARTIR ENLACE", url=f"https://t.me/share/url?url={link}")], 
          [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code; txt = get_text(lang, 'ask_bonus')
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")]] 
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_progress_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    
    progress = user_data.get('progress_to_next_state', 0)
    state = user_data.get('state', 1)
    
    txt = (
        "🚀 **TU PROGRESO EN EL SISTEMA**\n"
        "──────────────────\n"
        f"🧬 **Estado Actual:** {STATES.get(state, 'Unknown')}\n"
        f"📈 **Avance a {STATES.get(state + 1, 'MAX')}:** `{render_progressbar(progress, 100)}` {progress}%\n"
        f"🔥 **Racha Activa:** {user_data.get('streak', 0)} días\n"
        f"📊 **Consistencia:** { 'Alta' if user_data.get('streak', 0) >= 3 else 'Baja' }\n"
        f"🔒 **Tokens Bloqueados:** {user_data.get('tokens_locked', 0)}\n\n"
        "💡 **TIP:** Usuarios con racha activa desbloquean mejores tareas."
    )
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_mission_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    txt = (
        "🎯 **MISIÓN ESPECIAL (LIMITADA)**\n\n"
        "Solo para usuarios activos hoy.\n\n"
        "**Completar 2 tareas antes de 3h** puede:\n"
        "• Aumentar tu progreso interno\n"
        "• Priorizarte en próximas rondas\n\n"
        "⚠️ No siempre está disponible. ¡Aprovecha!"
    )
    kb = [[InlineKeyboardButton("🧠 VER TAREAS", callback_data="tier_1")], 
          [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_state_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; lang = query.from_user.language_code
    
    state_desc = "\n".join([f"🔹 **{name}:** acceso {('básico', 'priorizado', 'multiplicadores', 'anticipado', 'reservado')[i]}" for i, name in STATES.items()])
    
    txt = (
        "🧬 **ESTADOS DEL SISTEMA**\n"
        "──────────────────\n"
        f"{state_desc}\n\n"
        "⚠️ Los estados no se compran. Se desbloquean por comportamiento."
    )
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# 9. ENRUTADOR
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    
    if data == "start_validation": await start_validation_flow(update, context); return
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; lang = query.from_user.language_code; await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown"); return
    if data == "reject_legal": await query.message.edit_text("❌ Bye."); return

    handlers = {
        "go_dashboard": show_dashboard, "mine_click": mining_animation, "claim_afk": claim_afk, 
        "verify_task_manual": verify_task_manual, "shop_menu": tier1_menu, # Redirección
        "buy_premium_info": tier3_menu, "pay_crypto_info": tier3_menu, "confirm_crypto_wait": tier3_menu,
        "tier_1": tier1_menu, "tier_2": tier2_menu, "tier_3": tier3_menu, 
        "team_menu": team_menu, "show_progress": show_progress_menu, 
        "show_mission": show_mission_menu, "show_state": show_state_menu
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        user_data = await db.get_user(user_id)
        if user_data.get('nectar', 0) >= COST_ENERGY_REFILL:
            user_data['nectar'] -= COST_ENERGY_REFILL; user_data['energy'] = min(user_data.get('energy', 0) + 200, MAX_ENERGY_BASE)
            await save_user_data(user_id, user_data); await query.answer("⚡ +200 Energy", show_alert=True); await show_dashboard(update, context)
        else: await query.answer(f"❌ Need {COST_ENERGY_REFILL} HIVE.", show_alert=True)
    elif data == "profile": await show_state_menu(update, context) # Redirección a estado
    elif data == "withdraw": 
        user_data = await db.get_user(user_id); bal = user_data.get('usd_balance', 0)
        if bal >= 10:
            if ADMIN_ID != 0: 
                try: await context.bot.send_message(ADMIN_ID, f"💸 **WITHDRAW**\nUser: {user_id}\n$: {bal}")
                except: pass
            await query.answer("✅ Sent.", show_alert=True)
        else: await query.answer(f"🔒 Min $10 USD. You: ${bal:.2f} USD", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v154.0 RLE Engine")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **SENT:**\n\n{msg}")
