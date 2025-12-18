import logging
import asyncio
import random
import time
import math
import statistics
import os
import json
from datetime import datetime
from typing import Tuple, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# ==============================================================================
# CONFIGURACIÓN DEL GAMEPLAY & EQUILIBRIO (V200.0)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# --- IDS & WALLETS ---
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except:
    ADMIN_ID = 0

CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_ADDRESS_PENDING")

# --- ARSENAL DE ENLACES (TIERS 1, 2, 3) ---
# NO BORRAR NADA - ESTOS SON TUS ACTIVOS DE INGRESOS
LINKS = {
    # TIER 1: TRÁFICO Y MICRO-TAREAS (Bajo valor, alto volumen)
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'EVERVE': "https://everve.net/ref/1950045/",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    
    # TIER 2: BANDA ANCHA Y PROCESAMIENTO (Valor medio, pasivo)
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # TIER 3: FINANZAS Y HIGH-TICKET (Alto valor, CPA puro)
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

# --- IMÁGENES Y MEDIA ---
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- MECÁNICAS DE JUEGO (GAME DESIGN) ---

# JERARQUÍA DE ROLES
# Cada rol desbloquea más capacidad de energía y acceso a Tiers superiores
ROLES_CONFIG = {
    "LARVA":      {"xp": 0,     "max_energy": 300, "regen": 0.5, "tiers": [1]},
    "OBRERO":     {"xp": 500,   "max_energy": 500, "regen": 0.8, "tiers": [1, 2]},
    "EXPLORADOR": {"xp": 1500,  "max_energy": 800, "regen": 1.0, "tiers": [1, 2, 3]},
    "GUARDIAN":   {"xp": 3500,  "max_energy": 1200,"regen": 1.2, "tiers": [1, 2, 3]},
    "NODO":       {"xp": 7000,  "max_energy": 2000,"regen": 1.5, "tiers": [1, 2, 3]},
    "GENESIS":    {"xp": 15000, "max_energy": 5000,"regen": 3.0, "tiers": [1, 2, 3]}
}
ROLES_LIST = list(ROLES_CONFIG.keys())

# ECONOMÍA
BASE_MINING_REWARD = 0.50   # Néctar base por click
ENERGY_COST_PER_TAP = 10    # Energía consumida por click
COST_FULL_RECHARGE = 200    # Costo en Néctar para llenar tanque
OXYGEN_DECAY_RATE = 5.0     # % de oxígeno perdido por hora de inactividad

# ==============================================================================
# ALGORITMOS MATEMÁTICOS (EL "FACTOR X")
# ==============================================================================

def calculate_bio_rhythm(timestamps: List[float]) -> Tuple[float, str]:
    """
    ALGORITMO DE ENTROPÍA:
    Analiza si el usuario es humano o máquina basándose en la varianza temporal.
    
    - Varianza baja (clicks cada 1.00s exactos) = BOT
    - Varianza alta (clicks caóticos) = HUMANO NORMAL
    - Varianza media rítmica (Flow) = HUMANO EXPERTO
    """
    if len(timestamps) < 4: 
        return 1.0, "🔵 Calibrando..."
    
    # Calcular intervalos (Deltas)
    intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    
    # Estadística básica
    try:
        avg = statistics.mean(intervals)
        stdev = statistics.stdev(intervals)
    except:
        return 1.0, "⚪ Neutro"
        
    if avg == 0: return 0.1, "🔴 ERROR"
    
    # Coeficiente de Variación (CV)
    cv = stdev / avg 
    
    # LÓGICA DE DETECCIÓN
    if cv < 0.05: 
        # Demasiado perfecto. Castigo masivo.
        return 0.1, "🔴 ROBÓTICO (Penalizado)" 
    elif 0.05 <= cv <= 0.25: 
        # El "Flow State" humano. Premio.
        return 1.3, "🌊 FLUJO PERFECTO (Bonus x1.3)"
    elif cv > 1.0:
        # Demasiado lento/distraído.
        return 0.8, "💤 Lento"
    else:
        # Humano normal
        return 1.0, "🟢 Humano"

async def process_biological_update(user: dict) -> dict:
    """
    Actualiza el estado biológico del usuario:
    - Regenera Energía basada en el tiempo y el Rol.
    - Decae el Oxígeno si ha estado inactivo.
    - Calcula si debe subir de Rango/Rol.
    """
    now = time.time()
    last_ts = user.get('last_update_ts', now)
    elapsed = now - last_ts
    
    # 1. Obtener Configuración del Rol Actual
    role_name = user.get('role', 'LARVA')
    config = ROLES_CONFIG.get(role_name, ROLES_CONFIG['LARVA'])
    
    # 2. Regenerar Energía
    if elapsed > 0:
        regen_amount = elapsed * config['regen']
        user['energy'] = min(config['max_energy'], user['energy'] + int(regen_amount))
        
    # 3. Decaer Oxígeno (Mecánica de Retención)
    # Si pasa más de 1 hora (3600s), empieza a perder eficiencia.
    if elapsed > 3600:
        hours_inactive = elapsed / 3600
        decay = hours_inactive * OXYGEN_DECAY_RATE
        # El oxígeno no baja de 10%
        user['oxygen'] = max(10.0, user.get('oxygen', 100.0) - decay)
        
    # 4. Chequear Evolución de Rol
    current_xp = user.get('role_xp', 0)
    
    # Buscar el rol más alto posible para su XP
    new_role = role_name
    for r_name, r_conf in ROLES_CONFIG.items():
        if current_xp >= r_conf['xp']:
            new_role = r_name
        else:
            break
            
    if new_role != role_name:
        user['role'] = new_role
        # Bonus por subir de nivel: Energía llena
        user['energy'] = ROLES_CONFIG[new_role]['max_energy']
        user['max_energy'] = ROLES_CONFIG[new_role]['max_energy']
        
    # Guardar timestamps
    user['last_update_ts'] = now
    
    return user

# ==============================================================================
# HANDLERS: FLUJO DE INICIO Y VERIFICACIÓN
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start: Punto de entrada."""
    user = update.effective_user
    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() else None
    
    # Crear usuario en DB
    await db.create_user(user.id, user.first_name, user.username, referrer_id)
    
    # Generar Captcha Visual (Texto simple por ahora)
    captcha = f"HIVE-{random.randint(100, 999)}"
    context.user_data['captcha'] = captcha
    
    txt = (
        f"🧬 **PROTOCOLO PANDORA: HIVE GENESIS**\n"
        f"────────────────────────\n"
        f"Saludos, **{user.first_name}**.\n\n"
        "Has sido seleccionado para integrarte a la Colmena.\n"
        "A diferencia de otros sistemas, aquí tu valor biológico importa.\n\n"
        "1. **Mantén tu Oxígeno:** Si te desconectas, tu eficiencia cae.\n"
        "2. **Crea Células:** La soledad es ineficiente. Únete a otros.\n"
        "3. **Evoluciona:** De Larva a Génesis.\n\n"
        "🛡️ **PROTOCOLO DE SEGURIDAD**\n"
        f"Digita este código para sincronizarte:\n`{captcha}`"
    )
    
    try:
        await update.message.reply_photo(IMG_BEEBY, caption=txt, parse_mode="Markdown")
    except:
        await update.message.reply_text(txt, parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todo el texto que envía el usuario (Captcha, Email, Comandos ocultos)."""
    text = update.message.text.strip()
    user = update.effective_user
    
    # 1. VERIFICACIÓN DE CAPTCHA
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None # Limpiar
        
        kb = [[InlineKeyboardButton("✅ ACEPTAR CONEXIÓN NEURONAL", callback_data="accept_legal")]]
        await update.message.reply_text(
            "✅ **IDENTIDAD CONFIRMADA**\n\n"
            "El sistema requiere acceso para monetizar tu actividad en la red.\n"
            "¿Aceptas los términos del Enjambre?",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
        return
        
    # 2. VERIFICACIÓN DE EMAIL (Para pagos CPA)
    if context.user_data.get('waiting_for_email'):
        if "@" in text and "." in text:
            await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            
            # Bono inmediato por completar registro
            user_db = await db.get_user(user.id)
            user_db['nectar'] += 100
            await db.save_user(user.id, user_db)
            
            kb = [[InlineKeyboardButton("🚀 ENTRAR AL NÚCLEO", callback_data="go_dashboard")]]
            await update.message.reply_text(
                "🎉 **SINCRONIZACIÓN COMPLETA**\n\n"
                "Has recibido **+100 Néctar** de bienvenida.\n"
                "Tu viaje evolutivo comienza ahora.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ Formato inválido. Ingresa un email real.")
        return

    # Si el usuario ya está registrado y escribe algo random, lo mandamos al dashboard
    user_data = await db.get_user(user.id)
    if user_data:
        await show_dashboard(update, context)

# ==============================================================================
# HANDLERS: DASHBOARD PRINCIPAL (HUD)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el estado completo del usuario."""
    # Detectar si viene de botón o comando
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        message_func = update.callback_query.message.edit_text
    else:
        user_id = update.effective_user.id
        message_func = update.message.reply_text

    # Recuperar datos
    user_data = await db.get_user(user_id)
    if not user_data: 
        # Si no existe (raro), reiniciamos
        await message_func("⚠️ Error de Sincronización. Escribe /start")
        return

    # Check Ban
    if user_data.get('ban_status'):
        await message_func("🚫 **DESCONEXIÓN FORZADA**\nTu patrón ha sido marcado como hostil/bot.")
        return

    # ACTUALIZACIÓN BIOLÓGICA (Regeneración)
    user_data = await process_biological_update(user_data)
    await db.save_user(user_id, user_data)
    
    # Preparar Datos Visuales
    role = user_data['role']
    oxygen = user_data.get('oxygen', 100.0)
    
    # Status de Oxígeno (Semáforo)
    oxy_icon = "🟢"
    if oxygen < 70: oxy_icon = "🟡"
    if oxygen < 30: oxy_icon = "🔴"
    
    # Info de Célula
    cell_text = "Sin Célula (x1.0)"
    if user_data.get('cell_id'):
        cell = await db.get_cell(user_data['cell_id'])
        if cell:
            cell_text = f"{cell['name']} (x{cell['synergy_level']:.2f})"
            
    # Barra de Energía
    energy_bar = render_progressbar(user_data['energy'], user_data['max_energy'])
    
    txt = (
        f"🧬 **PANDORA INTERFACE v2.0** | {role}\n"
        f"──────────────────────\n"
        f"🫁 **Oxígeno:** {oxygen:.1f}% {oxy_icon}\n"
        f"⚡ **Energía:** `{energy_bar}` {int(user_data['energy'])}/{user_data['max_energy']}\n"
        f"🦠 **Célula:** {cell_text}\n"
        f"──────────────────────\n"
        f"🪙 **Néctar:** `{user_data['nectar']:.2f}` (Líquido)\n"
        f"🔒 **Hive:** `{user_data['tokens_locked']:.4f}` (Vesting)\n"
        f"💵 **Saldo CPA:** `${user_data['usd_balance']:.2f}`\n"
        f"📈 **XP:** {int(user_data['role_xp'])}"
    )
    
    kb = [
        [InlineKeyboardButton("⛏️ SINTETIZAR (MINE)", callback_data="mine_action")],
        [InlineKeyboardButton("🧠 TAREAS (EARN)", callback_data="tasks_hub")],
        [InlineKeyboardButton("🦠 CÉLULA (SQUAD)", callback_data="cell_menu")],
        [InlineKeyboardButton("🛒 TIENDA", callback_data="shop_menu"), InlineKeyboardButton("👥 RED", callback_data="team_menu")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="go_dashboard")]
    ]
    
    try:
        await message_func(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except Exception as e:
        # A veces Telegram da error si el mensaje es idéntico al anterior. Lo ignoramos.
        pass

# ==============================================================================
# HANDLERS: MINERÍA (EL NÚCLEO DE LA ADICCIÓN)
# ==============================================================================

async def mine_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mecánica de 'Tap' evolucionada.
    Combina:
    1. Energía (Limitante)
    2. Bio-Ritmo (Multiplicador de Habilidad/Anti-bot)
    3. Sinergia (Multiplicador Social)
    4. Oxígeno (Multiplicador de Retención)
    """
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # 1. Actualizar estado antes de calcular
    user_data = await process_biological_update(user_data)
    
    # 2. Chequear Energía
    if user_data['energy'] < ENERGY_COST_PER_TAP:
        await query.answer(f"⚡ Energía agotada. Espera o Recarga.", show_alert=True)
        return

    # Consumir Energía
    user_data['energy'] -= ENERGY_COST_PER_TAP
    
    # 3. Calcular Bio-Ritmo (Entropía)
    now = time.time()
    trace = user_data.get('entropy_trace', [])
    trace.append(now)
    # Guardamos solo los últimos 20 taps para análisis
    if len(trace) > 20: trace.pop(0)
    user_data['entropy_trace'] = trace
    
    rhythm_mult, rhythm_msg = calculate_bio_rhythm(trace)
    
    # 4. Calcular Sinergia de Célula
    synergy_mult = 1.0
    if user_data.get('cell_id'):
        cell = await db.get_cell(user_data['cell_id'])
        if cell:
            synergy_mult = cell.get('synergy_level', 1.0)
            # Acumular XP para la célula (meta-game)
            cell['total_xp'] += 1
            await db.update_cell(cell['id'], cell)
            
    # 5. Calcular Factor de Oxígeno
    # Si el oxígeno es bajo, el usuario gana MENOS. Esto lo obliga a jugar.
    oxygen_mult = user_data.get('oxygen', 100.0) / 100.0
    
    # 6. FÓRMULA FINAL DE RECOMPENSA
    variability = random.uniform(0.95, 1.05) # Pequeña variación para sentirlo orgánico
    total_gain = BASE_MINING_REWARD * rhythm_mult * synergy_mult * oxygen_mult * variability
    
    # Dividir ganancia: 40% Néctar (Usable ya), 60% Hive (Bloqueado/Airdrop)
    nectar_gain = total_gain * 0.4
    locked_gain = total_gain * 0.6
    
    user_data['nectar'] += nectar_gain
    user_data['tokens_locked'] += locked_gain
    
    # Ganar XP (Evolución)
    # El ritmo humano (Flow) da más XP
    xp_gain = 1.0 * rhythm_mult
    user_data['role_xp'] += xp_gain
    
    # Recuperar Oxígeno por estar activo (Respirar)
    user_data['oxygen'] = min(100.0, user_data['oxygen'] + 2.0)
    
    # Guardar todo
    await db.save_user(user_id, user_data)
    
    # Feedback al usuario
    # No editamos el mensaje en cada tap para no saturar la API (Rate Limit),
    # usamos query.answer para feedback instantáneo y editamos el texto a veces.
    
    await query.answer(f"+{nectar_gain:.2f} Néctar | {rhythm_msg}")
    
    # Actualizar visualmente cada 5 taps aprox o si sube de nivel
    if random.random() < 0.2:
        txt = (
            f"⛏️ **SÍNTESIS EXITOSA**\n"
            f"🌊 Ritmo: {rhythm_msg}\n"
            f"🦠 Sinergia: x{synergy_mult:.2f}\n"
            f"────────────────\n"
            f"💎 **+{nectar_gain:.3f} Néctar**\n"
            f"⚡ Energía: {int(user_data['energy'])}"
        )
        kb = [[InlineKeyboardButton("⛏️ SINTETIZAR", callback_data="mine_action")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
        try: await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass

# ==============================================================================
# HANDLERS: SISTEMA DE TIERS (CPA & MONETIZACIÓN)
# ==============================================================================

async def tasks_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🟢 TIER 1: RECOLECCIÓN (Fácil)", callback_data="tier_1")],
        [InlineKeyboardButton("🟡 TIER 2: PROCESAMIENTO (Medio)", callback_data="tier_2")],
        [InlineKeyboardButton("🔴 TIER 3: CÁMARA REAL (Difícil)", callback_data="tier_3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(
        "🧠 **MATRIZ DE TAREAS**\n\n"
        "Selecciona el nivel de complejidad.\n"
        "Recuerda: Tiers más altos requieren Roles evolucionados.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def tier_1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acceso: TODOS"""
    query = update.callback_query
    # Lista de botones generada dinámicamente o estática
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("💰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("🪙 COINTIPLY", url=LINKS['COINTIPLY']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("💸 FREECASH", url=LINKS['FREECASH']), InlineKeyboardButton("🌟 SWAGBUCKS", url=LINKS['SWAGBUCKS'])],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_hub")]
    ]
    await query.message.edit_text("🟢 **TIER 1: RECOLECCIÓN**\nMicro-tareas rápidas.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier_2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acceso: OBRERO+"""
    query = update.callback_query; user_id = query.from_user.id
    user = await db.get_user(user_id)
    
    # Verificación de Rol
    allowed_roles = ROLES_CONFIG['OBRERO']['tiers'] + ROLES_CONFIG['EXPLORADOR']['tiers'] # etc... simplificado:
    current_tier_access = ROLES_CONFIG.get(user['role'], ROLES_CONFIG['LARVA'])['tiers']
    
    if 2 not in current_tier_access and not user.get('is_premium'):
        await query.answer("🔒 BLOQUEADO. Evoluciona a OBRERO para acceder.", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("🚦 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("💼 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("🌱 SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_hub")]
    ]
    await query.message.edit_text("🟡 **TIER 2: PROCESAMIENTO**\nIngresos pasivos.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier_3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acceso: EXPLORADOR+"""
    query = update.callback_query; user_id = query.from_user.id
    user = await db.get_user(user_id)
    
    current_tier_access = ROLES_CONFIG.get(user['role'], ROLES_CONFIG['LARVA'])['tiers']
    
    if 3 not in current_tier_access and not user.get('is_premium'):
        await query.answer("🔒 BLOQUEADO. Evoluciona a EXPLORADOR para acceder.", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($20)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("🦉 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("☁️ AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("✅ VERIFICAR TAREA MANUAL", callback_data="verify_manual")],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_hub")]
    ]
    await query.message.edit_text("🔴 **TIER 3: CÁMARA REAL**\nFinanzas de alto valor.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.message.edit_text("🛰️ **ESCANEANDO BLOCKCHAIN...**")
    await asyncio.sleep(2.0)
    await q.message.edit_text(
        "📝 **SOLICITUD REGISTRADA**\n\n"
        "Tu acción ha quedado en cola de verificación manual.\n"
        "Si es válida, recibirás USD en tu saldo.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="go_dashboard")]])
    )

# ==============================================================================
# HANDLERS: CÉLULAS Y SOCIAL
# ==============================================================================

async def cell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data.get('cell_id'):
        # MODO: YA TENGO CÉLULA
        cell = await db.get_cell(user_data['cell_id'])
        txt = (
            f"🦠 **CÉLULA: {cell['name']}**\n"
            f"────────────────\n"
            f"👥 Miembros: {len(cell['members'])}\n"
            f"🔥 Sinergia: x{cell['synergy_level']:.2f}\n"
            f"🏆 XP Total: {int(cell['total_xp'])}\n"
            f"🆔 **ID:** `{cell['id']}`\n\n"
            "Comparte el ID con tus amigos para aumentar la Sinergia."
        )
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    else:
        # MODO: SIN CÉLULA
        txt = (
            "⚠️ **ORGANISMO AISLADO**\n\n"
            "No perteneces a ninguna célula.\n"
            "Estás perdiendo el **Bono de Sinergia**.\n\n"
            "Opciones:"
        )
        kb = [
            [InlineKeyboardButton("➕ CREAR CÉLULA (100 Néctar)", callback_data="create_cell_act")],
            [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
        ]
        # Nota: Unirse a célula por ID requiere input de texto, se maneja en general_text_handler o comando aparte
    
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def create_cell_act(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    cost = 100
    if user_data['nectar'] < cost:
        await query.answer("❌ Néctar insuficiente.", show_alert=True)
        return
        
    user_data['nectar'] -= cost
    name = f"Enjambre-{random.randint(1000,9999)}"
    cell_id = await db.create_cell(user_id, name)
    user_data['cell_id'] = cell_id
    
    await db.save_user(user_id, user_data)
    await query.answer("✅ Célula Creada")
    await cell_menu(update, context)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    refs = len(user_data.get('referrals', []))
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    txt = (
        f"👥 **RED DE DESCENDENCIA**\n\n"
        f"Hijos Directos: {refs}\n"
        f"Poder de Enjambre: x{user_data.get('swarm_power', 1.0):.2f}\n\n"
        f"🔗 **Tu Enlace:**\n`{link}`"
    )
    kb = [[InlineKeyboardButton("📤 COMPARTIR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==============================================================================
# HANDLERS: TIENDA
# ==============================================================================

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    txt = f"🛒 **MERCADO ORGÁNICO**\nSaldo: {user_data['nectar']:.2f} Néctar"
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA (200 Néctar)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 MEMBRESÍA REINA ($10 USD)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data['nectar'] >= COST_FULL_RECHARGE:
        user_data['nectar'] -= COST_FULL_RECHARGE
        # Recargar al máximo permitido por su rol
        config = ROLES_CONFIG.get(user_data['role'], ROLES_CONFIG['LARVA'])
        user_data['energy'] = config['max_energy']
        
        await db.save_user(user_id, user_data)
        await query.answer("⚡ Energía Restaurada", show_alert=True)
        await show_dashboard(update, context)
    else:
        await query.answer("❌ Néctar insuficiente", show_alert=True)

async def buy_premium_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        f"💎 **EVOLUCIÓN ARTIFICIAL (PREMIUM)**\n\n"
        "Obtén el rol REINA, Acceso a todos los Tiers y Bonus x2.\n\n"
        f"Envía $10 USD (TRC20) a:\n`{CRYPTO_WALLET_USDT}`\n\n"
        "Luego envía el Hash de transacción aquí.",
        parse_mode="Markdown"
    )
    # Aquí podríamos activar un flag en context para esperar el hash en general_text_handler

# ==============================================================================
# DISPATCHER CENTRAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enruta todos los clicks de botones."""
    query = update.callback_query
    data = query.data
    
    # Mapeo simple de acciones
    if data == "accept_legal":
        context.user_data['waiting_for_email'] = True
        await query.message.edit_text("📧 Ingresa tu **EMAIL** para continuar:", parse_mode="Markdown")
        return

    mapping = {
        "go_dashboard": show_dashboard,
        "mine_action": mine_action,
        "tasks_hub": tasks_hub,
        "tier_1": tier_1_menu,
        "tier_2": tier_2_menu,
        "tier_3": tier_3_menu,
        "verify_manual": verify_manual,
        "cell_menu": cell_menu,
        "create_cell_act": create_cell_act,
        "shop_menu": shop_menu,
        "buy_energy": buy_energy,
        "buy_premium": buy_premium_flow,
        "team_menu": team_menu
    }
    
    if data in mapping:
        await mapping[data](update, context)
    
    # Siempre intentar responder al callback para que no se quede cargando
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("PANDORA PROTOCOL V200.0 - SYSTEM HEALTHY")
async def invite_command(u, c): await team_menu(u, c)
