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
# 1. KERNEL & CONFIGURACIÓN DEL SISTEMA
# =============================================================================
# Configuración del Logger para depuración
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# ID del Administrador (Seguridad)
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado correctamente en las variables de entorno.")
    ADMIN_ID = 0

# Recursos Visuales (Imágenes y Medios)
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# =============================================================================
# CONFIGURACIÓN DE ECONOMÍA (TOKENOMICS & HARD MONEY)
# =============================================================================
# Saldos iniciales
INITIAL_USD = 0.00      
BONUS_REWARD_USD = 0.05     
INITIAL_HIVE = 0.0

# Factor de Bloqueo (Vesting)
# El 65% de todo lo generado se bloquea para crear escasez y valor a largo plazo.
LOCK_RATIO = 0.65           

# Costos y Recompensas de Minería (Tap)
MINING_COST_PER_TAP = 10     # Costo de Energía por cada acción
BASE_REWARD_PER_TAP = 0.15   # Recompensa base en HIVE antes de multiplicadores
REWARD_VARIABILITY = 0.2     # Variabilidad del caos (+- 20%)

# Configuración de Energía
MAX_ENERGY_BASE = 500       
ENERGY_REGEN_PER_SEC = 1     # Regeneración por segundo
AFK_CAP_HOURS = 6            # Límite de horas para recompensa AFK
MINING_COOLDOWN = 0.8        # Tiempo entre clicks
COST_ENERGY_REFILL = 200     # Costo en HIVE para recargar energía

# Configuración Anti-Fraude
MIN_TIME_PER_TASK = 15       # Segundos mínimos para considerar una tarea válida
TASK_TIMESTAMPS_LIMIT = 5    # Cantidad de timestamps a guardar en memoria

# =============================================================================
# SISTEMA DE ROLES Y JERARQUÍA (EVOLUCIÓN)
# =============================================================================
ROLES = [
    "Larva", 
    "Obrero", 
    "Explorador", 
    "Guardian", 
    "Nodo", 
    "Reina"
]

# Niveles de acceso a los Tiers según el Rol
TIER_ACCESS = {
    "Larva": 0,       # Sin acceso a Tiers
    "Obrero": 1,      # Acceso Tier 1 (Clicks)
    "Explorador": 2,  # Acceso Tier 2 (Pasivos)
    "Guardian": 3,    # Acceso Tier 3 (Finanzas)
    "Nodo": 3,        # Acceso Tier 3 + Bonos
    "Reina": 4        # Acceso Total + Admin Panel
}

# =============================================================================
# 2. ARSENAL DE ENLACES (ECOSYSTEM) - LISTA COMPLETA
# =============================================================================
LINKS = {}

# --- TIER 1: CLICKS & JUEGOS ---
LINKS['VALIDATOR_MAIN'] = os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")
LINKS['ADBTC'] = "https://r.adbtc.top/3284589"
LINKS['FREEBITCOIN'] = "https://freebitco.in/?r=55837744"
LINKS['FAUCETPAY'] = "https://faucetpay.io/?r=2275014"
LINKS['COINTIPLY'] = "https://cointiply.com/r/jR1L6y"
LINKS['GAMEHAG'] = "https://gamehag.com/r/NWUD9QNR"
LINKS['EVERVE'] = "https://everve.net/ref/1950045/"
LINKS['FREECASH'] = "https://freecash.com/r/XYN98"
LINKS['SWAGBUCKS'] = "https://www.swagbucks.com/p/register?rb=226213635&rp=1"

# --- TIER 2: PASIVOS & MICRO-WORK ---
LINKS['HONEYGAIN'] = "https://join.honeygain.com/ALEJOE9F32"
LINKS['PACKETSTREAM'] = "https://packetstream.io/?psr=7hQT"
LINKS['PAWNS'] = "https://pawns.app/?r=18399810"
LINKS['TRAFFMONETIZER'] = "https://traffmonetizer.com/?aff=2034896"
LINKS['PAIDWORK'] = "https://www.paidwork.com/?r=nexus.ventas.life"
LINKS['SPROUTGIGS'] = "https://sproutgigs.com/?a=83fb1bf9"
LINKS['GOTRANSCRIPT'] = "https://gotranscript.com/r/7667434"
LINKS['KOLOTIBABLO'] = "http://getcaptchajob.com/30nrmt1xpj"
LINKS['TESTBIRDS'] = "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381"

# --- TIER 3: FINANZAS & ALTO VALOR ---
LINKS['VIP_OFFER_1'] = os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4")
LINKS['BYBIT'] = "https://www.bybit.com/invite?ref=BBJWAX4"
LINKS['PLUS500'] = "https://www.plus500.com/en-uy/refer-friend"
LINKS['NEXO'] = "https://nexo.com/ref/rbkekqnarx?src=android-link"
LINKS['REVOLUT'] = "https://revolut.com/referral/?referral-code=alejandroperdbhx"
LINKS['WISE'] = "https://wise.com/invite/ahpc/josealejandrop73"
LINKS['YOUHODLER'] = "https://app.youhodler.com/sign-up?ref=SXSSSNB1"
LINKS['AIRTM'] = "https://app.airtm.com/ivt/jos3vkujiyj"
LINKS['POLLOAI'] = "https://pollo.ai/invitation-landing?invite_code=wI5YZK"
LINKS['GETRESPONSE'] = "https://gr8.com//pr/mWAka/d"
LINKS['BCGAME'] = "https://bc.game/i-477hgd5fl-n/"
LINKS['BETFURY'] = "https://betfury.io/?r=6664969919f42d20e7297e29"

# =============================================================================
# 3. TEXTOS MULTI-IDIOMA (SISTEMA DE LOCALIZACIÓN)
# =============================================================================
TEXTS = {
    'es': {},
    'en': {}
}

# --- TEXTOS ESPAÑOL ---
TEXTS['es']['welcome_caption'] = (
    "🧬 **BIENVENIDO A THE ONE HIVE**\n"
    "──────────────────────────\n"
    "Hola, **{name}**. Estás entrando a una economía real basada en el esfuerzo humano.\n\n"
    "🧠 **TU ESTRATEGIA DE EVOLUCIÓN**\n"
    "1. **TIER 1 (OBRERO):** Tareas simples. Genera 'Dust' para empezar.\n"
    "2. **TIER 2 (EXPLORADOR):** Bloqueado. Requiere subir de nivel.\n"
    "3. **TIER 3 (GUARDIAN):** Finanzas. Alta rentabilidad.\n\n"
    "🛡️ **FASE 1: VERIFICACIÓN**\n"
    "👇 **INGRESA EL CÓDIGO** de seguridad para validar que no eres un robot:"
)

TEXTS['es']['ask_terms'] = (
    "✅ **ENLACE SEGURO ESTABLECIDO**\n\n"
    "¿Aceptas recibir ofertas exclusivas y monetizar tus datos de navegación?"
)

TEXTS['es']['ask_email'] = (
    "🤝 **VERIFICACIÓN CONFIRMADA**\n\n"
    "📧 Por favor, ingresa tu dirección de **EMAIL** para activar los pagos en USD:"
)

TEXTS['es']['ask_bonus'] = (
    "🎉 **CUENTA CONFIGURADA EXITOSAMENTE**\n\n"
    "🎁 **MISIÓN INICIAL ($0.05 USD):**\n"
    "Regístrate en nuestro Partner oficial y valida tu cuenta. Los usuarios constantes tienen prioridad en los pagos."
)

TEXTS['es']['btn_claim_bonus'] = "🚀 HACER MISIÓN AHORA"

TEXTS['es']['dashboard_body'] = (
    "🧬 **IDENTIDAD DE LA COLMENA**\n"
    "👤 **Rol Actual:** {role_name} {cell_tag}\n"
    "🔥 **Racha de Actividad:** {streak} días\n"
    "📈 **Comportamiento:** {behavior:.1f}/100\n"
    "──────────────────\n"
    "💰 **Saldo USD:** `${usd:.2f} USD`\n"
    "🍯 **Saldo HIVE:** `{hive:.4f}`\n"
    "🔒 **Bloqueado (Vesting):** `{locked_hive:.4f}`\n"
    "⚡ **Energía:** `{energy_bar}` {energy}%\n"
    "──────────────────\n"
    "🌍 **Estado Hive Global:** Nivel {g_lvl} | Salud {g_hp}%\n"
    "_{afk_msg}_"
)

TEXTS['es']['mine_feedback'] = (
    "⛏️ **ACCIÓN DE MINERÍA COMPLETADA**\n"
    "📊 **Rendimiento:** {performance_msg}\n"
    "🪙 **HIVE Generado:** +{gain}\n"
    "🔒 **Bloqueado (Futuro):** {locked_amt:.4f}\n"
    "🔓 **Progreso interno actualizado.**"
)

TEXTS['es']['shop_body'] = (
    "🏪 **MERCADO NEGRO DE LA COLMENA**\n"
    "Saldo Disponible: {hive} HIVE\n\n"
    "⚡ **RECARGAR ENERGÍA COMPLETA**\n"
    "Costo: 200 HIVE\n\n"
    "👑 **MEMBRESÍA REINA (PREMIUM) - $10 USD**\n"
    "(Desbloquea Tier 2 y 3 instantáneamente sin subir de nivel)"
)

TEXTS['es']['swarm_menu_body'] = (
    "🔗 **TU EQUIPO (ENJAMBRE)**\n\n"
    "En The One Hive no ganas por invitar gente inactiva.\n"
    "**Ganás únicamente cuando tus invitados TRABAJAN.**\n\n"
    "👥 **Obreros Activos:** {count}\n"
    "🚀 **Calidad de Red:** {quality}\n\n"
    "📌 **Tu Enlace de Reclutamiento:**\n`{link}`"
)

TEXTS['es']['fraud_alert'] = (
    "⚠️ **ALERTA DEL SISTEMA DE SEGURIDAD**\n\n"
    "Se han detectado patrones de actividad inusuales o inhumanos.\n"
    "El acceso ha sido restringido temporalmente por protección."
)

TEXTS['es']['locked_tier'] = (
    "🔒 **NIVEL DE ACCESO BLOQUEADO**\n\n"
    "Necesitas el rango **{required_state}** o tener Membresía Premium para acceder a este arsenal.\n\n"
    "💡 *Continúa trabajando en el nivel anterior o adquiere el pase en la Tienda.*"
)

# Botones Dashboard
TEXTS['es']['btn_tasks'] = "🧠 TIER 1 (WORK)"
TEXTS['es']['btn_tier2'] = "📡 TIER 2 (PASSIVE)"
TEXTS['es']['btn_tier3'] = "💎 TIER 3 (FINANCE)"
TEXTS['es']['btn_progress'] = "🚀 MI PROGRESO"
TEXTS['es']['btn_mission'] = "🎯 MISIÓN DIARIA"
TEXTS['es']['btn_state'] = "🧬 ESTADO"
TEXTS['es']['btn_shop'] = "🛒 TIENDA"
TEXTS['es']['btn_withdraw'] = "💸 RETIRAR FONDOS"
TEXTS['es']['btn_team'] = "👥 ENJAMBRE"
TEXTS['es']['btn_back'] = "🔙 VOLVER AL MENU"
TEXTS['es']['btn_cell'] = "🦠 CÉLULA (GUILD)"

# --- TEXTOS INGLÉS (FALLBACK) ---
TEXTS['en']['welcome_caption'] = "Welcome to The One Hive..." 
TEXTS['en']['ask_terms'] = "Accept terms?" 
TEXTS['en']['dashboard_body'] = "State: {role_name}..." 
TEXTS['en']['fraud_alert'] = "System Error."
TEXTS['en']['locked_tier'] = "🔒 **LOCKED TIER**"

# =============================================================================
# 4. MOTOR LÓGICO (PANDORA ENGINE) & HELPERS
# =============================================================================

def get_text(lang_code, key, **kwargs):
    """
    Recupera el texto en el idioma correcto y formatea las variables.
    """
    lang = 'es' if lang_code and 'es' in lang_code else 'en'
    # Fallback a español si no existe en inglés
    if lang not in TEXTS:
        lang = 'es'
    
    t_map = TEXTS.get(lang, TEXTS['es'])
    t = t_map.get(key, key)
    
    try: 
        return t.format(**kwargs)
    except: 
        return t

def generate_captcha(): 
    """Genera un código aleatorio simple para validación humana."""
    return f"HIVE-{random.randint(100, 999)}"

def render_progressbar(current, total, length=10):
    """
    Renderiza una barra de progreso visual con caracteres ASCII.
    Ejemplo: ██████░░░░
    """
    if total == 0: total = 1 
    percent = max(0, min(current / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "░" * empty

async def process_user_state(user_data):
    """
    NÚCLEO DEL ENGINE:
    Esta función recalcula el estado del usuario cada vez que interactúa.
    Maneja: Energía, Recompensas AFK, Decaimiento y Evolución.
    """
    now_ts = time.time()
    last_update = user_data.get('last_update_ts', now_ts)
    elapsed = now_ts - last_update
    
    # --- 1. Regeneración de Energía ---
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    if elapsed > 0:
        # Recupera energía basada en el tiempo transcurrido
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN_PER_SEC))
        user_data['energy'] = int(new_energy)
    
    # --- 2. AFK Rewards (Factor X - Hard Money) ---
    # Tasa muy reducida para evitar inflación, basada en el ROL
    role_idx = 0
    if user_data.get('role') in ROLES:
        role_idx = ROLES.index(user_data['role'])
    
    # Fórmula: (Indice de Rol + 1) * 0.0005 HIVE por segundo
    afk_rate = (role_idx + 1) * 0.0005 
    # Cap de tiempo AFK
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    if afk_time > 60: 
        # Lo generado en AFK va DIRECTO a Bloqueado (Vesting)
        # Esto incentiva entrar a la app para desbloquearlo
        generated_afk = afk_time * afk_rate
        user_data['locked_balance'] = float(user_data.get('locked_balance', 0)) + generated_afk
    
    # --- 3. Evolución de Rol (Hidden XP) ---
    hidden_xp = user_data.get('hidden_progress', 0)
    current_role = user_data.get('role', 'Larva')
    
    # Tabla de experiencia requerida para evolucionar
    XP_TABLE = {
        "Larva": 0,
        "Obrero": 200,
        "Explorador": 1000,
        "Guardian": 5000,
        "Nodo": 20000,
        "Reina": 100000
    }
    
    # Chequeo de subida de nivel
    try:
        curr_idx = ROLES.index(current_role)
        # Si no es el último rol...
        if curr_idx < len(ROLES) - 1:
            next_role = ROLES[curr_idx + 1]
            # Si tiene suficiente XP oculta...
            if hidden_xp >= XP_TABLE.get(next_role, 999999):
                user_data['role'] = next_role
                user_data['nectar'] += 100 # Bonus inmediato por subir de nivel
    except: 
        pass

    # Actualizar timestamp
    user_data['last_update_ts'] = now_ts
    return user_data

# --- SISTEMA DE PUNTUACIÓN (ANTIFRAUDE) ---
def check_scripting_speed(task_timestamps):
    """Detecta si las tareas se hacen humanamente posible o es un script."""
    if len(task_timestamps) < 3: return 0
    
    MIN_TIME = MIN_TIME_PER_TASK 
    risk_score_increase = 0
    
    # Analizar los últimos 3 tiempos
    if len(task_timestamps) >= 3:
        latest_stamps = task_timestamps[::-1] # Invertir para ver los últimos
        gap1 = latest_stamps[0] - latest_stamps[1]
        gap2 = latest_stamps[1] - latest_stamps[2]
        
        # Si ambos intervalos son menores al mínimo permitido...
        if gap1 < MIN_TIME and gap2 < MIN_TIME:
            risk_score_increase = 25 # Aumentar riesgo drásticamente
            
    return risk_score_increase

def update_fraud_score(user_data, activity_type="task_complete"):
    """Actualiza el puntaje de fraude del usuario."""
    current_score = user_data.get('fraud_score', 0)
    
    if activity_type == "task_complete":
        timestamps = user_data.get('task_timestamps', [])
        current_score += check_scripting_speed(timestamps)
        
    # Normalizar score entre 0 y 100
    user_data['fraud_score'] = min(100, max(0, current_score))
    
    # Auto-Ban si supera el umbral
    if user_data['fraud_score'] >= 80:
        user_data['ban_status'] = True
        
    return user_data

async def save_user_data(user_id, data):
    """Wrapper para guardar datos en Redis."""
    if hasattr(db, 'r') and db.r: 
        await db.r.set(f"user:{user_id}", json.dumps(data))

# =============================================================================
# 5. HANDLERS INICIALES (COMANDOS Y VALIDACIÓN)
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start: Punto de entrada."""
    user = update.effective_user
    lang = user.language_code
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    # Registrar usuario en DB
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Asegurar que el usuario existe y tiene datos
    user_data = await db.get_user(user.id)
    if not user_data:
        # Fallback de emergencia por si Redis falla
        await db.add_user(user.id, user.first_name, user.username)
        user_data = await db.get_user(user.id)

    # Generar Captcha
    txt = get_text(lang, 'welcome_caption', name=user.first_name)
    captcha = generate_captcha()
    context.user_data['captcha'] = captcha
    code_message = f"🔐 **CÓDIGO DE ACTIVACIÓN**:\n\n`{captcha}`"

    kb = [[InlineKeyboardButton("▶️ COMENZAR VALIDACIÓN", callback_data="start_validation")]]
    
    # Intentar enviar con foto, si falla, enviar texto
    try: 
        await update.message.reply_photo(photo=IMG_BEEBY, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error enviando foto: {e}")
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
    await update.message.reply_text(code_message, parse_mode="Markdown")

async def start_validation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cuando el usuario pulsa 'Comenzar Validación'"""
    query = update.callback_query
    user = query.from_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    if user_data.get('ban_status', False):
        await query.message.edit_text(get_text(lang, 'fraud_alert'), parse_mode="Markdown")
        return
        
    await query.answer("Ingresa el código del captcha.")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todo el texto que envía el usuario (Captchas, Emails, Comandos)"""
    text = update.message.text.strip()
    user = update.effective_user
    lang = user.language_code
    
    user_data = await db.get_user(user.id)
    if user_data and user_data.get('ban_status', False):
        await update.message.reply_text(get_text(lang, 'fraud_alert'), parse_mode="Markdown")
        return
        
    # --- COMANDOS ADMIN ---
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"):
            try:
                # Formato: /approve_task 123456789
                parts = text.split()
                if len(parts) > 1:
                    target = int(parts[1])
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
            except Exception as e:
                logger.error(f"Error admin command: {e}")
            return
        
    # --- FLUJO USUARIO: CAPTCHA ---
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        # Subir a Obrero automáticamente al validar (Onboarding)
        if user_data.get('role') == 'Larva':
            user_data['role'] = 'Obrero'
            user_data['hidden_progress'] += 100
            await save_user_data(user.id, user_data)
            
        kb = [[InlineKeyboardButton("✅ ACEPTAR / ACCEPT", callback_data="accept_legal")]]
        await update.message.reply_text(get_text(lang, 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # Reinicio forzado
    if text.upper() == "/START": 
        await start(update, context)
        return
    
    # --- FLUJO USUARIO: EMAIL ---
    if context.user_data.get('waiting_for_email'):
        if "@" in text and "." in text: # Validación simple
            if hasattr(db, 'update_email'): 
                await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: 
            await update.message.reply_text("⚠️ Email inválido. Intenta de nuevo.")
        return

    # Si no es nada de lo anterior y el usuario existe, mostrar panel
    if user_data: 
        await show_dashboard(update, context)

# =============================================================================
# 6. DASHBOARD (IDENTITY CENTER) - VISTA PRINCIPAL
# =============================================================================
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el panel principal con estadísticas y menús."""
    user = update.effective_user
    lang = user.language_code
    
    if update.callback_query:
        msg = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        msg = update.message
        user_id = user.id

    user_data = await db.get_user(user_id)
    if not user_data:
        return # Si falla DB

    if user_data.get('ban_status', False):
        await msg.reply_text(get_text(lang, 'fraud_alert'), parse_mode="Markdown")
        return

    # Procesar lógica de estado (Energía, AFK, Roles) antes de mostrar
    user_data = await process_user_state(user_data)
    await save_user_data(user_id, user_data)
    
    # --- PREPARACIÓN DE DATOS VISUALES ---
    locked_balance = float(user_data.get('locked_balance', 0))
    afk_msg = "Desbloquea Tokens con actividad." if locked_balance < 0.0001 else f"🔒 **{locked_balance:.4f} HIVE** (Bloqueados)."
    
    current_e = int(user_data.get('energy', 0))
    max_e = user_data.get('max_energy', 500)
    
    # Evitar división por cero
    if max_e == 0: max_e = 500

    energy_percent_val = int((current_e / max_e) * 100)
    bar = render_progressbar(current_e, max_e)
    
    hive_balance = float(user_data.get('nectar', 0))
    role_name = user_data.get('role', 'Larva')
    
    # Datos globales de la Hive
    g_stats = await db.get_hive_global_stats()
    
    cell_tag = ""
    if user_data.get('cell_id'):
        cell_tag = "[CÉLULA]"

    # Generar texto
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
    
    # --- CONSTRUCCIÓN DE LA INTERFAZ DE BOTONES ---
    kb = []
    
    # Fila 1: Tiers de Trabajo (Controlados por Rol)
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tasks'), callback_data="tier_1")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tier2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text(lang, 'btn_tier3'), callback_data="tier_3")])
    
    # Fila 2: Acciones Nucleares (Minería)
    kb.append([InlineKeyboardButton("⛏️ MINAR (TAP)", callback_data="mine_click")])
    
    # Fila 3: Social y Células
    kb.append([
        InlineKeyboardButton(get_text(lang, 'btn_cell'), callback_data="cell_menu"), 
        InlineKeyboardButton(get_text(lang, 'btn_team'), callback_data="team_menu")
    ])
    
    # Fila 4: Economía y Progreso
    kb.append([
        InlineKeyboardButton(get_text(lang, 'btn_shop'), callback_data="shop_menu"), 
        InlineKeyboardButton(get_text(lang, 'btn_progress'), callback_data="show_progress")
    ])
    
    if update.callback_query:
        # Usar editMessageText para evitar parpadeo y spam
        try: 
            await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception: 
            pass # Ignorar si el mensaje es idéntico
    else:
        await msg.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# =============================================================================
# 7. ACCIONES: MINERÍA (TAP) Y CÉLULAS
# =============================================================================

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el evento de 'Tap' o Minería Manual."""
    query = update.callback_query
    user_id = query.from_user.id
    user = query.from_user
    lang = user.language_code
    
    user_data = await db.get_user(user_id)
    user_data = await process_user_state(user_data)
    
    if user_data.get('ban_status', False): return
        
    # --- Anti-Autoclicker Cooldown ---
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN: 
        await query.answer("❄️ Enfriando motor...", show_alert=False)
        return
    context.user_data['last_mine_time'] = time.time()

    # --- Verificación de Energía ---
    cost = MINING_COST_PER_TAP
    if user_data['energy'] < cost: 
        await query.answer("🔋 Falta Energía.", show_alert=True)
        return

    # --- Procesar Minería ---
    user_data['energy'] -= cost
    
    # Fórmulas de Recompensa
    role_mult = (ROLES.index(user_data.get('role', 'Larva')) + 1) * 0.1
    # Variabilidad del Caos (Factor suerte)
    variability = 1.0 + random.uniform(-REWARD_VARIABILITY, REWARD_VARIABILITY)
    
    base_gain = BASE_REWARD_PER_TAP * (1 + role_mult)
    total_gain = base_gain * variability
    
    # Economía de Bloqueo (Factor X)
    locked_part = total_gain * LOCK_RATIO
    liquid_part = total_gain - locked_part
    
    # Asignar saldos
    user_data['nectar'] = float(user_data.get('nectar', 0) + liquid_part)
    user_data['locked_balance'] = float(user_data.get('locked_balance', 0) + locked_part)
    
    # Aumentar XP Oculta
    user_data['hidden_progress'] += 2.5
    
    # Guardar
    await save_user_data(user_id, user_data)
    await db.update_hive_global(total_gain) # Contribuir al enjambre global
    
    msg_txt = get_text(lang, 'mine_feedback', 
                       performance_msg="Óptimo", 
                       gain=f"{liquid_part:.4f}", 
                       mult=round(variability, 2),
                       locked_amt=locked_part)
                       
    kb = [[InlineKeyboardButton("⛏️ MINAR DE NUEVO", callback_data="mine_click")], 
          [InlineKeyboardButton(get_text(lang, 'btn_back'), callback_data="go_dashboard")]]
    
    try: 
        await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except: 
        await query.answer("⛏️ Recolectado")

# --- LÓGICA DE CÉLULAS (GUILDS) ---
async def cell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data.get('cell_id'):
        # Ver detalles de su célula
        cell = await db.get_cell(user_data['cell_id'])
        txt = (
            f"🦠 **CÉLULA: {cell.get('name')}**\n\n"
            f"👥 Miembros: {len(cell.get('members', []))}\n"
            f"🔥 Sinergia: Normal\n\n"
            "Trabajen juntos para aumentar el bono de producción."
        )
        kb = [[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    else:
        # Menú para crear
        txt = (
            "🦠 **SISTEMA CELULAR**\n\n"
            "Las células permiten multiplicar ganancias mediante trabajo cooperativo.\n\n"
            "¿Deseas fundar una nueva colonia?"
        )
        kb = [
            [InlineKeyboardButton("🆕 CREAR CÉLULA (500 HIVE)", callback_data="create_cell_action")],
            [InlineKeyboardButton("🔙", callback_data="go_dashboard")]
        ]
              
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def create_cell_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data['nectar'] < 500:
        await query.answer("❌ Faltan 500 HIVE", show_alert=True)
        return
        
    user_data['nectar'] -= 500
    cid = await db.create_cell(user_id, f"Cell-{user_data['username']}")
    await save_user_data(user_id, user_data)
    
    await query.message.edit_text(
        f"✅ **CÉLULA FUNDADA**\nID: `{cid}`\n\nAhora eres líder de tu propia colonia.", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]), 
        parse_mode="Markdown"
    )

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
    query = update.callback_query
    user_id = query.from_user.id
    lang = query.from_user.language_code
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
    query = update.callback_query
    user_id = query.from_user.id
    lang = query.from_user.language_code
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
    query = update.callback_query
    user_id = query.from_user.id
    
    # Animación de carga
    await query.message.edit_text("🛰️ **VERIFICANDO EN LA BLOCKCHAIN...**")
    await asyncio.sleep(1.5)
    
    # Notificar Admin si existe
    if ADMIN_ID != 0:
        try: 
            await context.bot.send_message(ADMIN_ID, f"📋 **TASK PENDING**\nUser: `{user_id}`\n`/approve_task {user_id}`")
        except: 
            pass
            
    await query.message.edit_text("📝 **SOLICITUD ENVIADA**\nSe acreditará tras revisión humana.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    lang = query.from_user.language_code
    
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
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    lang = query.from_user.language_code
    
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
    lang = update.effective_user.language_code
    txt = get_text(lang, 'ask_bonus')
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus'), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR", callback_data="verify_task_manual")]] 
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_progress_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
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
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # ANTI-FRAUDE CHECK GLOBAL
    if user_data and user_data.get('ban_status', False) and data != "go_dashboard":
        await query.message.edit_text("⛔ Cuenta restringida.", parse_mode="Markdown")
        return
    
    # ACTIONS:
    if data == "start_validation": 
        await start_validation_flow(update, context)
        return

    if data == "accept_legal": 
        context.user_data['waiting_for_terms'] = False
        context.user_data['waiting_for_email'] = True
        lang = query.from_user.language_code
        await query.message.edit_text(get_text(lang, 'ask_email'), parse_mode="Markdown")
        return

    # DICTIONARY DISPATCH
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
    
    if data in handlers: 
        await handlers[data](update, context)
    elif data == "buy_energy":
        # Acción específica de compra
        if float(user_data.get('nectar', 0)) >= COST_ENERGY_REFILL:
            user_data['nectar'] = float(user_data.get('nectar', 0)) - COST_ENERGY_REFILL
            user_data['energy'] = 500
            await save_user_data(user_id, user_data)
            await query.answer("⚡ Energía Recargada", show_alert=True)
            await show_dashboard(update, context)
        else: 
            await query.answer("❌ Saldo insuficiente", show_alert=True)
    elif data == "withdraw": 
        await query.answer("Mínimo $10 USD", show_alert=True)
    
    # Intentar cerrar la query para que el relojito de telegram no gire
    try: await query.answer()
    except: pass

async def help_command(u, c): 
    await u.message.reply_text("TheOneHive v300.0 - Full Arsenal + Factor X")

async def invite_command(u, c): 
    await team_menu(u, c)

async def reset_command(u, c): 
    c.user_data.clear()
    await u.message.reply_text("Reset OK.")

async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **ENVIADO:** {msg}")
