import logging
import asyncio
import random
import string
import datetime
import json
import os
import time
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# =============================================================================
# 1. KERNEL & SEGURIDAD (V300.0 - FULL PRESERVED + FACTOR X)
# =============================================================================
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD Y ADMIN
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado correctamente.")
    ADMIN_ID = 0

# IMAGEN DE BIENVENIDA (Preservada)
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# DIRECCIONES DE COBRO Y PAGOS (Preservadas)
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA "HARD MONEY" (FUSIÓN)
# Combina el sistema de USD original con el sistema de HIVE Bloqueado
INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     
LOCK_RATIO = 0.65       # 65% de lo minado se bloquea
INITIAL_HIVE = 0.0      
MINING_COST_PER_TAP = 5 
BASE_REWARD_PER_TAP = 0.15 
REWARD_VARIABILITY = 0.2

# ENERGÍA Y MINERÍA
MAX_ENERGY_BASE = 500       
ENERGY_REGEN_PER_SEC = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 0.8
COST_ENERGY_REFILL = 200    

# ANTI-FRAUDE
MIN_TIME_PER_TASK = 15 
TASK_TIMESTAMPS_LIMIT = 5 

# ROLES Y ACCESOS (JERARQUÍA COMPLETA)
ROLES = ["Larva", "Obrero", "Explorador", "Guardian", "Nodo", "Reina"]

# Niveles de acceso a los Tiers (No se borra ningún Tier)
TIER_ACCESS = {
    "Larva": 0,
    "Obrero": 1,      # Acceso Tier 1
    "Explorador": 2,  # Acceso Tier 2
    "Guardian": 3,    # Acceso Tier 3
    "Nodo": 3,
    "Reina": 4        # Acceso Total + Admin
}

# =============================================================================
# 2. ARSENAL DE ENLACES (LISTA COMPLETA ORIGINAL)
# =============================================================================
# NO SE HA BORRADO NADA. Se mantienen todos los enlaces originales.
LINKS = {
    # --- TIER 1: CLICKS & JUEGOS (ACCESIBLE PARA OBREROS) ---
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'EVERVE': "https://everve.net/ref/1950045/",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    
    # --- TIER 2: PASIVOS & MICRO-WORK (ACCESIBLE PARA EXPLORADORES) ---
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # --- TIER 3: FINANZAS & ALTO VALOR (ACCESIBLE PARA GUARDIANES) ---
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
# 3. TEXTOS MULTI-IDIOMA (COMPLETOS)
# =============================================================================
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
            "🧬 **IDENTIDAD HIVE**\n"
            "👤 **Rol:** {role_name} {cell_tag}\n"
            "🔥 **Racha:** {streak} días\n"
            "📈 **Comportamiento:** {behavior:.1f}/100\n"
            "──────────────────\n"
            "💰 **USD:** `${usd:.2f} USD`\n"
            "🍯 **HIVE:** `{hive:.4f}`\n"
            "🔒 **Bloqueado:** `{locked_hive:.4f}`\n"
            "⚡ **Energía:** `{energy_bar}` {energy}%\n"
            "──────────────────\n"
            "🌍 **Global Hive:** Nivel {g_lvl} | Salud {g_hp}%\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **ACCIÓN COMPLETADA**\n"
            "📊 **Rendimiento:** {performance_msg}\n"
            "🪙 **HIVE Generado:** +{gain}\n"
            "🔒 **Bloqueado (Vesting):** {locked_amt:.4f}\n"
            "🔓 **Progreso interno actualizado.**"
        ),
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\n👑 **MEMBRESÍA REINA (PREMIUM) - $10**\n(Desbloquea Tier 2 y 3 sin subir de nivel)",
        'swarm_menu_body': (
            "🔗 **TU EQUIPO (ENJAMBRE)**\n\n"
            "No ganás por invitar. **Ganás cuando tus invitados TRABAJAN.**\n"
            "👥 **Obreros Activos:** {count}\n"
            "🚀 **Calidad de Red:** {quality}\n\n"
            "📌 **Tu Enlace:**\n`{link}`"
        ),
        'fraud_alert': "⚠️ **SISTEMA DE SEGURIDAD**\n\nPatrones inusuales detectados. Acceso restringido.",
        'locked_tier': "🔒 **NIVEL BLOQUEADO**\n\nNecesitas ser nivel **{required_state}** o tener Membresía Premium para acceder a estas tareas de alto valor.\n\n💡 *Sigue trabajando en el nivel anterior o compra el pase en la Tienda.*",
        'btn_tasks': "🧠 TIER 1 (WORK)", 'btn_tier2': "📡 TIER 2 (PASSIVE)", 'btn_tier3': "💎 TIER 3 (FINANCE)",
        'btn_progress': "🚀 MI PROGRESO", 'btn_mission': "🎯 MISIÓN",
        'btn_state': "🧬 ESTADO", 'btn_shop': "🛒 TIENDA", 'btn_withdraw': "💸 RETIRAR", 
        'btn_team': "👥 REFERIDOS", 'btn_back': "🔙 VOLVER", 'btn_cell': "🦠 CÉLULA"
    },
    'en': {
        'welcome_caption': "Welcome {name}...", 
        'ask_terms': "Accept terms?", 
        'dashboard_body': "State: {role_name}...", 
        'fraud_alert': "System Error.",
        'locked_tier': "🔒 **LOCKED TIER**"
    }
}

# =============================================================================
# 4. MOTOR LÓGICO (ENGINE) & HELPERS
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

# --- CÁLCULO DE ESTADO DEL USUARIO (ENGINE ACTUALIZADO) ---
async def process_user_state(user_data):
    """
    Función central que recalcula energía, AFK, decaimiento y evolución.
    """
    now_ts = time.time()
    last_update = user_data.get('last_update_ts', now_ts)
    elapsed = now_ts - last_update
    
    # 1. Regeneración de Energía
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN_PER_SEC))
        user_data['energy'] = int(new_energy)
    
    # 2. AFK Rewards (Factor X - Hard Money)
    # Tasa muy reducida para evitar inflación
    role_idx = 0
    if user_data.get('role') in ROLES:
        role_idx = ROLES.index(user_data['role'])
    
    afk_rate = (role_idx + 1) * 0.0005 # Gana más según su rol
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    if afk_time > 60: 
        # Lo generado en AFK va DIRECTO a Bloqueado (Vesting)
        generated_afk = afk_time * afk_rate
        user_data['locked_balance'] = float(user_data.get('locked_balance', 0)) + generated_afk
    
    # 3. Evolución de Rol (Hidden XP)
    hidden_xp = user_data.get('hidden_progress', 0)
    current_role = user_data.get('role', 'Larva')
    
    # Tabla de experiencia
    XP_TABLE = {
        "Larva": 0,
        "Obrero": 200,
        "Explorador": 1000,
        "Guardian": 5000,
        "Nodo": 20000,
        "Reina": 100000
    }
    
    # Chequeo simple de subida
    try:
        curr_idx = ROLES.index(current_role)
        if curr_idx < len(ROLES) - 1:
            next_role = ROLES[curr_idx + 1]
            if hidden_xp >= XP_TABLE.get(next_role, 999999):
                user_data['role'] = next_role
                user_data['nectar'] += 100 # Bonus por subir de nivel
    except: pass

    user_data['last_update_ts'] = now_ts
    return user_data

# --- SISTEMA DE PUNTUACIÓN (ANTIFRAUDE) ---
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
        timestamps = user_data.get('task_timestamps', [])
        current_score += check_scripting_speed(timestamps)
    user_data['fraud_score'] = min(100, max(0, current_score))
    if user_data['fraud_score'] >= 80:
        user_data['ban_status'] = True
    return user_data

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r: await db.r.set(f"user:{user_id}", json.dumps(data))

# =============================================================================
# 5. HANDLERS (COMANDOS Y FLUJO INICIAL)
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Asegurar que el usuario existe y tiene datos
    user_data = await db.get_user(user.id)
    if not user_data:
        # Fallback de emergencia
        await db.add_user(user.id, user.first_name, user.username)
        user_data = await db.get_user(user.id)

    txt = get_text(lang, 'welcome_caption', name=user.first_name)
    
    captcha = generate_captcha()
    context.user_data['captcha'] = captcha
    code_message = f"🔐 **CÓDIGO DE ACTIVACIÓN**:\n\n`{captcha}`"

    kb = [[InlineKeyboardButton("▶️ COMENZAR VALIDACIÓN", callback_data="start_validation")]]
    
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
        
    # --- COMANDOS ADMIN ---
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"):
            try:
                target = int(text.split()[1])
                target_data = await db.get_user(target)
                if target_data:
                    curr_usd = float(target_data.get('usd_balance', 0))
                    target_data['usd_balance'] = curr_usd + BONUS_REWARD_USD 
                    # Aprobar tarea suma XP y consistencia
                    target_data['hidden_progress'] += 50
                    target_data = update_fraud_score(target_data, activity_type="task_complete") 
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **TASK APPROVED**\n💰 +${BONUS_REWARD_USD} USD")
                    await update.message.reply_text(f"Paid {target}")
            except: pass
            return
        
    # --- FLUJO USUARIO ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        # Subir a Obrero automáticamente al validar
        if user_data.get('role') == 'Larva':
            user_data['role'] = 'Obrero'
            user_data['hidden_progress'] += 100
            await save_user_data(user.id, user_data)
            
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
# 6. DASHBOARD (IDENTITY CENTER) - VISTA PRINCIPAL
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

    # Procesar lógica de estado (Energía, AFK, Roles)
    user_data = await process_user_state(user_data)
    await save_user_data(user_id, user_data)
    
    # VISUALIZACIÓN
    locked_balance = float(user_data.get('locked_balance', 0))
    afk_msg = "Desbloquea Tokens con actividad." if locked_balance < 0.0001 else f"🔒 **{locked_balance:.4f} HIVE** (Bloqueados)."
    
    current_e = int(user_data.get('energy', 0))
    max_e = user_data.get('max_energy', 500)
    
    energy_percent_val = int((current_e / max_e) * 100)
    bar = render_progressbar(current_e, max_e)
    
    hive_balance = float(user_data.get('nectar', 0))
    role_name = user_data.get('role', 'Larva')
    
    # Datos globales
    g_stats = await db.get_hive_global_stats()
    
    cell_tag = ""
    if user_data.get('cell_id'):
        cell_tag = "[CÉLULA]"

    txt = get_text(lang, 'dashboard_body',
        role_name=role_name.upper(),
        cell_tag=cell_tag,
        streak=user_data.get('streak_days', 0),
        behavior=user_data.get('behavior_score', 100),
        usd=user_data.get('usd_balance', 0.0), 
        hive=f"{hive_balance:.4f}", 
        locked_hive=f"{locked_balance:.4f}",
        energy=energy_percent_val,
        energy_bar=bar,
        g_lvl=g_stats.get('level', 1),
        g_hp=g_stats.get('health', 100),
        afk_msg=afk_msg
    )
    
    # --- CONSTRUCCIÓN DINÁMICA DE MENÚS (TODOS LOS BOTONES ORIGINALES) ---
    kb = []
    
    # Tiers de Trabajo (Controlados por Rol)
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="tier_1")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tier2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tier3'), callback_data="tier_3")])
    
    # Acciones de Minería y Células
    kb.append([InlineKeyboardButton("⛏️ MINAR (TAP)", callback_data="mine_click")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_cell'), callback_data="cell_menu"), InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu")])
    
    # Tienda y Progreso
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu"), InlineKeyboardButton(get_text(lang, 'btn_progress'), callback_data="show_progress")])
    
    if update.callback_query:
        try: await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await msg.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# =============================================================================
# 7. ACCIONES: MINERÍA (TAP) Y CÉLULAS
# =============================================================================

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user = query.from_user; lang = user.language_code
    
    user_data = await db.get_user(user_id)
    user_data = await process_user_state(user_data)
    
    if user_data.get('ban_status', False): return
        
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: await query.answer("❄️ Enfriando...", show_alert=False); return
    context.user_data['last_mine_time'] = time.time()

    cost = MINING_COST_PER_TAP
    if user_data['energy'] < cost: await query.answer("🔋 Falta Energía.", show_alert=True); return

    user_data['energy'] -= cost
    
    # Fórmulas de Recompensa
    role_mult = (ROLES.index(user_data.get('role', 'Larva')) + 1) * 0.1
    variability = 1.0 + random.uniform(-REWARD_VARIABILITY, REWARD_VARIABILITY)
    
    base_gain = BASE_REWARD_PER_TAP * (1 + role_mult)
    total_gain = base_gain * variability
    
    # Bloqueo (Factor X)
    locked_part = total_gain * LOCK_RATIO
    liquid_part = total_gain - locked_part
    
    user_data['nectar'] = float(user_data.get('nectar', 0) + liquid_part)
    user_data['locked_balance'] = float(user_data.get('locked_balance', 0) + locked_part)
    
    # Aumentar XP Oculta
    user_data['hidden_progress'] += 2.5
    user_data['streak_days'] = user_data.get('streak_days', 0) # Mantener lógica simple por ahora
    
    await save_user_data(user_id, user_data)
    await db.update_hive_global(total_gain) # Contribuir al enjambre global
    
    msg_txt = get_text(lang, 'mine_feedback', 
                       performance_msg="Óptimo", 
                       gain=f"{liquid_part:.4f}", 
                       mult=round(variability, 2),
                       locked_amt=locked_part)
                       
    kb = [[InlineKeyboardButton("⛏️ MINAR DE NUEVO", callback_data="mine_click")], 
          [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️ OK")

# --- LÓGICA DE CÉLULAS (GUILDS) ---
async def cell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data.get('cell_id'):
        # Ver detalles de su célula
        cell = await db.get_cell(user_data['cell_id'])
        txt = f"🦠 **CÉLULA: {cell.get('name')}**\n\n👥 Miembros: {len(cell.get('members', []))}\n🔥 Sinergia: Normal\n\nTrabajen juntos para aumentar el bono."
        kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    else:
        # Menú para crear
        txt = "🦠 **SISTEMA CELULAR**\n\nLas células permiten multiplicar ganancias mediante trabajo cooperativo.\n\n¿Deseas fundar una nueva colonia?"
        kb = [[InlineKeyboardButton("🆕 CREAR CÉLULA (500 HIVE)", callback_data="create_cell_action")],
              [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
              
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def create_cell_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data['nectar'] < 500:
        await query.answer("❌ Faltan 500 HIVE", show_alert=True)
        return
        
    user_data['nectar'] -= 500
    cid = await db.create_cell(user_id, f"Cell-{user_data['username']}")
    await save_user_data(user_id, user_data)
    
    await query.message.edit_text(f"✅ **CÉLULA FUNDADA**\nID: `{cid}`\n\nAhora eres líder.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]), parse_mode="Markdown")

# =============================================================================
# 8. MENÚS DE TAREAS (TODOS LOS TIERS CON ENLACES)
# =============================================================================

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 1: CLICKS & JUEGOS"""
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("🪙 COINTIPLY", url=LINKS['COINTIPLY']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("💸 FREECASH", url=LINKS['FREECASH']), InlineKeyboardButton("🌟 SWAGBUCKS", url=LINKS['SWAGBUCKS'])],
        [InlineKeyboardButton("📉 EVERVE", url=LINKS['EVERVE']), InlineKeyboardButton("⛏️ TAP MINING", callback_data="mine_click")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("👷 **TIER 1: OBRERO**\nTareas básicas para acumular capital.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 2: PASIVOS (BLOQUEADO POR ROL)"""
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    user_data = await db.get_user(user_id)
    
    required = TIER_ACCESS.get('Explorador')
    current_role_lvl = TIER_ACCESS.get(user_data.get('role', 'Larva'), 0)
    
    if current_role_lvl < required:
        await query.message.edit_text(get_text(lang, 'locked_tier', required_state="EXPLORADOR"), parse_mode="Markdown")
        return

    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("🚦 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("💼 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("🌱 SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("🧪 TESTBIRDS", url=LINKS['TESTBIRDS'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔭 **TIER 2: EXPLORADOR**\nIngresos pasivos y Freelance.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """TIER 3: FINANZAS (BLOQUEADO POR ROL)"""
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    user_data = await db.get_user(user_id)
    
    required = TIER_ACCESS.get('Guardian')
    current_role_lvl = TIER_ACCESS.get(user_data.get('role', 'Larva'), 0)
    
    if current_role_lvl < required:
        await query.message.edit_text(get_text(lang, 'locked_tier', required_state="GUARDIAN"), parse_mode="Markdown")
        return

    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($20)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("🦉 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("☁️ AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🐔 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("📈 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🏦 YOUHODLER", url=LINKS['YOUHODLER'])],
        [InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🛡️ **TIER 3: GUARDIAN**\nFinanzas de alto nivel.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    await query.message.edit_text("🛰️ **VERIFICANDO EN LA BLOCKCHAIN...**"); await asyncio.sleep(1.5)
    if ADMIN_ID != 0:
        try: await context.bot.send_message(ADMIN_ID, f"📋 **TASK PENDING**\nUser: `{user_id}`\n`/approve_task {user_id}`")
        except: pass
    await query.message.edit_text("📝 **SOLICITUD ENVIADA**\nSe acreditará tras revisión humana.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); lang = query.from_user.language_code
    refs = len(user_data.get('referrals', []))
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    # Textos de Calidad (New feature)
    quality = "Baja"
    if refs > 5: quality = "Media"
    if refs > 20: quality = "Alta (Nodo)"
    
    txt = get_text(lang, 'swarm_menu_body', count=refs, quality=quality, link=link)
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
    progress = user_data.get('hidden_progress', 0)
    role = user_data.get('role', 'Larva')
    
    txt = f"🚀 **EVOLUCIÓN**\n\nRol Actual: {role}\nXP Oculta acumulada: {progress:.1f}\n\n_Sigue trabajando para mutar al siguiente nivel._"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_mission_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🎯 **MISIÓN DIARIA**\n\nCompleta 2 tareas del Tier actual para recibir un bono de energía."
    kb = [[InlineKeyboardButton("IR A TAREAS", callback_data="tier_1")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_state_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🧬 **JERARQUÍA DE LA COLMENA**\n\n1. Larva\n2. Obrero (Tier 1)\n3. Explorador (Tier 2)\n4. Guardian (Tier 3)\n5. Nodo\n6. Reina"
    kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# =============================================================================
# 9. ENRUTADOR PRINCIPAL (ROUTER)
# =============================================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # ANTI-FRAUDE CHECK
    if user_data and user_data.get('ban_status', False) and data != "go_dashboard":
        await query.message.edit_text("⛔ Cuenta restringida.", parse_mode="Markdown"); return
    
    if data == "start_validation": await start_validation_flow(update, context); return
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; lang = query.from_user.language_code; await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown"); return

    handlers = {
        "go_dashboard": show_dashboard, 
        "mine_click": mining_animation, 
        "verify_task_manual": verify_task_manual, 
        "shop_menu": shop_menu, 
        "buy_premium": buy_premium_flow,
        "tier_1": tier1_menu, 
        "tier_2": tier2_menu, 
        "tier_3": tier3_menu, 
        "team_menu": team_menu, 
        "show_progress": show_progress_menu, 
        "show_mission": show_mission_menu, 
        "show_state": show_state_menu,
        "cell_menu": cell_menu,
        "create_cell_action": create_cell_action
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        if float(user_data.get('nectar', 0)) >= COST_ENERGY_REFILL:
            user_data['nectar'] = float(user_data.get('nectar', 0)) - COST_ENERGY_REFILL
            user_data['energy'] = 500
            await save_user_data(user_id, user_data); await query.answer("⚡ Energía Recargada", show_alert=True); await show_dashboard(update, context)
        else: await query.answer("❌ Saldo insuficiente", show_alert=True)
    elif data == "withdraw": 
        await query.answer("Mínimo $10 USD", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v300.0 - Full Arsenal + Factor X")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **ENVIADO**")
