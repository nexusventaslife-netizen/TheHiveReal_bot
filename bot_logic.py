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
# 1. KERNEL & SEGURIDAD (V200.0 - ULTIMATE HIVE + PANDORA MERGE)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado.")
    ADMIN_ID = 0

# IMAGEN DE BIENVENIDA
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# ECONOMÍA "HARD MONEY" (PANDORA PROTOCOL)
# El valor emerge de la utilidad, no de la promesa.
LOCK_RATIO = 0.65           # 65% de lo minado se bloquea (Vesting)
INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     

# TOKENOMICS (HIVE/Token Utility)
MINING_COST_PER_TAP = 10     # Costo de energía
BASE_REWARD_PER_TAP = 0.15   # Recompensa base
REWARD_VARIABILITY = 0.2     # Variabilidad del caos

# ALGORITMO DE MINERÍA / ENERGÍA
MAX_ENERGY_BASE = 500       
ENERGY_REGEN_PER_SEC = 1            
AFK_CAP_HOURS = 6           
MINING_COOLDOWN = 0.8       # Más rápido, más adictivo
COST_ENERGY_REFILL = 200    

# ANTI-FRAUDE & ENGINE
MIN_TIME_PER_TASK = 15 
TASK_TIMESTAMPS_LIMIT = 5 

# ESCALAFÓN DE ROLES (EVOLUCIÓN ORGÁNICA)
# Estos son los niveles que el usuario verá y sentirá
ROLES = ["Larva", "Obrero", "Explorador", "Guardian", "Reina"]

# NIVELES DE ACCESO A TIERS SEGÚN ROL
TIER_ACCESS = {
    "Larva": 1,
    "Obrero": 1,      # Acceso Tier 1
    "Explorador": 2,  # Acceso Tier 2
    "Guardian": 3,    # Acceso Tier 3
    "Reina": 3        # Acceso Total
}

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES (ECOSYSTEM)
# -----------------------------------------------------------------------------
LINKS = {
    # TIER 1: CLICKS & JUEGOS (ACCESO OBRERO)
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'EVERVE': "https://everve.net/ref/1950045/",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    
    # TIER 2: PASIVOS & MICRO-WORK (ACCESO EXPLORADOR)
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # TIER 3: FINANZAS & ALTO VALOR (ACCESO GUARDIAN/REINA)
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend"
}

# -----------------------------------------------------------------------------
# 3. TEXTOS MULTI-IDIOMA (ADAPTATIVOS)
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **BIENVENIDO A THE ONE HIVE**\n"
            "──────────────────────────\n"
            "Hola, **{name}**. Estás entrando a una Colmena Viva.\n\n"
            "🧠 **TU CAMINO EVOLUTIVO**\n"
            "1. **LARVA:** Recién llegado. Sin acceso.\n"
            "2. **OBRERO:** Acceso a Tareas Básicas (Tier 1).\n"
            "3. **EXPLORADOR:** Acceso a Pasivos (Tier 2).\n"
            "4. **GUARDIAN:** Finanzas (Tier 3).\n"
            "5. **REINA:** Estatus Máximo.\n\n"
            "🛡️ **FASE 1: VERIFICACIÓN**\n"
            "👇 **INGRESA EL CÓDIGO** para validar tu humanidad:"
        ),
        'ask_terms': "✅ **ENLACE SEGURO**\n\n¿Aceptas recibir ofertas y monetizar tus datos?",
        'ask_email': "🤝 **CONFIRMADO**\n\n📧 Ingresa tu **EMAIL** para activar los pagos USD:",
        'ask_bonus': "🎉 **CUENTA LISTA**\n\n🎁 **MISIÓN ($0.05 USD):**\nRegístrate en el Partner y valida. Los usuarios constantes tienen prioridad.",
        'dashboard_body': (
            "🧬 **HIVE IDENTITY**\n"
            "👤 **Rol Actual:** {role} {cell_tag}\n"
            "🔥 **Racha:** {streak} días\n"
            "📊 **Reputación:** {behavior_score:.1f}/100\n"
            "──────────────────\n"
            "💰 **USD:** `${usd:.2f} USD`\n"
            "🍯 **NÉCTAR:** `{hive:.4f}`\n"
            "🔒 **Bloqueado (Vesting):** `{locked_hive:.4f}`\n"
            "⚡ **Energía:** `{energy_bar}` {energy}%\n"
            "──────────────────\n"
            "🌍 **Hive Global:** Nivel {global_lvl} | Salud {global_hp}%\n"
            "_{afk_msg}_"
        ),
        'mine_feedback': (
            "⛏️ **TRABAJO REGISTRADO**\n"
            "💪 **Esfuerzo:** {effort_msg}\n"
            "🍯 **Néctar:** +{gain} (Caos x{mult})\n"
            "📈 **Experiencia Oculta:** Aumentada\n"
            "🔒 **{locked_amt:.4f}** bloqueados para el futuro."
        ),
        'locked_tier': "🔒 **NIVEL BLOQUEADO**\n\nNecesitas ser **{required_role}** para acceder a esta zona.\n\n💡 *Sigue trabajando para evolucionar o adquiere el pase Reina.*",
        'btn_tasks': "🧠 TRABAJO (TIER 1)", 'btn_tier2': "📡 PASIVOS (TIER 2)", 'btn_tier3': "💎 FINANZAS (TIER 3)",
        'btn_state': "🧬 ESTADO", 'btn_shop': "🛒 TIENDA", 'btn_cell': "🦠 CÉLULA", 
        'btn_team': "👥 ENJAMBRE", 'btn_back': "🔙 VOLVER"
    },
    'en': {
        'welcome_caption': "Welcome to The One Hive...", 
        'dashboard_body': "Identity: {role}...",
        'locked_tier': "LOCKED TIER"
    }
}

# -----------------------------------------------------------------------------
# 4. PANDORA PSYCH-ENGINE (MOTOR LÓGICO SUPERIOR)
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

# --- MOTOR DE EVOLUCIÓN (ROLES) ---
def calculate_next_role(user_data):
    current_role = user_data.get('role', 'Larva')
    hidden_xp = user_data.get('hidden_progress', 0)
    
    # Umbrales de XP Oculta
    THRESHOLDS = {
        "Larva": 0,
        "Obrero": 500,
        "Explorador": 2500,
        "Guardian": 10000,
        "Reina": 50000
    }
    
    # Lógica de ascenso
    try:
        current_idx = ROLES.index(current_role)
    except:
        current_idx = 0
        
    if current_idx < len(ROLES) - 1:
        next_role_name = ROLES[current_idx + 1]
        req_xp = THRESHOLDS.get(next_role_name, 999999)
        
        if hidden_xp >= req_xp:
            return next_role_name
            
    return current_role

# --- MOTOR DE PUNTUACIÓN (SCORING) ---
def calculate_behavior_score(user_data):
    streak = user_data.get('streak_days', 0)
    spam = user_data.get('spam_score', 0)
    decay = user_data.get('role_decay', 0)
    
    base_score = 100.0
    
    # Bonificaciones
    base_score += (streak * 0.5)
    
    # Penalizaciones
    base_score -= (spam * 2.0)
    base_score -= (decay * 1.5)
    
    return max(0.0, min(100.0, base_score))

async def process_user_state(user_data):
    """Procesa regeneración de energía, AFK y evolución"""
    now_ts = time.time()
    last_update = user_data.get('last_update_ts', now_ts)
    elapsed = now_ts - last_update
    
    # 1. Regenerar Energía
    current_energy = user_data.get('energy', 500)
    max_e = user_data.get('max_energy', 500)
    
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN_PER_SEC))
        user_data['energy'] = int(new_energy)
    
    # 2. AFK Rewards (Economía Bloqueada)
    # Tasa muy baja para fomentar actividad real
    role_mult = (ROLES.index(user_data.get('role', 'Larva')) + 1) * 0.05
    afk_rate = 0.001 * role_mult
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    if afk_time > 60:
        # Lo generado AFK va DIRECTO a bloqueado (Hard Money)
        generated = afk_time * afk_rate
        user_data['locked_balance'] = float(user_data.get('locked_balance', 0)) + generated
        
    # 3. Decay (Si pasa mucho tiempo sin entrar)
    if elapsed > (24 * 3600 * 3): # 3 días inactivo
        user_data['role_decay'] = user_data.get('role_decay', 0) + 1
        # Penalización de XP oculta
        user_data['hidden_progress'] = max(0, user_data.get('hidden_progress', 0) - 50)
        
    user_data['last_update_ts'] = now_ts
    return user_data

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

    # Inicialización segura
    user_data = await db.get_user(user.id)
    if not user_data: # Fallback
        await db.add_user(user.id, user.first_name, user.username)
        user_data = await db.get_user(user.id)

    txt = get_text(lang, 'welcome_caption', name=user.first_name)
    
    captcha = generate_captcha()
    context.user_data['captcha'] = captcha
    code_message = f"🔐 **CÓDIGO DE ACTIVACIÓN**:\n\n`{captcha}`"

    kb = [[InlineKeyboardButton("▶️ INICIAR VALIDACIÓN", callback_data="start_validation")]]
    
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
        await query.message.edit_text("⛔ **ACCESO DENEGADO**\nDetectamos actividad inusual.", parse_mode="Markdown")
        return
    await query.answer("Ingresa el código del captcha abajo 👇")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    if user_data and user_data.get('ban_status', False): return
        
    # --- FLUJO USUARIO ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        # Al validar captcha, sube a OBRERO automáticamente
        if user_data.get('role') == 'Larva':
            user_data['role'] = 'Obrero'
            user_data['hidden_progress'] += 100
            await db.r.set(f"user:{user.id}", json.dumps(user_data))
            
        kb = [[InlineKeyboardButton("✅ ACEPTAR", callback_data="accept_legal")]]
        await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): 
                await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Email inválido.")
        return

    if user_data: await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD (IDENTITY CENTER)
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
    if not user_data: return

    # Procesar estado (Energía, AFK)
    user_data = await process_user_state(user_data)
    
    # Verificar Evolución
    new_role = calculate_next_role(user_data)
    if new_role != user_data['role']:
        user_data['role'] = new_role
        # Bonus por subir de nivel
        user_data['nectar'] += 100
        await context.bot.send_message(user_id, f"🧬 **MUTACIÓN COMPLETADA**\nHas evolucionado a **{new_role.upper()}**!")

    await db.r.set(f"user:{user_id}", json.dumps(user_data))
    
    # Datos Globales (Hive Mind)
    global_lvl = await db.r.get("hive:global:level") or 1
    global_hp = await db.r.get("hive:global:health") or 100
    
    # Visual
    locked = float(user_data.get('locked_balance', 0))
    afk_msg = "Trabaja para liberar tokens." if locked < 0.1 else f"🔒 **{locked:.4f}** se liberarán pronto."
    
    current_e = int(user_data.get('energy', 0))
    max_e = user_data.get('max_energy', 500)
    bar = render_progressbar(current_e, max_e)
    
    cell_tag = ""
    if user_data.get('cell_id'):
        cell_tag = "[CÉLULA ACTIVA]"

    txt = get_text(lang, 'dashboard_body',
        role=user_data.get('role', 'Larva').upper(),
        cell_tag=cell_tag,
        streak=user_data.get('streak_days', 0),
        behavior_score=user_data.get('behavior_score', 100),
        usd=user_data.get('usd_balance', 0.0),
        hive=user_data.get('nectar', 0.0),
        locked_hive=locked,
        energy=int((current_e / max_e) * 100),
        energy_bar=bar,
        global_lvl=global_lvl,
        global_hp=global_hp,
        afk_msg=afk_msg
    )
    
    # MENÚ ADAPTATIVO (Según ROL)
    role = user_data.get('role', 'Larva')
    access_lvl = TIER_ACCESS.get(role, 0)
    
    kb = []
    # Tier 1 (Siempre visible si es Obrero+)
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="tier_1")])
    
    # Tier 2 (Explorador+)
    if access_lvl >= 2:
        kb.append([InlineKeyboardButton(get_text(lang, 'btn_tier2'), callback_data="tier_2")])
    else:
        kb.append([InlineKeyboardButton("🔒 PASIVOS (Bloqueado)", callback_data="tier_2")])
        
    # Tier 3 (Guardian+)
    if access_lvl >= 3:
        kb.append([InlineKeyboardButton(get_text(lang, 'btn_tier3'), callback_data="tier_3")])
    else:
        kb.append([InlineKeyboardButton("🔒 FINANZAS (Bloqueado)", callback_data="tier_3")])

    kb.append([InlineKeyboardButton("⛏️ MINAR (TAP)", callback_data="mine_click")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_cell'), callback_data="cell_menu"), InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu")])
    
    if update.callback_query:
        try: await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await msg.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. ACCIONES: MINERÍA & CÉLULAS
# -----------------------------------------------------------------------------

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; lang = query.from_user.language_code
    
    user_data = await db.get_user(user_id)
    user_data = await process_user_state(user_data)
    
    # Cooldown Check
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: 
        await query.answer("❄️ Enfriando motor...", show_alert=False)
        return
    context.user_data['last_mine_time'] = time.time()

    if user_data['energy'] < MINING_COST_PER_TAP: 
        await query.answer("🔋 Falta Energía.", show_alert=True)
        return

    # Consumo Energía
    user_data['energy'] -= MINING_COST_PER_TAP
    
    # Cálculo de Recompensa (Caos + Rol)
    role_mult = (ROLES.index(user_data.get('role', 'Larva')) + 1) * 0.1
    variability = 1.0 + random.uniform(-REWARD_VARIABILITY, REWARD_VARIABILITY)
    
    total_reward = BASE_REWARD_PER_TAP * (1 + role_mult) * variability
    
    # ECONOMÍA PANDORA: BLOQUEO
    locked_amt = total_reward * LOCK_RATIO
    liquid_amt = total_reward - locked_amt
    
    user_data['nectar'] += liquid_amt
    user_data['locked_balance'] = float(user_data.get('locked_balance', 0)) + locked_amt
    
    # XP Oculta
    user_data['hidden_progress'] += random.uniform(1, 3)
    
    # Actualizar Hive Global
    await db.update_global_hive(total_reward)
    
    await db.r.set(f"user:{user_id}", json.dumps(user_data))
    
    msg_txt = get_text(lang, 'mine_feedback', 
                       effort_msg="Óptimo", 
                       gain=f"{liquid_amt:.4f}", 
                       mult=round(variability, 2),
                       locked_amt=locked_amt)
                       
    kb = [[InlineKeyboardButton("⛏️ TAP", callback_data="mine_click")], 
          [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    
    try: await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: await query.answer("⛏️")

async def cell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data.get('cell_id'):
        # Ya tiene célula -> Ver info
        cell = await db.get_cell(user_data['cell_id'])
        txt = f"🦠 **CÉLULA: {cell.get('name')}**\n\n👥 Miembros: {len(cell.get('members', []))}\n🔥 Sinergia: x{cell.get('synergy_level', 1.0)}"
        kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    else:
        # No tiene célula -> Crear o Unir
        txt = "🦠 **SISTEMA CELULAR**\n\nTrabajar en equipo aumenta la producción.\n\n¿Quieres crear tu propia célula?"
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
    cid = await db.create_cell(user_id, f"Cell {user_data['username']}")
    await db.r.set(f"user:{user_id}", json.dumps(user_data))
    
    await query.message.edit_text(f"✅ **CÉLULA CREADA**\nID: `{cid}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 8. MENÚS DE TAREAS (CONTROL DE TIERS)
# -----------------------------------------------------------------------------

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("🔙", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("👷 **ZONA OBRERA (TIER 1)**\nGenera polvo para empezar.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    
    if TIER_ACCESS.get(user_data.get('role'), 0) < 2:
        await query.answer("🔒 Requiere Rol EXPLORADOR", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("🔙", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔭 **ZONA EXPLORADOR (TIER 2)**\nIngresos pasivos activados.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    
    if TIER_ACCESS.get(user_data.get('role'), 0) < 3:
        await query.answer("🔒 Requiere Rol GUARDIAN", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton("🔥 BYBIT", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("🔙", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🛡️ **ZONA GUARDIAN (TIER 3)**\nAlta rentabilidad.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 9. OTROS MENÚS
# -----------------------------------------------------------------------------
async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = "🛒 **TIENDA DE LA COLMENA**\n\nAdquiere estatus o energía.\n\n👑 **PASE REINA:** Desbloquea todo.\n⚡ **RECARGA ENERGÍA:** 200 HIVE"
    kb = [[InlineKeyboardButton("⚡ RECARGAR (200 HIVE)", callback_data="buy_energy")],
          [InlineKeyboardButton("👑 PASE REINA ($10)", callback_data="buy_premium")],
          [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(f"💎 **MEMBRESÍA REINA**\n\nEnvía $10 USD a la wallet USDT (TRC20) y envía el hash.", parse_mode="Markdown")
    context.user_data['waiting_for_hash'] = True

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    kb = [[InlineKeyboardButton("🚀 RECLAMAR", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("✅ LISTO", callback_data="go_dashboard")]]
    await update.message.reply_text(get_text(lang, 'ask_bonus'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await query.message.edit_text(f"🔗 **ENJAMBRE**\n\nInvita obreros para fortalecer tu célula.\n\nLink:\n`{link}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 10. ENRUTADOR
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data
    
    handlers = {
        "go_dashboard": show_dashboard, 
        "mine_click": mining_animation, 
        "cell_menu": cell_menu,
        "create_cell_action": create_cell_action,
        "shop_menu": shop_menu, 
        "buy_premium": buy_premium_flow,
        "tier_1": tier1_menu, 
        "tier_2": tier2_menu, 
        "tier_3": tier3_menu, 
        "team_menu": team_menu
    }
    
    if data == "start_validation": await start_validation_flow(update, context); return
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; await query.message.edit_text(get_text(query.from_user.language_code, 'ask_email'), parse_mode="Markdown"); return
    
    if data == "buy_energy":
        user_id = query.from_user.id
        user_data = await db.get_user(user_id)
        if user_data['nectar'] >= 200:
            user_data['nectar'] -= 200
            user_data['energy'] = 500
            await db.r.set(f"user:{user_id}", json.dumps(user_data))
            await query.answer("⚡ Recargado!", show_alert=True)
            await show_dashboard(update, context)
        else:
            await query.answer("❌ Sin saldo", show_alert=True)
            return

    if data in handlers: await handlers[data](update, context)
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v200.0 - Ultimate")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    await u.message.reply_text("Broadcast sent.")
