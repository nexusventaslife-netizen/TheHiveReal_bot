import logging
import asyncio
import random
import string
import datetime
import json
import os
import time
import math
from datetime import datetime as dt, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import database as db  # Asumimos que tu archivo database.py sigue existiendo para persistencia

# =============================================================================
# 1. KERNEL & SEGURIDAD (V156.0 + ELITE V2 ENGINE INTEGRATION)
# =============================================================================
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# --- SEGURIDAD ---
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    BOT_TOKEN = os.getenv("BOT_TOKEN", "") # Necesario para correr
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado.")
    ADMIN_ID = 0

# --- VISUALES ---
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- PAGOS ---
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# --- ECONOMÍA "HARD MONEY" (V156.0 BASE) ---
INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     
INITIAL_HIVE = 0.0
MINING_COST_PER_TAP = 5     
BASE_REWARD_PER_TAP = 0.01 
MAX_ENERGY_BASE = 500       
ENERGY_REGEN = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 1.2       
COST_ENERGY_REFILL = 200    
MIN_TIME_PER_TASK = 15 
TASK_TIMESTAMPS_LIMIT = 5 

# --- ELITE V2: ADVANCED ECONOMY & BEHAVIOR CONFIG ---
# (Agregado para cumplir con la solicitud de "Mejorar el código")
DAILY_EMISSION_SOFTCAP = 120.0
LOCK_RATIO = 0.65       # 65% de lo minado se va a vesting (Hardcore)
VESTING_DAYS = 7        # Días para liberar tokens
INACTIVITY_DECAY_DAYS = 3
RATE_LIMIT_SEC = 8      # Límite para calcular inercia
EVENT_PROB = 0.018      # Probabilidad de evento raro

# --- ESTADOS DEL SISTEMA (NIVELES) ---
STATES = {
    1: "Explorador", # Larva
    2: "Operador",   # Obrero
    3: "Insider",    # Explorador
    4: "Nodo",       # Guardian
    5: "Genesis"     # Genesis
}

# =============================================================================
# 2. MOTOR DE ENGAGEMENT (ELITE V2 ENGINE CLASS)
# =============================================================================
# Esta clase encapsula la lógica matemática avanzada para reemplazar el random simple.

class EngagementEngine:
    """
    Motor no determinista que evalúa el comportamiento del usuario
    para otorgar recompensas basadas en consistencia y no solo en clicks.
    """
    def score(self, user_data):
        # Extraemos métricas del user_data (o usamos defaults)
        streak = user_data.get('streak', 0)
        consistency = user_data.get('consistency', 0.0) # Nueva métrica
        freq = user_data.get('session_freq', 0.0)       # Nueva métrica
        spam = user_data.get('spam_score', 0.0)         # Score de spam/clicker
        decay = user_data.get('role_decay', 0)          # Desgaste por inactividad
        
        last_action_iso = user_data.get('last_action_iso', dt.utcnow().isoformat())
        try:
            last_time = dt.fromisoformat(last_action_iso)
        except:
            last_time = dt.utcnow()

        # Fórmula Elite v2
        base = (streak * 0.35) + (consistency * 0.35) + (freq * 0.2) - (spam * 0.6) - (decay * 0.25)
        
        # Inercia: Si la acción es muy rápida, reduce el score (anti-autoclicker sutil)
        seconds_diff = (dt.utcnow() - last_time).total_seconds()
        inertia = 1.0 if seconds_diff > RATE_LIMIT_SEC else 0.6
        
        return max(base * inertia, 0)

    def reward(self, base_amount, score):
        # La recompensa ya no es plana, depende de la Entropía y el Score del usuario
        entropy = random.uniform(0.8, 1.2)
        # Spike: Posibilidad de recompensa crítica si el score es alto
        spike = random.uniform(1.15, 1.5) if random.random() < min(0.12, score / 120) else 1.0
        
        return base_amount * entropy * spike

ENGINE = EngagementEngine()

# =============================================================================
# 3. ARSENAL DE ENLACES (ACTUALIZADO CON FAUCETPAY)
# =============================================================================
LINKS = {
    # TIER 1: CLICKS & JUEGOS
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014", # AGREGADO
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

# =============================================================================
# 4. TEXTOS MULTI-IDIOMA
# =============================================================================
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **BIENVENIDO A THE ONE HIVE (ELITE CORE)**\n"
            "──────────────────────────\n"
            "Hola, **{name}**. Estás entrando a una economía real y vigilada.\n\n"
            "🧠 **SISTEMA DE REPUTACIÓN ACTIVO**\n"
            "Tus acciones son evaluadas por el `HiveEngine`. La consistencia premia más que la velocidad.\n\n"
            "1. **TIER 1 (EXPLORADOR):** Tareas simples. Genera 'Dust'.\n"
            "2. **TIER 2 (OPERADOR):** Bloqueado. Requiere reputación alta.\n"
            "3. **TIER 3 (GÉNESIS):** Finanzas. Alta rentabilidad.\n\n"
            "👇 **INGRESA EL CÓDIGO** para validar humanidad:"
        ),
        'ask_terms': "✅ **ENLACE SEGURO**\n\n¿Aceptas recibir ofertas y monetizar tus datos?",
        'ask_email': "🤝 **CONFIRMADO**\n\n📧 Ingresa tu **EMAIL** para activar los pagos USD:",
        'ask_bonus': "🎉 **CUENTA LISTA**\n\n🎁 **MISIÓN ($0.05 USD):**\nRegístrate en el Partner y valida. Los usuarios constantes tienen prioridad.",
        'btn_claim_bonus': "🚀 HACER MISIÓN",
        'dashboard_body': (
            "🧩 **ESTADO: {state_name}**\n"
            "🔥 **Racha:** {streak} días | ⭐ **Reputación:** {behavior_score}\n"
            "📈 **Progreso Oculto:** {progress_bar} {progress_percent}%\n"
            "──────────────────\n"
            "💰 **USD:** `${usd:.2f} USD`\n"
            "🪙 **HIVE LIBRE:** `{hive}`\n"
            "🔒 **VESTING (7 Días):** `{locked_hive}`\n"
            "⚡ **Energía:** `{energy_bar}` {energy}%\n"
            "──────────────────\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **ANÁLISIS DE ENGAGEMENT**\n"
            "📊 **Calidad:** {performance_msg}\n"
            "🪙 **Recompensa Total:** {total_gain}\n"
            "🔓 **Libre:** {free} | 🔒 **Vesting:** {locked}\n"
            "⚡ *Tu reputación afecta la minería.*"
        ),
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\n👑 **MEMBRESÍA REINA (PREMIUM) - $10**\n(Ignora requisitos de reputación)",
        'swarm_menu_body': (
            "🔗 **TU ENJAMBRE**\n\n"
            "No ganás por invitar. **Ganás cuando tus invitados TRABAJAN.**\n"
            "👥 **Obreros Activos:** {count}\n"
            "🚀 **Multiplicador:** x{mult}\n\n"
            "📌 **Tu Enlace:**\n`{link}`"
        ),
        'fraud_alert': "⚠️ **SISTEMA DE SEGURIDAD**\n\nComportamiento automatizado detectado. Acceso restringido.",
        'locked_tier': "🔒 **NIVEL BLOQUEADO**\n\nNecesitas ser nivel **{required_state}** o tener Membresía Premium.\n\n💡 *El sistema Elite requiere consistencia diaria para subir.*",
        'btn_tasks': "🧠 VER TAREAS (WORK)", 'btn_progress': "🚀 MI PROGRESO", 'btn_mission': "🎯 MISIÓN",
        'btn_state': "🧬 ESTADO", 'btn_shop': "🛒 TIENDA", 'btn_withdraw': "💸 RETIRAR", 
        'btn_team': "👥 REFERIDOS", 'btn_back': "🔙 VOLVER"
    },
    'en': {
        'welcome_caption': "Welcome {name}...", 'ask_terms': "Accept terms?", 'ask_email': "Email:", 'ask_bonus': "Bonus ready.",
        'btn_claim_bonus': "Claim", 'dashboard_body': "State: {state_name}...", 'mine_feedback': "Mined.", 
        'fraud_alert': "System Error.", 'btn_tasks': "Tasks", 'btn_progress': "Progress", 'btn_mission': "Mission",
        'btn_state': "State", 'btn_shop': "Shop", 'btn_withdraw': "Withdraw", 'btn_team': "Team", 'btn_back': "Back",
        'locked_tier': "🔒 **LOCKED TIER**"
    }
}

# =============================================================================
# 5. LÓGICA DE NEGOCIO Y PERSISTENCIA DE DATOS
# =============================================================================

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

def calculate_swarm_bonus(referrals_count):
    return round(1.0 + (min(referrals_count, 50) * 0.05), 2)

async def save_user_data(user_id, data):
    """Wrapper para guardar en BD (asumiendo que db.r es Redis o similar)"""
    if hasattr(db, 'r') and db.r: 
        await db.r.set(f"user:{user_id}", json.dumps(data))

# --- ACTUALIZACIÓN DE ESTADO Y MÉTRICAS ELITE ---
async def update_user_elite_metrics(user_data, activity_type="mine"):
    """
    Función central que actualiza las métricas del Engine v2
    """
    now_ts = time.time()
    last_activity = user_data.get('last_activity_ts', 0)
    day_ago = now_ts - (24 * 3600)
    
    # 1. Racha (Streak)
    if now_ts - last_activity > (48 * 3600):
        user_data['streak'] = 0 
        user_data['role_decay'] = user_data.get('role_decay', 0) + 1 # Penalización por abandono
    
    if activity_type == "mine" and (now_ts - last_activity > 3600):
        if last_activity > day_ago and user_data['streak'] == 0:
            user_data['streak'] = 1
        elif last_activity < day_ago and user_data['streak'] > 0:
            user_data['streak'] += 1

    # 2. Frecuencia y Consistencia (Simulada para persistencia simple)
    # En un DB relacional esto sería más complejo, aquí usamos promedios móviles simples
    if activity_type == "mine":
        current_freq = user_data.get('session_freq', 0.0)
        user_data['session_freq'] = min(10.0, current_freq + 0.1)
    
    user_data['last_activity_ts'] = now_ts
    user_data['last_action_iso'] = dt.utcnow().isoformat()
    
    return user_data

async def calculate_user_state(user_data):
    """
    Recalcula energía y recompensas pasivas (AFK) con lógica Elite
    """
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    # Regeneración de Energía
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    # AFK REWARD - Usando multiplicadores Elite
    # El usuario gana pasivamente solo si tiene un rol decente (State > 1)
    afk_rate = 0
    if user_data.get('state', 1) > 1:
        afk_rate = user_data.get('state', 1) * 0.00005 * calculate_swarm_bonus(len(user_data.get('referrals', [])))
    
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    pending_afk = user_data.get('pending_afk', 0)
    
    if afk_time > 60: 
        generated = afk_time * afk_rate
        # En Elite v2, el AFK se va directo a Bloqueado/Vesting para evitar dumping
        user_data['tokens_locked'] = float(user_data.get('tokens_locked', 0) + generated)
    
    user_data['pending_afk'] = 0
    user_data['last_update_ts'] = now
    
    # Actualizamos métricas de comportamiento
    user_data = await update_user_elite_metrics(user_data, activity_type="check")
    
    return user_data

# --- ANTI-FRAUDE ---
def check_scripting_speed(task_timestamps):
    if len(task_timestamps) < 3: return 0
    MIN_TIME = MIN_TIME_PER_TASK 
    risk_score_increase = 0
    if len(task_timestamps) >= 3:
        latest_stamps = task_timestamps[::-1] 
        gap1 = latest_stamps[0] - latest_stamps[1]
        gap2 = latest_stamps[1] - latest_stamps[2]
        if gap1 < MIN_TIME and gap2 < MIN_TIME:
            risk_score_increase = 25 
    return risk_score_increase

def update_fraud_score(user_data, activity_type="task_complete"):
    current_score = user_data.get('fraud_score', 0)
    if activity_type == "task_complete":
        current_score += check_scripting_speed(user_data.get('task_timestamps', []))
    
    # Recuperación lenta de reputación si no hace spam
    if activity_type == "mine" and current_score > 0:
        current_score -= 0.1 
            
    user_data['fraud_score'] = min(100, max(0, current_score))
    
    if user_data['fraud_score'] >= 80:
        user_data['ban_status'] = True
        user_data['tokens_locked'] += user_data.get('nectar', 0)
        user_data['nectar'] = 0
        
    return user_data

# =============================================================================
# 6. HANDLERS (TELEGRAM)
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    # Integración con DB existente
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    user_data = await db.get_user(user.id)
    
    # INICIALIZACIÓN DE PERFIL ELITE V2
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['energy'] = MAX_ENERGY_BASE
        user_data['state'] = 1
        user_data['streak'] = 0
        user_data['progress_to_next_state'] = 0
        user_data['tokens_locked'] = 0.0 
        user_data['nectar'] = 0.0 
        user_data['usd_balance'] = INITIAL_USD
        user_data['fraud_score'] = 0 
        user_data['task_timestamps'] = [] 
        user_data['ban_status'] = False
        user_data['is_premium'] = False 
        
        # Nuevos campos Elite v2
        user_data['consistency'] = 0.0
        user_data['session_freq'] = 0.0
        user_data['behavior_score'] = 0.0
        user_data['role_decay'] = 0
        user_data['vesting_until'] = (dt.utcnow() + timedelta(days=VESTING_DAYS)).isoformat()
        
        await save_user_data(user.id, user_data)

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
        await query.message.edit_text(get_text(lang, 'fraud_alert'), parse_mode="Markdown")
        return
    await query.answer("Ingresa el código del captcha.")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    if user_data and user_data.get('ban_status', False):
        await update.message.reply_text(get_text(lang, 'fraud_alert'), parse_mode="Markdown")
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
                    # Elite: Tarea completada sube consistencia masivamente
                    target_data['consistency'] = min(100.0, target_data.get('consistency', 0) + 5.0)
                    target_data['task_timestamps'].append(time.time())
                    target_data = await update_user_elite_metrics(target_data, activity_type="task_complete")
                    target_data = update_fraud_score(target_data, activity_type="task_complete") 
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **TASK APPROVED**\n💰 +${BONUS_REWARD_USD} USD")
                    await update.message.reply_text(f"Paid {target}")
            except: pass
            return
        elif text.startswith("/broadcast"):
            msg = text.replace("/broadcast", "").strip()
            if msg: await update.message.reply_text(f"📢 **ENVIADO** (Simulado)")
            return

    # --- CAPTCHA & EMAIL ---
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

# =============================================================================
# 7. DASHBOARD (CORE UI)
# =============================================================================
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; lang = user.language_code
    
    if update.callback_query:
        msg = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        msg = update.message
        user_id = user.id

    user_data = await db.get_user(user_id)
    if user_data.get('ban_status', False):
        await msg.reply_text(get_text(lang, 'fraud_alert'), parse_mode="Markdown")
        return

    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    # VISUALIZACIÓN ELITE
    locked_balance = float(user_data.get('tokens_locked', 0))
    afk_msg = "Desbloquea Tokens con actividad constante." if locked_balance < 0.0001 else f"🔒 **{locked_balance:.4f} HIVE** en Vesting."
    
    current_e = int(user_data.get('energy', 0))
    max_e = MAX_ENERGY_BASE
    
    energy_percent_val = int((current_e / max_e) * 100)
    bar = render_progressbar(current_e, max_e)
    
    current_state = user_data.get('state', 1)
    
    # Calculamos el Score actual usando el ENGINE
    behavior_score = ENGINE.score(user_data)
    user_data['behavior_score'] = behavior_score # Actualizamos DB para mostrarlo
    
    progress_val = user_data.get('progress_to_next_state', 0)
    progress_bar = render_progressbar(progress_val, 100)
    
    hive_balance = float(user_data.get('nectar', 0))

    txt = get_text(lang, 'dashboard_body',
        state_name=STATES.get(current_state, "Unknown"),
        streak=user_data.get('streak', 0),
        behavior_score=f"{behavior_score:.1f}", # NUEVO: Muestra reputación
        progress_bar=progress_bar, 
        progress_percent=f"{progress_val:.1f}", 
        usd=user_data.get('usd_balance', 0.0), 
        hive=f"{hive_balance:.4f}", 
        locked_hive=f"{locked_balance:.4f}", 
        energy=energy_percent_val, 
        energy_bar=bar,
        afk_msg=afk_msg
    )
    
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="tier_1")], 
        [InlineKeyboardButton(get_text(lang, 'btn_progress'), callback_data="show_progress"), InlineKeyboardButton(get_text(lang, 'btn_mission'), callback_data="show_mission")],
        [InlineKeyboardButton(get_text(lang, 'btn_state'), callback_data="show_state")],
        [InlineKeyboardButton("🔓 RECLAMAR (VESTING)", callback_data="claim_afk")],
        [InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu"), InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu")]
    ]
    
    if update.callback_query:
        try: await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await msg.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# =============================================================================
# 8. MINERÍA & ACCIONES (INTEGRACIÓN COMPLETA ENGINE)
# =============================================================================

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data.get('ban_status', False): return

    locked = float(user_data.get('tokens_locked', 0))
    vesting_date = user_data.get('vesting_until')
    
    # Comprobación de Vesting (Elite v2)
    can_claim = False
    if vesting_date:
        try:
            v_date = dt.fromisoformat(vesting_date)
            if dt.utcnow() > v_date: can_claim = True
        except:
            can_claim = True # Si falla fecha, permitir (fail-safe)
    
    if locked > 0 and can_claim:
        user_data['nectar'] = float(user_data.get('nectar', 0)) + locked
        user_data['tokens_locked'] = 0.0
        # Reset vesting para el próximo ciclo
        user_data['vesting_until'] = (dt.utcnow() + timedelta(days=VESTING_DAYS)).isoformat()
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ +{locked:.4f} HIVE Liberados!", show_alert=True)
        await show_dashboard(update, context)
    elif locked > 0 and not can_claim:
        await query.answer(f"⏳ Tokens en Vesting hasta {vesting_date[:10]}", show_alert=True)
    else:
        await query.answer("❄️ No hay tokens bloqueados.", show_alert=True)

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ELITE MINING: Usa el Engine.score y Engine.reward en lugar de random simple.
    """
    query = update.callback_query; user_id = query.from_user.id
    user = query.from_user; lang = user.language_code
    
    user_data = await db.get_user(user_id)
    if user_data.get('ban_status', False): return
        
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: await query.answer("❄️ Enfriando...", show_alert=False); return
    context.user_data['last_mine_time'] = time.time()

    user_data = await calculate_user_state(user_data) 
    cost = MINING_COST_PER_TAP
    if user_data['energy'] < cost: await query.answer("🔋 Falta Energía.", show_alert=True); return

    user_data['energy'] -= cost
    
    # --- LOGICA ELITE V2 ---
    # 1. Calcular Multiplicadores de Equipo
    refs = len(user_data.get('referrals', []))
    swarm_mult = calculate_swarm_bonus(refs)
    
    # 2. Obtener Score de Comportamiento
    score = ENGINE.score(user_data)
    user_data['behavior_score'] = score
    
    # 3. Base Hard Money + Bonus de Estado
    base_gain = BASE_REWARD_PER_TAP * swarm_mult * (1 + (user_data.get('state', 1) * 0.1))
    
    # 4. Calcular Recompensa Real con Engine (Entropy + Spike)
    total_gain = ENGINE.reward(base_gain, score)
    
    # 5. Aplicar Anti-Fraude
    fraud_mult = 1.0
    if user_data.get('fraud_score', 0) > 20: fraud_mult = 0.5
    if user_data.get('fraud_score', 0) > 50: fraud_mult = 0.1
    
    final_gain = total_gain * fraud_mult
    
    # 6. ECONOMÍA DE BLOQUEO (LOCK RATIO)
    # Parte va a saldo libre, parte a bloqueado para vesting
    to_locked = final_gain * LOCK_RATIO
    to_free = final_gain - to_locked
    
    user_data['nectar'] = float(user_data.get('nectar', 0) + to_free)
    user_data['tokens_locked'] = float(user_data.get('tokens_locked', 0) + to_locked)
    
    # 7. Actualizar Progreso (Elite: Solo avanza si el Score es decente)
    if score > 2.0:
        # Progreso oculto + visible
        current_prog = user_data.get('progress_to_next_state', 0)
        gain_prog = 0.1 # Muy lento
        user_data['progress_to_next_state'] = min(100, current_prog + gain_prog)
        
        # Evolución de Estado
        if user_data['progress_to_next_state'] >= 100 and user_data['state'] < 5:
             user_data['state'] += 1
             user_data['progress_to_next_state'] = 0
             user_data['consistency'] += 10 # Bonus por subir nivel

    # Update timestamp y métricas
    user_data = await update_user_elite_metrics(user_data, activity_type="mine")
    await save_user_data(user_id, user_data)
    
    # Feedback Visual
    quality_msg = "⭐ Excelente" if score > 8 else ("🟢 Normal" if score > 4 else "⚠️ Baja")
    msg_txt = get_text(lang, 'mine_feedback', 
                       performance_msg=quality_msg, 
                       total_gain=f"{final_gain:.4f}",
                       free=f"{to_free:.4f}",
                       locked=f"{to_locked:.4f}")
    
    kb = [[InlineKeyboardButton("⛏️ MINAR (ENGINE ACTIVO)", callback_data="mine_click")], 
          [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️ Mining...")

# =============================================================================
# 9. MENÚS Y NAVEGACIÓN
# =============================================================================

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 1: ABIERTO - Con FaucetPay agregado"""
    query = update.callback_query
    lang = query.from_user.language_code
    
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("🪙 COINTIPLY", url=LINKS['COINTIPLY']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("💸 FREECASH", url=LINKS['FREECASH']), InlineKeyboardButton("🌟 SWAGBUCKS", url=LINKS['SWAGBUCKS'])],
        [InlineKeyboardButton("📉 EVERVE", url=LINKS['EVERVE']), InlineKeyboardButton("⛏️ MINAR (ENGINE)", callback_data="mine_click")],
        
        [InlineKeyboardButton("🟡 SIGUIENTE NIVEL (OPERADOR)", callback_data="tier_2")],
        [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **TIER 1: INICIACIÓN**\n\nGenera tokens y reputación con tareas simples.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    user_data = await db.get_user(user_id)
    
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
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    user_data = await db.get_user(user_id)
    
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
    await query.message.edit_text("🛰️ **VERIFICANDO CON ENGINE...**"); await asyncio.sleep(1.5)
    
    # Simulamos envío al admin
    if ADMIN_ID != 0:
        try: await context.bot.send_message(ADMIN_ID, f"📋 **TASK PENDING (ELITE)**\nUser: `{user_id}`\n`/approve_task {user_id}`")
        except: pass
    await query.message.edit_text("📝 **EN REVISIÓN**\nSe acreditará si tu consistencia es válida.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

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
    
    # Info adicional Elite
    score = user_data.get('behavior_score', 0)
    consistency = user_data.get('consistency', 0)
    
    txt = f"🚀 **PROGRESO ELITE**\n\nNivel: {STATES.get(state)}\nMeta: {STATES.get(state+1, 'MAX')}\n\n📊 **Métricas Ocultas:**\n• Reputación: {score:.1f}\n• Consistencia: {consistency:.1f}\n\n`{render_progressbar(progress, 100)}` {progress:.1f}%"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_mission_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🎯 **MISIÓN DIARIA**\n\nCompleta 2 tareas del Tier actual para subir tu Consistencia (+5 puntos)."
    kb = [[InlineKeyboardButton("IR A TAREAS", callback_data="tier_1")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_state_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🧬 **ESTADOS DE EVOLUCIÓN**\n\n1. Larva (Explorador)\n2. Obrero (Operador) - Requiere Reputación > 10\n3. Explorador (Insider) - Requiere Reputación > 30\n4. Guardian (Nodo)\n5. Genesis - Admin Level"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# =============================================================================
# 10. ENRUTADOR PRINCIPAL
# =============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data and user_data.get('ban_status', False) and data != "go_dashboard":
        await query.message.edit_text("⛔ Cuenta restringida.", parse_mode="Markdown"); return
    
    if data == "start_validation": await start_validation_flow(update, context); return
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; lang = query.from_user.language_code; await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown"); return

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

async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN no definido en variables de entorno.")
    else:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Command Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text("Hive Elite V2 Running.")))
        app.add_handler(CommandHandler("invite", invite_command))
        app.add_handler(CommandHandler("reset", reset_command))
        
        # Message Handlers
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, general_text_handler))
        
        # Callback Handler
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("🤖 HIVE ELITE V2 ENGINE STARTED...")
        app.run_polling()
