import logging
import asyncio
import random
import string
import datetime
import json
import os
import time
import math
import statistics # [NUEVO] Para calculos estadisticos de fraude/ritmo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# -----------------------------------------------------------------------------
# 1. KERNEL & SEGURIDAD (V157.0 - HIVE MIND PROTOCOL)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado.")
    ADMIN_ID = 0

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# ECONOMÍA
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com")

INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     

# TOKENOMICS (Disruptiva)
INITIAL_HIVE = 0.0          
MINING_COST_PER_TAP = 5     
BASE_REWARD_PER_TAP = 0.05  # Aumentado ligeramente para compensar dificultad
REWARD_VARIABILITY = 0.1    

# ALGORITMO DE MINERÍA
MAX_ENERGY_BASE = 500       
ENERGY_REGEN = 1.5          # Regeneración dinámica
AFK_CAP_HOURS = 8           
MINING_COOLDOWN = 1.0       # Reducido para sentir fluidez
COST_ENERGY_REFILL = 200    

# ANTI-FRAUDE
MIN_TIME_PER_TASK = 15      
TASK_TIMESTAMPS_LIMIT = 10  # Aumentado para mejor analisis estadistico

STATES = {
    1: "Explorador (Larva)",
    2: "Operador (Zángano)",
    3: "Insider (Obrera)",
    4: "Nodo (Guerrera)",
    5: "Genesis (Reina)"
}

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES
# -----------------------------------------------------------------------------
LINKS = {
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'EVERVE': "https://everve.net/ref/1950045/",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"),
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29"
}

# -----------------------------------------------------------------------------
# 3. TEXTOS
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': "🧬 **THE ONE HIVE: PROTOCOLO V157**\n──────────────────\nHola, **{name}**. El sistema ha evolucionado.\n\n🧠 **NUEVA MECÁNICA:**\nTu ganancia ya no depende solo de clicks. Depende de tu **RITMO** y de la **CALIDAD** de tu enjambre.\n\n🛡️ **FASE 1: VERIFICACIÓN**\n👇 Ingresa el código:",
        'ask_terms': "✅ **SISTEMA SEGURO**\n\n¿Aceptas sincronizar tus datos con la colmena?",
        'ask_email': "🤝 **ENLACE ESTABLECIDO**\n\n📧 Ingresa tu **EMAIL** para activar retiros USD:",
        'ask_bonus': "🎉 **SINCRO COMPLETA**\n\n🎁 **PRIMERA MISIÓN ($0.05 USD):**\nRegístrate en el Partner Principal.",
        'btn_claim_bonus': "🚀 INICIAR MISIÓN",
        'dashboard_body': (
            "🧩 **ESTADO: {state_name}**\n"
            "🔥 **Resonancia:** x{resonance:.2f}\n"
            "🌊 **Ritmo:** {rhythm_status}\n"
            "──────────────────\n"
            "💰 **USD:** `${usd:.2f}`\n"
            "🪙 **HIVE:** `{hive}`\n"
            "🔒 **Bloqueado:** `{locked_hive}`\n"
            "⚡ **Energía:** `{energy_bar}` {energy}%\n"
            "🛡️ **Integridad:** `{fraud_level}`\n"
            "──────────────────\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **MINADO EXITOSO**\n"
            "🌊 Ritmo: {rhythm_msg}\n"
            "🐝 Enjambre: x{swarm_mult}\n"
            "🪙 **Total:** +{gain} HIVE"
        ),
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\n👑 **MEMBRESÍA REINA (PREMIUM) - $10**",
        'swarm_menu_body': "🔗 **TU ENJAMBRE (SWARM)**\n\n👥 Miembros: {count}\n🧬 **Calidad del Enjambre:** {quality}%\n(Si tus referidos no trabajan, tu multiplicador baja).\n\n📌 **Tu Enlace:**\n`{link}`",
        'fraud_alert': "⚠️ **ANOMALÍA DETECTADA**\n\nTu patrón de actividad no parece humano. Enfriando sistema.",
        'ban_alert': "🚫 **DESCONEXIÓN FORZADA**\n\nViolación crítica del protocolo RLE.",
        'locked_tier': "🔒 **ACCESO DENEGADO**\n\nNivel requerido: **{required_state}**.",
        'btn_tasks': "🧠 TAREAS", 'btn_progress': "🚀 EVOLUCIÓN", 'btn_mission': "🎯 MISIÓN",
        'btn_state': "🧬 ESTADO", 'btn_shop': "🛒 TIENDA", 'btn_withdraw': "💸 RETIRAR", 
        'btn_team': "👥 ENJAMBRE", 'btn_back': "🔙 VOLVER"
    },
    'en': {
        'welcome_caption': "Welcome {name}...", 'ask_terms': "Accept?", 'ask_email': "Email:", 'ask_bonus': "Bonus ready.",
        'btn_claim_bonus': "Claim", 'dashboard_body': "State: {state_name}...", 'mine_feedback': "Mined.", 
        'fraud_alert': "Error.", 'ban_alert': "Banned.", 'btn_tasks': "Tasks", 'btn_progress': "Progress", 'btn_mission': "Mission",
        'btn_state': "State", 'btn_shop': "Shop", 'btn_withdraw': "Withdraw", 'btn_team': "Team", 'btn_back': "Back",
        'locked_tier': "Locked"
    }
}

# -----------------------------------------------------------------------------
# 4. ALGORITMOS DISRUPTIVOS (THE HIVE MIND)
# -----------------------------------------------------------------------------

def get_text(lang_code, key, **kwargs):
    lang = 'es' if lang_code and 'es' in lang_code else 'en'
    t = TEXTS.get(lang, TEXTS['es']).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_captcha(): return f"HIVE-{random.randint(100, 999)}"

def render_progressbar(current, total, length=10):
    if total == 0: total = 1 
    percent = max(0, min(current / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "░" * empty

# --- [NUEVO] ALGORITMO: BIO-RHYTHM ---
def calculate_bio_rhythm_bonus(timestamps):
    """
    Analiza la varianza de los intervalos de tiempo.
    Un bot tiene varianza cercana a 0 (muy preciso).
    Un humano tiene varianza alta (caótico) o media (flow).
    Retorna (Multiplicador, Estado)
    """
    if len(timestamps) < 4: return 1.0, "Calibrando..."
    
    # Calcular intervalos entre clicks consecutivos
    intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    
    if not intervals: return 1.0, "Neutro"
    
    avg_interval = statistics.mean(intervals)
    try:
        stdev = statistics.stdev(intervals)
    except:
        stdev = 0
        
    cv = stdev / avg_interval if avg_interval > 0 else 0 # Coeficiente de variación
    
    # Lógica Disruptiva: Premiar el "Flow" (ritmo constante pero humano)
    # CV muy bajo (< 0.05) = Posible Bot = Penalización
    # CV medio (0.1 a 0.5) = Humano en ritmo = Bono x1.2
    # CV alto (> 0.5) = Humano distraído = Normal x1.0
    
    if cv < 0.05:
        return 0.5, "🤖 Mecánico (Baja Ganancia)"
    elif 0.1 <= cv <= 0.4:
        return 1.3, "🌊 FLOW (Bono Activo)"
    else:
        return 1.0, "👤 Normal"

# --- [NUEVO] ALGORITMO: SWARM RESONANCE ---
def calculate_swarm_resonance(referrals_count, user_level):
    """
    No premia la cantidad, sino la calidad.
    (En una implementación real completa, consultaría el nivel de los referidos en DB).
    Por ahora, simulamos que la 'resonancia' crece logarítmicamente con los referidos pero se topa por el nivel del usuario.
    """
    base_mult = 1.0
    # Logaritmo suave: 10 refs = x1.5, 50 refs = x2.0, 100 refs = x2.3
    swarm_factor = math.log1p(referrals_count) * 0.2
    
    # El usuario debe subir de nivel para desbloquear todo el potencial de su enjambre
    # Nivel 1 cap: x1.2, Nivel 2 cap: x1.5, etc.
    level_cap = 1.0 + (user_level * 0.2)
    
    final_mult = min(base_mult + swarm_factor, level_cap)
    return round(final_mult, 2)

# --- ENGINE ---

async def update_user_progress(user_data, activity_type="mine"):
    now_ts = time.time()
    last_activity = user_data.get('last_activity_ts', 0)
    day_ago = now_ts - (24 * 3600)
    
    if now_ts - last_activity > (48 * 3600):
        user_data['streak'] = 0 
        user_data['progress_to_next_state'] = 0

    if activity_type == "mine" and (now_ts - last_activity > 3600):
        if last_activity > day_ago and user_data['streak'] == 0:
            user_data['streak'] = 1
        elif last_activity < day_ago and user_data['streak'] > 0:
            user_data['streak'] += 1

    user_data['last_activity_ts'] = now_ts
    
    # PROGRESO DINÁMICO
    current_progress = user_data.get('progress_to_next_state', 0)
    max_progress = 100
    
    if activity_type == "mine":
        # Minar da poco progreso para forzar tareas
        progress_gain = 0.05 
    elif activity_type == "task_complete":
        progress_gain = 15    
    else:
        progress_gain = 0
        
    user_data['progress_to_next_state'] = min(max_progress, current_progress + progress_gain)
    
    current_state = user_data.get('state', 1)
    if current_state < 5 and user_data['progress_to_next_state'] >= 100:
        user_data['state'] += 1
        user_data['progress_to_next_state'] = 0 
        user_data['max_energy'] = int(user_data.get('max_energy', 500) * 1.2) # Level up aumenta tanque
        
    return user_data

async def calculate_user_state(user_data):
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    # AFK MINING (Solo si hay Swarm)
    refs = len(user_data.get('referrals', []))
    afk_rate = user_data.get('state', 1) * 0.0005 * (1 + (refs * 0.01))
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 300: # Minimo 5 min para generar
        pending_afk += afk_time * afk_rate
        user_data['tokens_locked'] = float(user_data.get('tokens_locked', 0) + pending_afk)
    
    user_data['pending_afk'] = 0
    user_data['last_update_ts'] = now
    
    return await update_user_progress(user_data, activity_type="check")

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r: await db.r.set(f"user:{user_id}", json.dumps(data))

# -----------------------------------------------------------------------------
# 5. HANDLERS (TELEGRAM)
# -----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    user_data = await db.get_user(user.id)
    
    # INICIALIZACIÓN MIGRATORIA V157
    defaults = {
        'last_update_ts': time.time(),
        'energy': MAX_ENERGY_BASE, 'max_energy': MAX_ENERGY_BASE,
        'state': 1, 'streak': 0, 'progress_to_next_state': 0,
        'tokens_locked': 0.0, 'nectar': 0.0, 'is_premium': False,
        'fraud_score': 0, 'task_timestamps': [], 'ban_status': False,
        'click_intervals': [], 'resonance_level': 1.0 # Campos V157
    }
    
    needs_save = False
    for k, v in defaults.items():
        if k not in user_data:
            user_data[k] = v
            needs_save = True
            
    if needs_save: await save_user_data(user.id, user_data)
        
    if user_data.get('ban_status', False):
        await update.message.reply_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return

    txt = get_text(lang, 'welcome_caption', name=user.first_name)
    captcha = generate_captcha()
    context.user_data['captcha'] = captcha
    code_message = f"🔐 **CLAVE DE ACCESO**:\n\n`{captcha}`"

    kb = [[InlineKeyboardButton("▶️ INICIAR PROTOCOLO", callback_data="start_validation")]]
    
    try: 
        await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    await update.message.reply_text(code_message, parse_mode="Markdown")

async def start_validation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Ingresa el código.")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    lang = user.language_code
    user_data = await db.get_user(user.id)
    
    if user_data and user_data.get('ban_status', False): return
        
    # ADMIN
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"):
            try:
                target = int(text.split()[1])
                target_data = await db.get_user(target)
                if target_data:
                    curr_usd = float(target_data.get('usd_balance', 0))
                    target_data['usd_balance'] = curr_usd + BONUS_REWARD_USD
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **MISIÓN APROBADA**\n💰 +${BONUS_REWARD_USD} USD")
                    await update.message.reply_text(f"Paid {target}")
            except: pass
            return
        
    # USER FLOW
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        kb = [[InlineKeyboardButton("✅ CONFIRMAR", callback_data="accept_legal")]]
        await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Email inválido.")
        return

    if user_data: await show_dashboard(update, context)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    if update.callback_query: msg = update.callback_query.message; user_id = update.callback_query.from_user.id
    else: msg = update.message; user_id = user.id

    user_data = await db.get_user(user_id)
    if user_data.get('ban_status', False): return

    user_data = await calculate_user_state(user_data) 
    
    # Calcular metricas disruptivas para visualizacion
    timestamps = user_data.get('task_timestamps', [])
    rhythm_mult, rhythm_status = calculate_bio_rhythm_bonus(timestamps)
    
    refs = len(user_data.get('referrals', []))
    resonance = calculate_swarm_resonance(refs, user_data.get('state', 1))
    
    await save_user_data(user.id, user_data)
    
    locked_balance = float(user_data.get('tokens_locked', 0))
    afk_msg = "Minando en segundo plano..." if locked_balance < 0.01 else f"🔒 **{locked_balance:.4f} HIVE** (Recolectado)."
    
    current_e = int(user_data.get('energy', 0))
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    bar = render_progressbar(current_e, max_e)
    
    f_score = user_data.get('fraud_score', 0)
    f_level = "🟢 Óptimo" if f_score < 30 else "🟡 Revisando" if f_score < 60 else "🔴 Crítico"

    txt = get_text(lang, 'dashboard_body',
        state_name=STATES.get(user_data.get('state', 1), "Desconocido"),
        resonance=resonance,
        rhythm_status=rhythm_status,
        usd=user_data.get('usd_balance', 0.0), 
        hive=f"{float(user_data.get('nectar', 0)):.2f}",
        locked_hive=f"{locked_balance:.2f}",
        energy=int((current_e/max_e)*100), energy_bar=bar,
        afk_msg=afk_msg, fraud_level=f_level
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_progress'), callback_data="show_progress"), InlineKeyboardButton(get_text(lang, 'btn_mission'), callback_data="show_mission")],
        [InlineKeyboardButton("⛏️ MINAR (TAP)", callback_data="mine_click")],
        [InlineKeyboardButton("🔓 RECOLECTAR AFK", callback_data="claim_afk")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu"), InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu")]
    ]
    
    if update.callback_query:
        try: await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await msg.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 6. MINERÍA AVANZADA (DISRUPTIVE LOGIC)
# -----------------------------------------------------------------------------

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    locked = float(user_data.get('tokens_locked', 0))
    if locked > 0.1:
        user_data['nectar'] = float(user_data.get('nectar', 0)) + locked
        user_data['tokens_locked'] = 0.0
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ +{locked:.2f} HIVE Recolectados", show_alert=True)
        await show_dashboard(update, context)
    else:
        await query.answer("❄️ Recolectando néctar... Espera un poco más.", show_alert=True)

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    NÚCLEO DE LA MINERÍA DISRUPTIVA
    Combina: Energía + Ritmo (Varianza) + Resonancia (Swarm) + Pulso Global
    """
    query = update.callback_query; user_id = query.from_user.id; user = query.from_user; lang = user.language_code
    user_data = await db.get_user(user_id)
    
    if user_data.get('ban_status', False): return
        
    # Cooldown Anti-Spam Básico
    last_mine = context.user_data.get('last_mine_time', 0)
    now = time.time()
    if now - last_mine < MINING_COOLDOWN: 
        await query.answer("⏳ Calma...", show_alert=False); return
    context.user_data['last_mine_time'] = now

    user_data = await calculate_user_state(user_data) 
    cost = MINING_COST_PER_TAP
    if user_data['energy'] < cost: await query.answer("🔋 Energía Agotada. Descansa o Recarga.", show_alert=True); return

    user_data['energy'] -= cost
    
    # 1. ACTUALIZAR TIMESTAMPS PARA RLE/RITMO
    ts_list = user_data.get('task_timestamps', [])
    ts_list.append(now)
    user_data['task_timestamps'] = ts_list[-TASK_TIMESTAMPS_LIMIT:] 
    
    # 2. CALCULAR MULTIPLICADORES DISRUPTIVOS
    rhythm_mult, rhythm_msg = calculate_bio_rhythm_bonus(user_data['task_timestamps'])
    
    refs_count = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_resonance(refs_count, user_data.get('state', 1))
    
    global_pulse = await db.get_global_pulse() # Variable del mercado global
    
    # 3. FÓRMULA MAESTRA HIVE
    base_gain = BASE_REWARD_PER_TAP
    
    # Si detecta ritmo "Mecánico" (Bot), reduce ganancia drásticamente
    if rhythm_msg.startswith("🤖"):
        # Castigo silencioso: no avisamos, solo reducimos
        fraud_factor = 0.1 
        user_data['fraud_score'] = min(100, user_data.get('fraud_score', 0) + 5)
    else:
        fraud_factor = 1.0
        # Sanar score de fraude si juega humano
        user_data['fraud_score'] = max(0, user_data.get('fraud_score', 0) - 1)
        
    if user_data.get('fraud_score', 0) > 80:
        user_data['ban_status'] = True
        await save_user_data(user_id, user_data)
        await query.message.edit_text(get_text(lang, 'ban_alert'))
        return

    total_gain = base_gain * rhythm_mult * swarm_mult * global_pulse * fraud_factor
    
    # Variabilidad visual (RNG menor)
    rng = random.uniform(0.95, 1.05)
    total_gain *= rng
    
    user_data['nectar'] = float(user_data.get('nectar', 0) + total_gain)
    user_data = await update_user_progress(user_data, activity_type="mine")
    await save_user_data(user_id, user_data)
    
    msg_txt = get_text(lang, 'mine_feedback', 
                       rhythm_msg=rhythm_msg, 
                       swarm_mult=swarm_mult, 
                       gain=f"{total_gain:.4f}")
                       
    kb = [[InlineKeyboardButton("⛏️ TAP", callback_data="mine_click")], 
          [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer(f"+{total_gain:.2f}")

# -----------------------------------------------------------------------------
# 7. MENÚS
# -----------------------------------------------------------------------------

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("💸 FREECASH", url=LINKS['FREECASH']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("⛏️ MINAR AHORA", callback_data="mine_click")],
        [InlineKeyboardButton("🟡 SUBIR NIVEL (OPERADOR)", callback_data="tier_2")],
        [InlineKeyboardButton("🔙", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: RECOLECCIÓN**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    if user_data.get('state', 1) < 2 and not user_data.get('is_premium', False):
        await query.answer("🔒 Nivel 2 requerido.", show_alert=True); return

    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("🌱 SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔴 SUBIR NIVEL (INSIDER)", callback_data="tier_3")],
        [InlineKeyboardButton("🔙", callback_data="tier_1")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: PROCESAMIENTO**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    if user_data.get('state', 1) < 3 and not user_data.get('is_premium', False):
        await query.answer("🔒 Nivel 3 requerido.", show_alert=True); return

    kb = [
        [InlineKeyboardButton("🔥 BYBIT", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("🦉 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("☁️ AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙", callback_data="tier_2")]
    ]
    await query.message.edit_text("🔴 **ZONA 3: CÁMARA REAL**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text("🛰️ **VERIFICANDO EN BLOCKCHAIN...**"); await asyncio.sleep(1.5)
    await query.message.edit_text("📝 **PENDIENTE**\nEl oráculo verificará tu transacción manualmente.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    
    refs = len(user_data.get('referrals', []))
    resonance = calculate_swarm_resonance(refs, user_data.get('state', 1))
    quality_percent = int((resonance / (1 + refs*0.2)) * 100) if refs > 0 else 100 # Estimación visual
    
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = get_text(lang, 'swarm_menu_body', count=refs, quality=quality_percent, link=link)
    
    kb = [[InlineKeyboardButton("📤 INVOCAR ZÁNGANOS", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    txt = get_text(lang, 'shop_body', hive=f"{float(user_data.get('nectar', 0)):.2f}")
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA (200 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 PREMIUM ($10)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(f"💎 **ACCESO REINA**\n\nEnvía $10 USD a:\n`{CRYPTO_WALLET_USDT}` (TRC20)\n\nEnvía el HASH aquí.", parse_mode="Markdown")
    context.user_data['waiting_for_hash'] = True

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code; txt = get_text(lang, 'ask_bonus')
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")]] 
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_progress_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    progress = user_data.get('progress_to_next_state', 0)
    state = user_data.get('state', 1)
    txt = f"🚀 **EVOLUCIÓN**\n\nFase Actual: {STATES.get(state)}\nSiguiente: {STATES.get(state+1, 'PERFECCIÓN')}\n`{render_progressbar(progress, 100)}` {progress:.1f}%"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_mission_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🎯 **OBJETIVO DIARIO**\n\nMantén un Ritmo (Flow) durante 50 clics para activar el bono de Resonancia máxima."
    kb = [[InlineKeyboardButton("IR", callback_data="mine_click")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 8. ENRUTADOR
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data and user_data.get('ban_status', False) and data != "go_dashboard":
        await query.message.edit_text("🚫 Acceso Denegado."); return
    
    if data == "start_validation": await start_validation_flow(update, context); return
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; await query.message.edit_text(get_text(query.from_user.language_code, 'ask_email'), parse_mode="Markdown"); return

    handlers = {
        "go_dashboard": show_dashboard, 
        "mine_click": mining_animation, 
        "claim_afk": claim_afk,
        "verify_task_manual": verify_task_manual, 
        "shop_menu": shop_menu, 
        "buy_premium": buy_premium_flow,
        "tier_1": tier1_menu, 
        "tier_2": tier2_menu, 
        "tier_3": tier3_menu, 
        "team_menu": team_menu, 
        "show_progress": show_progress_menu, 
        "show_mission": show_mission_menu
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        cost = COST_ENERGY_REFILL
        if float(user_data.get('nectar', 0)) >= cost:
            user_data['nectar'] = float(user_data.get('nectar', 0)) - cost
            user_data['energy'] = min(user_data.get('energy', 0) + 200, user_data.get('max_energy', 500))
            await save_user_data(user_id, user_data); await query.answer("⚡ +200 Energía", show_alert=True); await show_dashboard(update, context)
        else: await query.answer("❌ HIVE Insuficiente", show_alert=True)
    elif data == "withdraw": 
        await query.answer("Mínimo $10 USD para retiro.", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("HIVE PROTOCOL v157 - ONLINE")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset Local.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text("📢 Mensaje enviado a la colmena.")
