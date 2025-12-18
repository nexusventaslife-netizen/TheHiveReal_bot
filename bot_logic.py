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
# 1. KERNEL & SEGURIDAD (V156.0 - FULL ARSENAL + RLE DEFENSE)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado.")
    ADMIN_ID = 0

# IMAGEN DE BIENVENIDA (SOLICITADA)
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# DIRECCIONES DE COBRO Y PAGOS
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA "HARD MONEY" (AJUSTADA)
INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     

# TOKENOMICS (HIVE/Token Utility)
INITIAL_HIVE = 0.0          # Inicia en 0.0 para crear escasez
MINING_COST_PER_TAP = 5     # Costo mínimo por minería
BASE_REWARD_PER_TAP = 0.01  # Baja recompensa por minería
REWARD_VARIABILITY = 0.1    # Baja variabilidad

# ALGORITMO DE MINERÍA / ENERGÍA
MAX_ENERGY_BASE = 500       
ENERGY_REGEN = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 1.2       
COST_ENERGY_REFILL = 200    

# ANTI-FRAUDE CONSTANTES (RLE DEFENSE)
MIN_TIME_PER_TASK = 15      # Segundos mínimos humanos entre tareas complejas
TASK_TIMESTAMPS_LIMIT = 5   # Historial a guardar

# ESTADOS DEL SISTEMA (NIVELES)
STATES = {
    1: "Explorador", # Acceso Tier 1
    2: "Operador",   # Acceso Tier 2
    3: "Insider",    # Acceso Tier 3
    4: "Nodo",
    5: "Genesis"
}

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES (ACTUALIZADO)
# -----------------------------------------------------------------------------
LINKS = {
    # TIER 1: CLICKS & JUEGOS
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'EVERVE': "https://everve.net/ref/1950045/",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    
    # TIER 2: PASIVOS & MICRO-WORK
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # TIER 3: FINANZAS & ALTO VALOR
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
# 3. TEXTOS MULTI-IDIOMA
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **BIENVENIDO A THE ONE HIVE**\n"
            "──────────────────────────\n"
            "Hola, **{name}**. Estás entrando a una economía real.\n\n"
            "🧠 **TU ESTRATEGIA (PROOF OF WORK)**\n"
            "1. **TIER 1 (EXPLORADOR):** Tareas simples. Genera 'Dust' para empezar.\n"
            "2. **TIER 2 (OPERADOR):** Bloqueado. Requiere subir de nivel o Premium.\n"
            "3. **TIER 3 (GÉNESIS):** Finanzas. Alta rentabilidad.\n\n"
            "🛡️ **FASE 1: VERIFICACIÓN**\n"
            "👇 **INGRESA EL CÓDIGO** que aparecerá a continuación:"
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
            "🪙 **HIVE (UTILIDAD):** `{hive}`\n"
            "🔒 **Bloqueado:** `{locked_hive}`\n"
            "⚡ **Energía:** `{energy_bar}` {energy}%\n"
            "🛡️ **Nivel de Riesgo:** `{fraud_level}`\n"
            "──────────────────\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **ACCIÓN COMPLETADA**\n"
            "📊 **Rendimiento:** {performance_msg}\n"
            "🪙 **Tokens generados:** +{gain} (Var. x{mult})\n"
            "🔓 **Progreso interno actualizado.**"
        ),
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\n👑 **MEMBRESÍA REINA (PREMIUM) - $10**\n(Desbloquea Tier 2 y 3 sin subir de nivel)",
        'swarm_menu_body': (
            "🔗 **TU EQUIPO**\n\n"
            "No ganás por invitar. **Ganás cuando tus invitados TRABAJAN.**\n"
            "👥 **Obreros Activos:** {count}\n"
            "🚀 **Multiplicador:** x{mult}\n\n"
            "📌 **Tu Enlace:**\n`{link}`"
        ),
        'fraud_alert': "⚠️ **SISTEMA DE SEGURIDAD**\n\nPatrones inusuales detectados. Acceso restringido temporalmente.",
        'ban_alert': "🚫 **CUENTA DESHABILITADA**\n\nEl sistema ha detectado violaciones reiteradas de los términos de consistencia (RLE Defense).",
        'locked_tier': "🔒 **NIVEL BLOQUEADO**\n\nNecesitas ser nivel **{required_state}** o tener Membresía Premium para acceder a estas tareas de alto valor.\n\n💡 *Sigue trabajando en el nivel anterior o compra el pase en la Tienda.*",
        'btn_tasks': "🧠 VER TAREAS (WORK)", 'btn_progress': "🚀 MI PROGRESO", 'btn_mission': "🎯 MISIÓN",
        'btn_state': "🧬 ESTADO", 'btn_shop': "🛒 TIENDA", 'btn_withdraw': "💸 RETIRAR", 
        'btn_team': "👥 REFERIDOS", 'btn_back': "🔙 VOLVER"
    },
    'en': {
        'welcome_caption': "Welcome {name}...", 'ask_terms': "Accept terms?", 'ask_email': "Email:", 'ask_bonus': "Bonus ready.",
        'btn_claim_bonus': "Claim", 'dashboard_body': "State: {state_name}...", 'mine_feedback': "Mined.", 
        'fraud_alert': "System Error.", 'ban_alert': "Account Banned.", 'btn_tasks': "Tasks", 'btn_progress': "Progress", 'btn_mission': "Mission",
        'btn_state': "State", 'btn_shop': "Shop", 'btn_withdraw': "Withdraw", 'btn_team': "Team", 'btn_back': "Back",
        'locked_tier': "🔒 **LOCKED TIER**"
    }
}

# -----------------------------------------------------------------------------
# 4. MOTOR LÓGICO & ANTI-FRAUDE (RLE DEFENSE V1.0)
# -----------------------------------------------------------------------------

def get_text(lang_code, key, **kwargs):
    lang = 'es' if lang_code and 'es' in lang_code else 'en'
    t = TEXTS.get(lang, TEXTS['es']).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_captcha(): return f"HIVE-{random.randint(100, 999)}"

def render_progressbar(current, total, length=10):
    if total == 0: total = 1 # Evitar división por cero
    percent = max(0, min(current / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "░" * empty

def calculate_swarm_bonus(referrals_count):
    return round(1.0 + (min(referrals_count, 50) * 0.05), 2)

# --- MÓDULO RLE DEFENSE: ALGORITMOS DE DETECCIÓN ---

def check_scripting_speed(timestamps):
    """
    Detecta si las últimas tareas se realizaron demasiado rápido.
    Retorna puntos de riesgo.
    """
    if len(timestamps) < 3: return 0
    
    # Diferencias de tiempo entre las últimas 3 tareas (timestamps es una lista de floats)
    # timestamps = [t1, t2, t3, t4, t5] (donde t5 es el más reciente)
    latest = sorted(timestamps) 
    if len(latest) < 3: return 0
    
    diff1 = latest[-1] - latest[-2]
    diff2 = latest[-2] - latest[-3]
    
    # Penalización si 2 intervalos consecutivos son menores a 15 segundos
    if diff1 < MIN_TIME_PER_TASK and diff2 < MIN_TIME_PER_TASK:
        return 15 # Aumentar score de fraude
    return 0

def check_multi_account(current_user_hash, referral_id):
    """
    Detecta patrones de granja de referidos.
    (Requiere futura integración WebApp para el hash real)
    """
    score = 0
    # Simulación: Si tuviéramos acceso directo a Redis aquí para chequear colisiones de IP
    # if db.r and db.r.exists(f"ip_hash:{current_user_hash}"): score += 30
    return score

def check_low_quality(acceptance_count, completion_count):
    """
    Detecta usuarios que aceptan muchas tareas y no las terminan.
    """
    if acceptance_count > 10 and (completion_count / acceptance_count) < 0.15:
        return 10 # Marcar como granja de baja calidad
    return 0

def get_fraud_multiplier_and_status(fraud_score):
    """
    Determina la reducción de recompensa y el estado de bloqueo basado en el score.
    Retorna: (multiplicador, es_baneado)
    """
    if fraud_score >= 80:
        return 0.0, True # BLOQUEO TOTAL
    elif fraud_score >= 45:
        return 0.1, False # ALTO RIESGO (10% ganancias, cooldown)
    elif fraud_score >= 20:
        return 0.5, False # SOSPECHA (50% ganancias)
    else:
        return 1.0, False # NORMAL

# -------------------------------------------------------

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

    current_progress = user_data.get('progress_to_next_state', 0)
    max_progress = 100
    
    # GAMIFICACIÓN: Subida de nivel real (HARD MONEY ADJUSTMENT)
    if activity_type == "mine":
        progress_gain = 0.05  # Mínimo avance por click (necesitas miles de clicks)
    elif activity_type == "task_complete":
        progress_gain = 15    # Tareas dan progreso real
    else:
        progress_gain = 0
        
    user_data['progress_to_next_state'] = min(max_progress, current_progress + progress_gain)
    
    current_state = user_data.get('state', 1)
    # Solo sube hasta nivel 5
    if current_state < 5 and user_data['progress_to_next_state'] >= 100:
        user_data['state'] += 1
        user_data['progress_to_next_state'] = 0 
        
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
    
    # AFK REWARD (HARD MONEY ADJUSTMENT - ESCASEZ)
    afk_rate = user_data.get('state', 1) * 0.0001 * calculate_swarm_bonus(len(user_data.get('referrals', [])))
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 60: 
        pending_afk += afk_time * afk_rate
        # Tokens AFK se van a LOCKED hasta actividad
        user_data['tokens_locked'] = float(user_data.get('tokens_locked', 0) + pending_afk)
    
    user_data['pending_afk'] = 0
    user_data['last_update_ts'] = now
    
    user_data = await update_user_progress(user_data, activity_type="check") 
    
    return user_data

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
    
    # INICIALIZACIÓN DE CAMPOS FALTANTES (MIGRACIÓN AL VUELO)
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['energy'] = MAX_ENERGY_BASE
        user_data['state'] = 1
        user_data['streak'] = 0
        user_data['progress_to_next_state'] = 0
        user_data['tokens_locked'] = 0.0
        user_data['nectar'] = 0.0
        user_data['is_premium'] = False
        
        # RLE DEFENSE FIELDS
        user_data['fraud_score'] = 0 
        user_data['task_timestamps'] = [] 
        user_data['ban_status'] = False
        user_data['ip_address_hash'] = None
        
        await save_user_data(user.id, user_data)
        
    # CHECK BAN STATUS AL INICIO
    if user_data.get('ban_status', False):
        await update.message.reply_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return

    txt = get_text(lang, 'welcome_caption', name=user.first_name)
    
    captcha = generate_captcha()
    context.user_data['captcha'] = captcha
    code_message = f"🔐 **CÓDIGO DE ACTIVACIÓN**:\n\n`{captcha}`"

    kb = [[InlineKeyboardButton("▶️ COMENZAR", callback_data="start_validation")]]
    
    try: 
        await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error enviando foto: {e}")
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    await update.message.reply_text(code_message, parse_mode="Markdown")

async def start_validation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user = query.from_user; lang = user.language_code
    user_data = await db.get_user(user.id)
    if user_data.get('ban_status', False):
        await query.message.edit_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return
    await query.answer("Ingresa el código del captcha.")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    
    # RLE DEFENSE: Check Ban Status
    if user_data and user_data.get('ban_status', False):
        await update.message.reply_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return
        
    # --- ADMIN ---
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"):
            try:
                target = int(text.split()[1])
                target_data = await db.get_user(target)
                if target_data:
                    curr_usd = float(target_data.get('usd_balance', 0))
                    target_data['usd_balance'] = curr_usd + BONUS_REWARD_USD 
                    # Simular task completion timestamp
                    ts_list = target_data.get('task_timestamps', [])
                    ts_list.append(time.time())
                    target_data['task_timestamps'] = ts_list[-TASK_TIMESTAMPS_LIMIT:] # Keep only last 5
                    
                    target_data = await update_user_progress(target_data, activity_type="task_complete")
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **TASK APPROVED**\n💰 +${BONUS_REWARD_USD} USD")
                    await update.message.reply_text(f"Paid {target}")
            except: pass
            return
        
    # --- FLUJO USUARIO ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        kb = [[InlineKeyboardButton("✅ ACEPTAR / ACCEPT", callback_data="accept_legal")]]
        await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): 
                await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Invalid Email. Try again.")
        return

    if user_data: await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD (RLE Menu)
# -----------------------------------------------------------------------------
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    
    if update.callback_query:
        msg = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        msg = update.message
        user_id = user.id

    user_data = await db.get_user(user_id)
    
    # RLE DEFENSE: Check Ban Status
    if user_data.get('ban_status', False):
        await msg.reply_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return

    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    # VISUALIZACIÓN
    locked_balance = float(user_data.get('tokens_locked', 0))
    afk_msg = "Desbloquea Tokens con actividad." if locked_balance < 0.0001 else f"🔒 **{locked_balance:.4f} HIVE** (Bloqueados)."
    
    current_e = int(user_data.get('energy', 0))
    max_e = MAX_ENERGY_BASE
    
    energy_percent_val = int((current_e / max_e) * 100)
    bar = render_progressbar(current_e, max_e)
    
    current_state = user_data.get('state', 1)
    progress_val = user_data.get('progress_to_next_state', 0)
    progress_bar = render_progressbar(progress_val, 100)
    
    hive_balance = float(user_data.get('nectar', 0))
    
    # INFO DE FRAUDE PARA DASHBOARD
    f_score = user_data.get('fraud_score', 0)
    if f_score < 20: f_level = "🟢 Bajo"
    elif f_score < 45: f_level = "🟡 Medio"
    else: f_level = "🔴 Alto"

    txt = get_text(lang, 'dashboard_body',
        state_name=STATES.get(current_state, "Unknown"),
        streak=user_data.get('streak', 0),
        progress_bar=progress_bar, 
        progress_percent=f"{progress_val:.1f}",
        usd=user_data.get('usd_balance', 0.0), 
        hive=f"{hive_balance:.4f}",
        locked_hive=f"{locked_balance:.4f}",
        energy=energy_percent_val,
        energy_bar=bar,
        afk_msg=afk_msg,
        fraud_level=f_level
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="tier_1")],
        [InlineKeyboardButton(get_text(lang, 'btn_progress'), callback_data="show_progress"), InlineKeyboardButton(get_text(lang, 'btn_mission'), callback_data="show_mission")],
        [InlineKeyboardButton(get_text(lang, 'btn_state'), callback_data="show_state")],
        [InlineKeyboardButton("🔓 RECLAMAR AFK", callback_data="claim_afk")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu"), InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu")]
    ]
    
    if update.callback_query:
        try: await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await msg.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. ACCIONES: MINERÍA & CLAIM
# -----------------------------------------------------------------------------

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data.get('ban_status', False): return

    locked = float(user_data.get('tokens_locked', 0))
    if locked > 0:
        user_data['nectar'] = float(user_data.get('nectar', 0)) + locked
        user_data['tokens_locked'] = 0.0
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ +{locked:.4f} HIVE Reclamados!", show_alert=True)
        await show_dashboard(update, context)
    else:
        await query.answer("❄️ No hay tokens AFK.", show_alert=True)

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user = query.from_user; lang = user.language_code
    
    user_data = await db.get_user(user_id)
    if user_data.get('ban_status', False): 
        await query.message.edit_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return
        
    last_mine = context.user_data.get('last_mine_time', 0)
    current_time = time.time()
    
    if current_time - last_mine < MINING_COOLDOWN: await query.answer("❄️ Enfriando...", show_alert=False); return
    context.user_data['last_mine_time'] = current_time

    user_data = await calculate_user_state(user_data) 
    cost = MINING_COST_PER_TAP
    if user_data['energy'] < cost: await query.answer("🔋 Falta Energía.", show_alert=True); return

    user_data['energy'] -= cost
    
    # ---------------- RLE DEFENSE INTEGRATION ----------------
    # 1. Registrar timestamp
    ts_list = user_data.get('task_timestamps', [])
    ts_list.append(current_time)
    user_data['task_timestamps'] = ts_list[-TASK_TIMESTAMPS_LIMIT:] # Guardar solo últimos 5
    
    # 2. Calcular Riesgo
    risk_points = check_scripting_speed(user_data['task_timestamps'])
    # risk_points += check_multi_account(...) # Futuro
    
    user_data['fraud_score'] = min(100, user_data.get('fraud_score', 0) + risk_points)
    
    # 3. Determinar castigo (Fricción Dinámica)
    fraud_mult, is_banned = get_fraud_multiplier_and_status(user_data['fraud_score'])
    
    if is_banned:
        user_data['ban_status'] = True
        user_data['tokens_locked'] += float(user_data.get('nectar', 0)) # Bloquear todo el saldo
        user_data['nectar'] = 0.0
        await save_user_data(user_id, user_data)
        await query.message.edit_text(get_text(lang, 'ban_alert'), parse_mode="Markdown")
        return
    # ---------------------------------------------------------
    
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    base_gain = BASE_REWARD_PER_TAP * swarm_mult * (1 + (user_data.get('state', 1) * 0.1))
    
    variability = 1.0 + random.uniform(-REWARD_VARIABILITY, REWARD_VARIABILITY)
    
    # Aplicar reducción por fraude
    token_gain = base_gain * variability * fraud_mult
    
    user_data['nectar'] = float(user_data.get('nectar', 0) + token_gain)
    user_data = await update_user_progress(user_data, activity_type="mine")
    await save_user_data(user_id, user_data)
    
    performance_text = "Óptimo"
    if fraud_mult < 0.2: performance_text = "⚠️ Inconsistente (Bajo Rendimiento)"
    elif fraud_mult < 0.6: performance_text = "⚠️ Revisión Requerida"
    
    msg_txt = get_text(lang, 'mine_feedback', performance_msg=performance_text, gain=f"{token_gain:.4f}", mult=round(variability, 2))
    kb = [[InlineKeyboardButton("⛏️ MINAR DE NUEVO", callback_data="mine_click")], 
          [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️ OK")

# -----------------------------------------------------------------------------
# 8. MENÚS DE TAREAS (GAMIFICACIÓN Y BLOQUEOS)
# -----------------------------------------------------------------------------

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 1: ABIERTO A TODOS - Clicks y Juegos Básicos"""
    query = update.callback_query
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("🪙 COINTIPLY", url=LINKS['COINTIPLY']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("💸 FREECASH", url=LINKS['FREECASH']), InlineKeyboardButton("🌟 SWAGBUCKS", url=LINKS['SWAGBUCKS'])],
        [InlineKeyboardButton("📉 EVERVE", url=LINKS['EVERVE']), InlineKeyboardButton("⛏️ TAP MINING", callback_data="mine_click")],
        
        [InlineKeyboardButton("🟡 SIGUIENTE NIVEL (OPERADOR)", callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **TIER 1: INICIACIÓN**\n\nGenera tus primeros tokens con tareas simples.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 2: BLOQUEADO (Nivel 2+ o Premium)"""
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    user_data = await db.get_user(user_id)
    
    # LÓGICA DE BLOQUEO
    if user_data.get('state', 1) < 2 and not user_data.get('is_premium', False):
        await query.message.edit_text(get_text(lang, 'locked_tier', required_state="OPERADOR"), parse_mode="Markdown")
        return

    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("🚦 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("💼 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("🌱 SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("🧪 TESTBIRDS", url=LINKS['TESTBIRDS'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔴 SIGUIENTE NIVEL (INSIDER)", callback_data="tier_3")],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tier_1")]
    ]
    await query.message.edit_text("🟡 **TIER 2: OPERADOR**\n\nIngresos pasivos y trabajo freelance.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 3: BLOQUEADO (Nivel 3+ o Premium)"""
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    user_data = await db.get_user(user_id)
    
    # LÓGICA DE BLOQUEO
    if user_data.get('state', 1) < 3 and not user_data.get('is_premium', False):
        await query.message.edit_text(get_text(lang, 'locked_tier', required_state="INSIDER"), parse_mode="Markdown")
        return

    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($20)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("🦉 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("☁️ AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🐔 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("📈 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🏦 YOUHODLER", url=LINKS['YOUHODLER'])],
        [InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tier_2")]
    ]
    await query.message.edit_text("🔴 **TIER 3: INSIDER (PRO)**\n\nFinanzas y ofertas High-Ticket.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # RLE DEFENSE: Check Ban
    if user_data.get('ban_status', False):
        await query.message.edit_text("🚫 Cuenta Bloqueada.")
        return

    await query.message.edit_text("🛰️ **VERIFICANDO...**"); await asyncio.sleep(1.5)
    if ADMIN_ID != 0:
        try: await context.bot.send_message(ADMIN_ID, f"📋 **TASK PENDING**\nUser: `{user_id}`\n`/approve_task {user_id}`")
        except: pass
    await query.message.edit_text("📝 **EN REVISIÓN**\nSe acreditará tras verificación manual.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    refs = len(user_data.get('referrals', []))
    mult = calculate_swarm_bonus(refs)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    txt = get_text(lang, 'swarm_menu_body', count=refs, mult=mult, link=link)
    kb = [[InlineKeyboardButton("📤 COMPARTIR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    # Formateo visual
    hive_display = f"{float(user_data.get('nectar', 0)):.4f}"
    txt = get_text(lang, 'shop_body', hive=hive_display)
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 COMPRAR PREMIUM ($10)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(f"💎 **MEMBRESÍA REINA**\n\nEnvía $10 USD a:\n`{CRYPTO_WALLET_USDT}` (TRC20)\n\nLuego envía el Hash aquí.", parse_mode="Markdown")
    context.user_data['waiting_for_hash'] = True

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code; txt = get_text(lang, 'ask_bonus')
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")]] 
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_progress_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    progress = user_data.get('progress_to_next_state', 0)
    state = user_data.get('state', 1)
    txt = f"🚀 **PROGRESO**\n\nNivel: {STATES.get(state)}\nMeta: {STATES.get(state+1, 'MAX')}\n`{render_progressbar(progress, 100)}` {progress:.1f}%"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_mission_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🎯 **MISIÓN DIARIA**\n\nCompleta 2 tareas del Tier actual para recibir un bono de energía."
    kb = [[InlineKeyboardButton("IR A TAREAS", callback_data="tier_1")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_state_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🧬 **ESTADOS**\n\n1. Explorador\n2. Operador (Desbloquea Tier 2)\n3. Insider (Desbloquea Tier 3)\n4. Nodo\n5. Génesis"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 9. ENRUTADOR PRINCIPAL
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # ANTI-FRAUDE CHECK (RLE DEFENSE)
    if user_data and user_data.get('ban_status', False) and data != "go_dashboard":
        await query.message.edit_text(get_text(query.from_user.language_code, 'ban_alert'), parse_mode="Markdown"); return
    
    if data == "start_validation": await start_validation_flow(update, context); return
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; lang = query.from_user.language_code; await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown"); return

    handlers = {
        "go_dashboard": show_dashboard, 
        "mine_click": mining_animation, 
        "claim_afk": claim_afk, # FUNCIÓN CRÍTICA
        "verify_task_manual": verify_task_manual, 
        "shop_menu": shop_menu, 
        "buy_premium": buy_premium_flow,
        "tier_1": tier1_menu, 
        "tier_2": tier2_menu, 
        "tier_3": tier3_menu, 
        "team_menu": team_menu, 
        "show_progress": show_progress_menu, 
        "show_mission": show_mission_menu, 
        "show_state": show_state_menu
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        if float(user_data.get('nectar', 0)) >= COST_ENERGY_REFILL:
            user_data['nectar'] = float(user_data.get('nectar', 0)) - COST_ENERGY_REFILL
            user_data['energy'] = min(user_data.get('energy', 0) + 200, MAX_ENERGY_BASE)
            await save_user_data(user_id, user_data); await query.answer("⚡ Energía Recargada", show_alert=True); await show_dashboard(update, context)
        else: await query.answer("❌ Saldo insuficiente", show_alert=True)
    elif data == "withdraw": 
        await query.answer("Mínimo $10 USD", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v156.0 - Full Arsenal")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **ENVIADO**")
