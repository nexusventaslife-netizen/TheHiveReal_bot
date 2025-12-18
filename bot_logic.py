import logging
import asyncio
import random
import time
import math
import statistics
import os
import json
from datetime import datetime
from typing import Tuple, List, Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import database as db

# ==============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y CONSTANTES
# ==============================================================================

# Logger Config
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# ADMIN ID (Para comandos de depuración futuros)
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    ADMIN_ID = 0

# IMAGEN DE BIENVENIDA (URL Fija)
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# WALLET DE LA EMPRESA (Para pagos manuales de usuarios)
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_ADDRESS_PENDING")

# --- ARSENAL DE ENLACES DE AFILIADOS (CPA MATRIX) ---
# NO EDITAR NI BORRAR NINGUNO. SON EL MOTOR DE INGRESOS.
LINKS = {
    # === TIER 1: TRÁFICO MASIVO & MICRO-TAREAS (Acceso: LARVA) ===
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'FAUCETPAY': "https://faucetpay.io/?r=2275014",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'EVERVE': "https://everve.net/ref/1950045/",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    
    # === TIER 2: INGRESOS PASIVOS & BANDA ANCHA (Acceso: OBRERO) ===
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # === TIER 3: FINANZAS, TRADING & HIGH TICKET (Acceso: EXPLORADOR) ===
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

# --- CONFIGURACIÓN DE ROLES Y EVOLUCIÓN ---
# Define la XP necesaria, la energía máxima y la velocidad de regeneración por rango.
ROLES_CONFIG = {
    "LARVA": {
        "xp_required": 0,
        "max_energy": 300,
        "regen_rate": 0.5, # Puntos por segundo
        "tier_access": [1]
    },
    "OBRERO": {
        "xp_required": 500,
        "max_energy": 500,
        "regen_rate": 0.8,
        "tier_access": [1, 2]
    },
    "EXPLORADOR": {
        "xp_required": 1500,
        "max_energy": 800,
        "regen_rate": 1.0,
        "tier_access": [1, 2, 3]
    },
    "GUARDIAN": {
        "xp_required": 3500,
        "max_energy": 1200,
        "regen_rate": 1.5,
        "tier_access": [1, 2, 3]
    },
    "NODO": {
        "xp_required": 7000,
        "max_energy": 2500,
        "regen_rate": 2.0,
        "tier_access": [1, 2, 3]
    },
    "GENESIS": {
        "xp_required": 15000,
        "max_energy": 5000,
        "regen_rate": 5.0,
        "tier_access": [1, 2, 3] # Acceso total + Bonus
    }
}

# --- ECONOMÍA DEL JUEGO ---
ENERGY_COST_PER_TAP = 10         # Costo de energía por acción de minado
BASE_MINING_REWARD = 0.50        # Recompensa base en Néctar
COST_FULL_RECHARGE = 200         # Costo en Néctar para rellenar tanque de energía
OXYGEN_DECAY_RATE_PER_HOUR = 5.0 # Porcentaje de oxígeno perdido por hora inactiva
CELL_CREATION_COST = 100         # Costo en Néctar para fundar una célula

# ==============================================================================
# 2. ALGORITMOS MATEMÁTICOS Y LÓGICA DE NEGOCIO
# ==============================================================================

def calculate_bio_rhythm(timestamps: List[float]) -> Tuple[float, str]:
    """
    ALGORITMO DE ENTROPÍA (ANTI-BOT)
    Analiza la varianza de los intervalos de tiempo entre clics.
    
    Retorna:
        - Multiplicador (float): Factor de ganancia (0.1 a 1.5)
        - Mensaje (str): Descripción del estado para el usuario
    """
    # Necesitamos al menos 4 puntos de datos para calcular varianza
    if len(timestamps) < 4:
        return 1.0, "🔵 Calibrando Sensores..."
    
    # Calcular los intervalos (deltas) entre clics consecutivos
    intervals = []
    for i in range(1, len(timestamps)):
        delta = timestamps[i] - timestamps[i-1]
        intervals.append(delta)
    
    if not intervals:
        return 1.0, "⚪ Ritmo Neutro"
    
    try:
        avg_interval = statistics.mean(intervals)
        stdev_interval = statistics.stdev(intervals)
    except Exception:
        # Si hay error matemático (ej. división por cero), devolvemos neutro
        return 1.0, "⚪ Ritmo Neutro"
        
    # Coeficiente de Variación (CV) = Desviación Estándar / Media
    # CV bajo significa clics muy regulares (Bot)
    # CV alto significa clics caóticos (Humano distraído)
    # CV medio significa "Flow" (Humano concentrado)
    
    cv = stdev_interval / avg_interval if avg_interval > 0 else 0
    
    # Lógica de Decisión
    if cv < 0.05:
        # Extremadamente preciso. Probablemente un script/autoclicker.
        # Penalización severa sin banear (Shadowban de recompensa).
        return 0.1, "🔴 ERROR: Patrón Robótico Detectado"
        
    elif 0.05 <= cv <= 0.25:
        # Ritmo humano, constante y enfocado. Estado de "Flow".
        # Recompensa máxima.
        return 1.3, "🌊 FLUJO PERFECTO (Bonus x1.3)"
        
    elif cv > 1.5:
        # Muy irregular. Humano lento.
        return 0.8, "💤 Ritmo Lento"
        
    else:
        # Humano promedio.
        return 1.0, "🟢 Ritmo Humano Normal"

async def update_user_biology(user_data: Dict) -> Dict:
    """
    MOTOR BIOLÓGICO: Actualiza Energía, Oxígeno y Roles.
    Esta función debe llamarse antes de cualquier interacción importante.
    """
    now = time.time()
    last_ts = user_data.get('last_update_ts', now)
    elapsed = now - last_ts
    
    # 1. Determinar Rol y Configuración Actual
    current_role = user_data.get('role', 'LARVA')
    config = ROLES_CONFIG.get(current_role, ROLES_CONFIG['LARVA'])
    
    # Asegurar que max_energy esté actualizada según el rol
    user_data['max_energy'] = config['max_energy']
    
    # 2. Regeneración de Energía
    if elapsed > 0:
        # Fórmula: Tiempo * Tasa de Regeneración del Rol
        regen_amount = elapsed * config['regen_rate']
        new_energy = user_data['energy'] + int(regen_amount)
        # No exceder el máximo
        user_data['energy'] = min(user_data['max_energy'], new_energy)
        
    # 3. Decaimiento de Oxígeno (Mecánica de Retención)
    # Si pasan más de 3600 segundos (1 hora), el oxígeno empieza a bajar.
    if elapsed > 3600:
        hours_inactive = elapsed / 3600
        decay = hours_inactive * OXYGEN_DECAY_RATE_PER_HOUR
        current_oxygen = user_data.get('oxygen', 100.0)
        # El oxígeno no baja de 10% (para no desanimar totalmente)
        user_data['oxygen'] = max(10.0, current_oxygen - decay)
        
    # 4. Evolución de Rol (Level Up)
    # Verificamos si la XP actual califica para un rol superior
    current_xp = user_data.get('role_xp', 0)
    best_role = current_role
    
    # Iteramos sobre la config para encontrar el rol más alto posible
    for role_name, role_data in ROLES_CONFIG.items():
        if current_xp >= role_data['xp_required']:
            # Asumimos que el orden en el dict es jerárquico o verificamos XP
            # Una forma simple es comparar XP requerida
            if role_data['xp_required'] >= ROLES_CONFIG[best_role]['xp_required']:
                best_role = role_name
                
    # Si subió de nivel
    if best_role != current_role:
        user_data['role'] = best_role
        user_data['max_energy'] = ROLES_CONFIG[best_role]['max_energy']
        # Bonus de Level Up: Restaurar Energía al Máximo
        user_data['energy'] = user_data['max_energy']
        
    # Actualizar timestamp
    user_data['last_update_ts'] = now
    
    return user_data

def generate_captcha_code() -> str:
    """Genera un código aleatorio simple para verificación."""
    return f"HIVE-{random.randint(1000, 9999)}"

def render_ascii_progressbar(current: int, total: int, length: int = 10) -> str:
    """Renderiza una barra de progreso visual (ej. ████░░░░░░)."""
    if total <= 0: total = 1
    percent = max(0.0, min(float(current) / float(total), 1.0))
    filled_length = int(length * percent)
    empty_length = length - filled_length
    return "█" * filled_length + "░" * empty_length

# ==============================================================================
# 3. HANDLERS DE COMANDOS Y FLUJO DE INICIO
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /start.
    Punto de entrada. Maneja referidos y decide si mostrar Captcha o Dashboard.
    """
    user = update.effective_user
    args = context.args
    
    # Parsear referido si existe
    referrer_id = None
    if args and len(args) > 0:
        if args[0].isdigit():
            referrer_id = int(args[0])
            
    # Intentar crear usuario en DB
    # create_user devuelve True si es nuevo, False si ya existe
    is_new_user = await db.create_user(user.id, user.first_name, user.username, referrer_id)
    
    # Recuperar datos del usuario
    user_data = await db.get_user(user.id)
    
    # CASO 1: Usuario ya verificado (tiene email y actividad)
    # Lo enviamos directo al Dashboard para no molestar.
    if user_data and user_data.get('email') and not is_new_user:
        await show_dashboard(update, context)
        return

    # CASO 2: Usuario Nuevo o No Verificado
    # Iniciamos el protocolo de seguridad "HIVE GENESIS"
    
    captcha_code = generate_captcha_code()
    context.user_data['captcha'] = captcha_code
    context.user_data['awaiting_captcha'] = True
    
    welcome_text = (
        f"🧬 **PROTOCOLO PANDORA: SECUENCIA DE INICIO**\n"
        f"──────────────────────────────\n"
        f"Identidad Detectada: **{user.first_name}**\n\n"
        "Has sido seleccionado para integrarte a la Colmena.\n"
        "Aquí, el valor se mide en Bio-Ritmo y Sinergia.\n\n"
        "🛡️ **VERIFICACIÓN DE SEGURIDAD**\n"
        "El sistema requiere confirmar que eres un organismo biológico.\n\n"
        f"Escribe el siguiente código de acceso:\n`{captcha_code}`"
    )
    
    # Enviamos imagen si es posible, sino texto
    try:
        await update.message.reply_photo(
            photo=IMG_BEEBY,
            caption=welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        await update.message.reply_text(
            text=welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /reset.
    BORRA COMPLETAMENTE AL USUARIO. Útil para depuración y pruebas.
    """
    user_id = update.effective_user.id
    
    # Borrar de la base de datos
    await db.delete_user(user_id)
    
    # Limpiar contexto local de Telegram
    context.user_data.clear()
    
    await update.message.reply_text(
        "🗑️ **SISTEMA FORMATEADO**\n\n"
        "Tu registro biológico ha sido eliminado de la Colmena.\n"
        "Eres un fantasma digital.\n\n"
        "Escribe /start para renacer."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help."""
    help_text = (
        "📚 **MANUAL DEL PROTOCOLO PANDORA**\n\n"
        "1. **Minar (Tap):** Genera Néctar y XP. Tu ritmo importa.\n"
        "2. **Oxígeno:** Baja si no juegas. Si baja, ganas menos.\n"
        "3. **Roles:** Sube de nivel para tener más energía y mejores tareas.\n"
        "4. **Células:** Únete a un grupo para multiplicar ganancias.\n\n"
        "🔧 **Comandos:**\n"
        "/start - Reiniciar interfaz\n"
        "/reset - Borrar cuenta (Cuidado)\n"
        "/invitar - Ver enlace de referido"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /invitar directo."""
    await team_menu(update, context)

# ==============================================================================
# 4. HANDLER DE MENSAJES DE TEXTO (CAPTCHA, EMAIL, CHAT)
# ==============================================================================

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesa todo el texto que no es comando.
    Maneja la máquina de estados: Captcha -> Email -> Dashboard.
    """
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    
    # --- ESTADO 1: ESPERANDO CAPTCHA ---
    if context.user_data.get('awaiting_captcha'):
        expected_code = context.user_data.get('captcha')
        
        if text == expected_code:
            # Captcha correcto
            context.user_data['awaiting_captcha'] = False
            context.user_data['captcha'] = None
            
            # Pasamos a pedir Aceptación Legal
            kb = [[InlineKeyboardButton("✅ ACEPTAR VINCULACIÓN", callback_data="accept_legal")]]
            
            await update.message.reply_text(
                "✅ **ADN VERIFICADO**\n\n"
                "Para monetizar tu actividad biológica, debes aceptar los términos del Enjambre.\n"
                "Esto vinculará tu cuenta de Telegram permanentemente.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        else:
            # Captcha incorrecto
            await update.message.reply_text("❌ Código de acceso inválido. Intenta de nuevo.")
            return

    # --- ESTADO 2: ESPERANDO EMAIL ---
    if context.user_data.get('waiting_for_email'):
        # Validación simple de formato email
        if "@" in text and "." in text and len(text) > 5:
            # Guardar email en DB
            await db.update_email(user_id, text)
            context.user_data['waiting_for_email'] = False
            
            # Dar Bono de Bienvenida
            user_data = await db.get_user(user_id)
            if user_data:
                user_data['nectar'] += 100.0
                await db.save_user(user_id, user_data)
            
            # Mostrar botón para ir al Dashboard
            kb = [[InlineKeyboardButton("🚀 ACCEDER AL NÚCLEO", callback_data="go_dashboard")]]
            
            await update.message.reply_text(
                "🎉 **SINCRONIZACIÓN EXITOSA**\n\n"
                "Has recibido **+100 Néctar** por completar el registro.\n"
                "Tu organismo está listo para la evolución.\n\n"
                "👇 Presiona el botón para entrar.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        else:
            await update.message.reply_text("⚠️ Formato de correo inválido. Por favor verifica.")
            return

    # --- ESTADO 3: FLUJO NORMAL ---
    # Si el usuario escribe /start manualmente (algunos clientes no lo mandan como comando)
    if text.upper() == "/START":
        await start_command(update, context)
        return
        
    # Si el usuario ya está logueado y escribe hola, etc, le mostramos el dashboard
    user_data = await db.get_user(user_id)
    if user_data:
        # Solo mostramos dashboard si tiene email, sino lo pedimos
        if user_data.get('email'):
            await show_dashboard(update, context)
        else:
            # Caso raro: está en DB pero no tiene email. Lo forzamos.
            context.user_data['waiting_for_email'] = True
            await update.message.reply_text("⚠️ **ATENCIÓN**\nFalta vincular tu Email. Escríbelo ahora:")
    else:
        # No está en DB, mandar a start
        await start_command(update, context)

# ==============================================================================
# 5. DASHBOARD PRINCIPAL (EL HUB)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra la interfaz principal con todas las estadísticas.
    Se adapta si viene de un mensaje de texto o de un callback query.
    """
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        message_func = update.callback_query.message.edit_text
    else:
        user_id = update.effective_user.id
        message_func = update.message.reply_text

    # Recuperar datos
    user_data = await db.get_user(user_id)
    
    # Manejo de error si el usuario no existe (ej. tras un reset manual)
    if not user_data:
        await message_func("⚠️ Error de Sincronización. Escribe /start para reiniciar.")
        return

    # Verificar estado de Ban
    if user_data.get('ban_status', False):
        await message_func("🚫 **ACCESO DENEGADO**\nTu patrón biológico ha sido marcado como hostil.")
        return

    # PROCESAR ACTUALIZACIÓN BIOLÓGICA (Regenerar energía, etc.)
    user_data = await update_user_biology(user_data)
    await db.save_user(user_id, user_data)
    
    # Preparar Variables para la Vista
    role = user_data.get('role', 'LARVA')
    energy = int(user_data.get('energy', 0))
    max_energy = int(user_data.get('max_energy', 300))
    oxygen = float(user_data.get('oxygen', 100.0))
    nectar = float(user_data.get('nectar', 0.0))
    usd = float(user_data.get('usd_balance', 0.0))
    tokens_locked = float(user_data.get('tokens_locked', 0.0))
    xp = int(user_data.get('role_xp', 0))
    
    # Iconos Dinámicos
    oxygen_icon = "🟢" if oxygen > 75 else "🟡" if oxygen > 30 else "🔴"
    progress_bar = render_ascii_progressbar(energy, max_energy)
    
    # Info de Célula
    cell_info = "Sin Célula (x1.0)"
    if user_data.get('cell_id'):
        cell = await db.get_cell(user_data['cell_id'])
        if cell:
            synergy = cell.get('synergy_level', 1.0)
            cell_info = f"{cell['name']} (x{synergy:.2f})"
            
    # Construcción del Mensaje
    dashboard_text = (
        f"🧬 **NÚCLEO PANDORA** | Rango: **{role}**\n"
        f"────────────────────────\n"
        f"🫁 **Oxígeno:** {oxygen:.1f}% {oxygen_icon}\n"
        f"⚡ **Energía:** `{progress_bar}` {energy}/{max_energy}\n"
        f"🦠 **Célula:** {cell_info}\n"
        f"────────────────────────\n"
        f"🪙 **Néctar:** `{nectar:.2f}` (Líquido)\n"
        f"🔒 **Hive:** `{tokens_locked:.4f}` (Futuro)\n"
        f"💵 **Saldo USD:** `${usd:.2f}`\n"
        f"📈 **XP Evolutiva:** {xp}\n"
        f"────────────────────────\n"
        f"💡 *Mantén tu oxígeno alto minando regularmente.*"
    )
    
    # Teclado Principal
    keyboard = [
        [InlineKeyboardButton("⛏️ MINAR (SINTETIZAR)", callback_data="mine_action")],
        [InlineKeyboardButton("🧠 TAREAS (EARN)", callback_data="tasks_hub"), InlineKeyboardButton("🦠 CÉLULA (SQUAD)", callback_data="cell_menu")],
        [InlineKeyboardButton("🛒 TIENDA", callback_data="shop_menu"), InlineKeyboardButton("👥 EQUIPO", callback_data="team_menu")],
        [InlineKeyboardButton("🔄 REFRESCAR SISTEMA", callback_data="go_dashboard")]
    ]
    
    try:
        await message_func(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        # Ignorar error si el mensaje es idéntico al anterior (Telegram API quirk)
        pass

# ==============================================================================
# 6. MECÁNICA DE MINERÍA (TAP)
# ==============================================================================

async def mine_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Acción de minado principal.
    Aplica el algoritmo Bio-Rítmico y Sinergia Celular.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # 1. Recuperar y Actualizar Estado
    user_data = await db.get_user(user_id)
    user_data = await update_user_biology(user_data)
    
    # 2. Verificar Energía
    if user_data['energy'] < ENERGY_COST_PER_TAP:
        await query.answer("⚡ Energía Agotada. Descansa o recarga en la Tienda.", show_alert=True)
        return
        
    # Consumir Energía
    user_data['energy'] -= ENERGY_COST_PER_TAP
    
    # 3. Registrar Timestamp para Entropía
    now = time.time()
    trace = user_data.get('entropy_trace', [])
    trace.append(now)
    # Mantenemos solo los últimos 20 clics para no saturar memoria
    if len(trace) > 20:
        trace.pop(0)
    user_data['entropy_trace'] = trace
    
    # 4. Calcular Multiplicadores
    # A) Ritmo (Anti-bot)
    rhythm_mult, rhythm_msg = calculate_bio_rhythm(trace)
    
    # B) Sinergia Celular
    synergy_mult = 1.0
    if user_data.get('cell_id'):
        cell = await db.get_cell(user_data['cell_id'])
        if cell:
            synergy_mult = cell.get('synergy_level', 1.0)
            # También sumamos XP a la célula para leaderboards futuros
            cell['total_xp'] += 1
            await db.update_cell(cell['id'], cell)
            
    # C) Oxígeno (Penalización por inactividad)
    oxygen_level = user_data.get('oxygen', 100.0)
    oxygen_mult = oxygen_level / 100.0
    
    # 5. Calcular Ganancia Final
    # Base * Ritmo * Sinergia * Oxígeno * Variabilidad Random
    variability = random.uniform(0.95, 1.05)
    
    total_gain = BASE_MINING_REWARD * rhythm_mult * synergy_mult * oxygen_mult * variability
    
    # Split de Economía:
    # 40% Néctar (Para gastar en upgrades/energía)
    # 60% Hive Tokens (Bloqueados para Airdrop)
    nectar_gain = total_gain * 0.4
    locked_gain = total_gain * 0.6
    
    user_data['nectar'] += nectar_gain
    user_data['tokens_locked'] += locked_gain
    
    # Ganancia de XP (Evolución)
    # El XP depende puramente del ritmo (habilidad)
    xp_gain = 1.0 * rhythm_mult
    user_data['role_xp'] += xp_gain
    
    # 6. Recuperar Oxígeno (Respiración Activa)
    # Cada clic recupera un poco de oxígeno perdido
    user_data['oxygen'] = min(100.0, oxygen_level + 2.0)
    
    # Guardar cambios
    await db.save_user(user_id, user_data)
    
    # 7. Feedback al Usuario
    # Usamos answer para feedback rápido
    await query.answer(f"+{nectar_gain:.2f} Néctar | {rhythm_msg}")
    
    # Aleatoriamente (20%) actualizamos todo el dashboard para mostrar progreso visual
    if random.random() < 0.2:
        await show_dashboard(update, context)

# ==============================================================================
# 7. MENÚ DE TAREAS (TIERS 1, 2, 3)
# ==============================================================================

async def tasks_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Selector principal de categorías de tareas."""
    query = update.callback_query
    
    kb = [
        [InlineKeyboardButton("🟢 TIER 1: INCUBADORA (Fácil)", callback_data="tier_1")],
        [InlineKeyboardButton("🟡 TIER 2: REFINERÍA (Medio)", callback_data="tier_2")],
        [InlineKeyboardButton("🔴 TIER 3: BÓVEDA REAL (Difícil)", callback_data="tier_3")],
        [InlineKeyboardButton("🔙 VOLVER AL NÚCLEO", callback_data="go_dashboard")]
    ]
    
    await query.message.edit_text(
        "🧠 **MATRIZ DE TAREAS**\n\n"
        "Selecciona el nivel de complejidad.\n"
        "Recuerda: Los Tiers superiores requieren roles evolucionados.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def tier_1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú Tier 1: Links básicos."""
    query = update.callback_query
    
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS (Videos)", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC (Clicks)", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🚰 FAUCETPAY", url=LINKS['FAUCETPAY'])],
        [InlineKeyboardButton("🪙 COINTIPLY", url=LINKS['COINTIPLY']), InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG'])],
        [InlineKeyboardButton("💸 FREECASH", url=LINKS['FREECASH']), InlineKeyboardButton("🌟 SWAGBUCKS", url=LINKS['SWAGBUCKS'])],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_hub")]
    ]
    
    await query.message.edit_text(
        "🟢 **TIER 1: INCUBADORA**\n"
        "Recolección básica de recursos. Acceso libre para todas las Larvas.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def tier_2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú Tier 2: Pasivos. Requiere Rol OBRERO."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # Verificación de Rol
    allowed_roles = ROLES_CONFIG['OBRERO']['tier_access'] # [1, 2]
    # Simplificación: Si el rol actual tiene acceso al tier 2
    current_role = user_data.get('role', 'LARVA')
    access_list = ROLES_CONFIG.get(current_role, ROLES_CONFIG['LARVA'])['tier_access']
    
    if 2 not in access_list and not user_data.get('is_premium'):
        await query.answer("🔒 ACCESO DENEGADO. Requiere Rol: OBRERO", show_alert=True)
        return
        
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS.APP", url=LINKS['PAWNS']), InlineKeyboardButton("🚦 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("💼 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("🌱 SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_hub")]
    ]
    
    await query.message.edit_text(
        "🟡 **TIER 2: REFINERÍA**\n"
        "Sistemas de ingreso pasivo y trabajo freelance.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def tier_3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú Tier 3: Finanzas. Requiere Rol EXPLORADOR."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    current_role = user_data.get('role', 'LARVA')
    access_list = ROLES_CONFIG.get(current_role, ROLES_CONFIG['LARVA'])['tier_access']
    
    if 3 not in access_list and not user_data.get('is_premium'):
        await query.answer("🔒 ACCESO DENEGADO. Requiere Rol: EXPLORADOR", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($20 Bonus)", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT']), InlineKeyboardButton("🦉 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("☁️ AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("✅ VERIFICAR TAREA MANUAL", callback_data="verify_manual_task")],
        [InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_hub")]
    ]
    
    await query.message.edit_text(
        "🔴 **TIER 3: BÓVEDA REAL**\n"
        "Alta rentabilidad financiera. Solo para la élite.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def verify_manual_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simulación de verificación manual."""
    query = update.callback_query
    
    await query.message.edit_text("🛰️ **INICIANDO ESCANEO DE BLOCKCHAIN...**")
    await asyncio.sleep(2.0)
    
    kb = [[InlineKeyboardButton("ENTENDIDO", callback_data="go_dashboard")]]
    await query.message.edit_text(
        "📝 **SOLICITUD REGISTRADA**\n\n"
        "Hemos detectado tu clic. El sistema validará la conversión (CPA) en las próximas 24 horas.\n"
        "Si es exitoso, recibirás saldo en USD directamente.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================================================================
# 8. SISTEMA DE CÉLULAS (GUILDS)
# ==============================================================================

async def cell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestión de Células: Ver info, crear o unirse."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # CASO A: Ya tiene célula
    if user_data.get('cell_id'):
        cell = await db.get_cell(user_data['cell_id'])
        if cell:
            txt = (
                f"🦠 **TU CÉLULA: {cell['name']}**\n"
                f"────────────────\n"
                f"👥 Miembros: {len(cell['members'])}\n"
                f"🔥 Sinergia: x{cell['synergy_level']:.2f}\n"
                f"🏆 XP Total: {int(cell['total_xp'])}\n"
                f"🆔 **ID:** `{cell['id']}`\n\n"
                "Comparte este ID con tus amigos. Si ellos se unen, tu multiplicador de sinergia aumenta."
            )
            kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
            await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
            return

    # CASO B: No tiene célula
    txt = (
        "⚠️ **ORGANISMO AISLADO**\n\n"
        "Actualmente estás trabajando solo (Multiplicador x1.0).\n"
        "Las Células permiten multiplicar tus ganancias mediante Sinergia.\n\n"
        f"**Costo de Creación:** {CELL_CREATION_COST} Néctar."
    )
    
    kb = [
        [InlineKeyboardButton(f"➕ CREAR CÉLULA ({CELL_CREATION_COST} Néctar)", callback_data="create_cell_action")],
        # Nota: Unirse a célula requiere input de texto con el ID, lo manejamos via comando o chat
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_cell_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción de crear célula."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data['nectar'] < CELL_CREATION_COST:
        await query.answer(f"❌ Néctar insuficiente. Necesitas {CELL_CREATION_COST}.", show_alert=True)
        return
        
    # Cobrar
    user_data['nectar'] -= CELL_CREATION_COST
    
    # Crear
    cell_name = f"Squad-{random.randint(1000, 9999)}"
    cell_id = await db.create_cell(user_id, cell_name)
    user_data['cell_id'] = cell_id
    
    await db.save_user(user_id, user_data)
    
    await query.answer("✅ Célula Biológica Creada")
    # Redirigir al menú para verla
    await cell_menu(update, context)

# ==============================================================================
# 9. TIENDA Y EQUIPO
# ==============================================================================

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    txt = (
        f"🛒 **MERCADO ORGÁNICO**\n"
        f"Saldo Disponible: `{user_data['nectar']:.2f}` Néctar\n\n"
        "Adquiere recursos para acelerar tu evolución."
    )
    
    kb = [
        [InlineKeyboardButton(f"⚡ RECARGA COMPLETA ({COST_FULL_RECHARGE} Néctar)", callback_data="buy_energy_action")],
        [InlineKeyboardButton("👑 EVOLUCIÓN ARTIFICIAL ($10 USD)", callback_data="buy_premium_info")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data['nectar'] >= COST_FULL_RECHARGE:
        user_data['nectar'] -= COST_FULL_RECHARGE
        
        # Recargar al máximo del rol actual
        config = ROLES_CONFIG.get(user_data['role'], ROLES_CONFIG['LARVA'])
        user_data['energy'] = config['max_energy']
        
        await db.save_user(user_id, user_data)
        
        await query.answer("⚡ Inyección de Energía Exitosa", show_alert=True)
        await show_dashboard(update, context)
    else:
        await query.answer("❌ Saldo Insuficiente", show_alert=True)

async def buy_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    txt = (
        f"💎 **MEMBRESÍA GÉNESIS (PREMIUM)**\n\n"
        "Obtén acceso inmediato al Rol **REINA**:\n"
        "• Energía x10\n"
        "• Acceso a todos los Tiers\n"
        "• Multiplicador x2.0 permanente\n\n"
        f"Envía **$10 USD** (TRC20) a:\n`{CRYPTO_WALLET_USDT}`\n\n"
        "Luego envía el Hash de transacción en el chat."
    )
    
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="shop_menu")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    refs_count = len(user_data.get('referrals', []))
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    txt = (
        f"👥 **RED DE DESCENDENCIA**\n\n"
        f"Hijos Directos: {refs_count}\n"
        f"Poder de Enjambre: x{user_data.get('swarm_power', 1.0):.2f}\n\n"
        "Ganas **50 Néctar** por cada nuevo usuario verificado.\n\n"
        f"🔗 **Tu Enlace Genético:**\n`{link}`"
    )
    
    kb = [
        [InlineKeyboardButton("📤 COMPARTIR ENLACE", url=f"https://t.me/share/url?url={link}")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# 10. DISPATCHER CENTRAL DE BOTONES
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Controlador central que enruta todos los callbacks de botones.
    """
    query = update.callback_query
    data = query.data
    
    # Mapeo de Acciones
    if data == "accept_legal":
        context.user_data['waiting_for_email'] = True
        await query.message.edit_text(
            "📧 **VINCULACIÓN REQUERIDA**\n\n"
            "Escribe tu dirección de **EMAIL** para activar la billetera interna y recibir pagos:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Diccionario de Funciones
    actions = {
        "go_dashboard": show_dashboard,
        "mine_action": mine_action,
        "tasks_hub": tasks_hub,
        "tier_1": tier_1_menu,
        "tier_2": tier_2_menu,
        "tier_3": tier_3_menu,
        "verify_manual_task": verify_manual_task,
        "cell_menu": cell_menu,
        "create_cell_action": create_cell_action,
        "shop_menu": shop_menu,
        "buy_energy_action": buy_energy_action,
        "buy_premium_info": buy_premium_info,
        "team_menu": team_menu
    }
    
    # Ejecutar acción correspondiente
    if data in actions:
        await actions[data](update, context)
    
    # Responder al callback para cerrar el relojito de carga
    try:
        await query.answer()
    except Exception:
        pass
