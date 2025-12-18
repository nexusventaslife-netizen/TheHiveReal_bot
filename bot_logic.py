import asyncio
import random
import time
import math
import statistics
import os
import ujson as json
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from loguru import logger
from database import db
from email_validator import validate_email, EmailNotValidError

# ==============================================================================
# 1. CONFIGURACIÓN MAESTRA DEL SISTEMA (HIVE CONFIG)
# ==============================================================================

# Variables Administrativas
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "T-PENDING-ADDRESS-TRC20")
SUPPORT_CONTACT = "@SoportePandora"

# Assets Visuales (CDNs)
IMG_WELCOME = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_LEVEL_UP = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- MATRIX DE ENLACES CPA (TIER SYSTEM) ---
# Estructura expandida con metadata para UI futura
LINKS_DB = {
    "TIER_1": {
        "TIMEBUCKS": {"url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"), "desc": "Videos y Encuestas", "payout": "$0.50"},
        "ADBTC": {"url": "https://r.adbtc.top/3284589", "desc": "Surf Ads Crypto", "payout": "Sats"},
        "FREEBITCOIN": {"url": "https://freebitco.in/?r=55837744", "desc": "Faucet Horaria", "payout": "BTC"},
        "FAUCETPAY": {"url": "https://faucetpay.io/?r=2275014", "desc": "MicroWallet + Earn", "payout": "Multi"},
        "COINTIPLY": {"url": "https://cointiply.com/r/jR1L6y", "desc": "Offerwalls", "payout": "$1.00"},
        "GAMEHAG": {"url": "https://gamehag.com/r/NWUD9QNR", "desc": "Juega y Gana", "payout": "Items"},
        "FREECASH": {"url": "https://freecash.com/r/XYN98", "desc": "Apps Testing", "payout": "$2.00"},
        "SWAGBUCKS": {"url": "https://www.swagbucks.com/p/register?rb=226213635&rp=1", "desc": "Gigante GPT", "payout": "$5.00"},
        "EVERVE": {"url": "https://everve.net/ref/1950045/", "desc": "Social Exchange", "payout": "$0.10"}
    },
    "TIER_2": {
        "HONEYGAIN": {"url": "https://join.honeygain.com/ALEJOE9F32", "desc": "Comparte Internet", "payout": "Pasivo"},
        "PACKETSTREAM": {"url": "https://packetstream.io/?psr=7hQT", "desc": "Banda Ancha P2P", "payout": "Pasivo"},
        "PAWNS": {"url": "https://pawns.app/?r=18399810", "desc": "Internet Sharing", "payout": "Pasivo"},
        "TRAFFMONETIZER": {"url": "https://traffmonetizer.com/?aff=2034896", "desc": "Monetiza Tráfico", "payout": "Pasivo"},
        "PAIDWORK": {"url": "https://www.paidwork.com/?r=nexus.ventas.life", "desc": "Freelance Micro", "payout": "Varía"},
        "SPROUTGIGS": {"url": "https://sproutgigs.com/?a=83fb1bf9", "desc": "Micro Jobs", "payout": "$1.00"},
        "GOTRANSCRIPT": {"url": "https://gotranscript.com/r/7667434", "desc": "Transcripción", "payout": "Alto"},
        "TESTBIRDS": {"url": "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381", "desc": "UX Testing", "payout": "€10+"}
    },
    "TIER_3": {
        "BYBIT": {"url": "https://www.bybit.com/invite?ref=BBJWAX4", "desc": "Exchange Top 3", "payout": "$20 Bonus"},
        "NEXO": {"url": "https://nexo.com/ref/rbkekqnarx?src=android-link", "desc": "Crypto Bank", "payout": "$25 BTC"},
        "REVOLUT": {"url": "https://revolut.com/referral/?referral-code=alejandroperdbhx", "desc": "Banco Digital", "payout": "€40"},
        "WISE": {"url": "https://wise.com/invite/ahpc/josealejandrop73", "desc": "Transferencias", "payout": "£50"},
        "AIRTM": {"url": "https://app.airtm.com/ivt/jos3vkujiyj", "desc": "Dólar Digital", "payout": "$2.00"},
        "BETFURY": {"url": "https://betfury.io/?r=6664969919f42d20e7297e29", "desc": "iGaming & Staking", "payout": "Varía"},
        "PLUS500": {"url": "https://www.plus500.com/en-uy/refer-friend", "desc": "Trading CFD", "payout": "Alto"},
        "YOUHODLER": {"url": "https://app.youhodler.com/sign-up?ref=SXSSSNB1", "desc": "Yield Account", "payout": "APY High"}
    }
}

# --- ECONOMÍA Y JUEGO ---
ROLES_CONFIG = {
    "LARVA":      {"xp": 0,     "max_energy": 300,  "regen": 0.5, "tiers": ["TIER_1"]},
    "OBRERO":     {"xp": 500,   "max_energy": 500,  "regen": 0.8, "tiers": ["TIER_1", "TIER_2"]},
    "EXPLORADOR": {"xp": 1500,  "max_energy": 800,  "regen": 1.0, "tiers": ["TIER_1", "TIER_2", "TIER_3"]},
    "GUARDIAN":   {"xp": 3500,  "max_energy": 1200, "regen": 1.5, "tiers": ["TIER_1", "TIER_2", "TIER_3"]},
    "NODO":       {"xp": 7000,  "max_energy": 2500, "regen": 2.0, "tiers": ["TIER_1", "TIER_2", "TIER_3"]},
    "GENESIS":    {"xp": 20000, "max_energy": 5000, "regen": 5.0, "tiers": ["ALL"]}
}

CONSTANTS = {
    "ENERGY_COST": 10,
    "BASE_REWARD": 0.50,
    "RECHARGE_COST": 200,
    "CELL_COST": 100,
    "OXYGEN_DECAY_HOUR": 5.0, # 5% por hora
    "PREMIUM_PRICE": 10.0 # USD
}

# ==============================================================================
# 2. MOTORES DE LÓGICA (CLASES DE NEGOCIO)
# ==============================================================================

class BioEngine:
    """Calcula la biología del usuario: Energía, Oxígeno, Niveles."""
    
    @staticmethod
    def calculate_state(user: Dict) -> Dict:
        now = time.time()
        last_regen = user.get("last_regen", now)
        elapsed = now - last_regen
        
        role = user.get("role", "LARVA")
        config = ROLES_CONFIG.get(role, ROLES_CONFIG["LARVA"])
        
        # 1. Regenerar Energía
        if elapsed > 0:
            regen = elapsed * config["regen"]
            new_energy = user["energy"] + int(regen)
            user["energy"] = min(config["max_energy"], new_energy)
            user["max_energy"] = config["max_energy"] # Sync max cap
            
        # 2. Decaer Oxígeno (Adicción)
        # El oxígeno decae si no hay interacción (last_pulse)
        last_pulse = user.get("last_pulse", now)
        idle_time = now - last_pulse
        
        if idle_time > 3600: # 1 Hora
            hours_idle = idle_time / 3600
            decay_amount = hours_idle * CONSTANTS["OXYGEN_DECAY_HOUR"]
            # No permitir que baje de 5%
            user["oxygen"] = max(5.0, user.get("oxygen", 100.0) - decay_amount)
            
        # 3. Evolución de Rol
        # Verificamos si merece un upgrade
        current_xp = user.get("role_xp", 0)
        best_role = role
        
        for r_name, r_data in ROLES_CONFIG.items():
            if current_xp >= r_data["xp"]:
                # Comprobación de jerarquía simple basada en XP
                if r_data["xp"] >= ROLES_CONFIG[best_role]["xp"]:
                    best_role = r_name
        
        if best_role != role:
            user["role"] = best_role
            user["energy"] = ROLES_CONFIG[best_role]["max_energy"] # Heal completo
            
        user["last_regen"] = now
        return user

class SecurityEngine:
    """Motor Anti-Fraude y Entropía."""
    
    @staticmethod
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        if len(timestamps) < 5: 
            return 1.0, "🔵 Calibrando Sensores..."
        
        deltas = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        
        try:
            mean = statistics.mean(deltas)
            stdev = statistics.stdev(deltas)
            cv = stdev / mean if mean > 0 else 0
        except:
            return 1.0, "⚪ Neutro"
            
        # CV < 0.05 -> Bot (Muy preciso)
        # CV > 1.5 -> Lento (Humano distraído)
        # 0.05 < CV < 0.3 -> Flow (Humano óptimo)
        
        if cv < 0.05: return 0.1, "🔴 DETECTADO: Patrón Robótico"
        elif 0.05 <= cv <= 0.35: return 1.4, "🌊 BIO-RITMO PERFECTO (Bonus)"
        elif cv > 1.5: return 0.8, "💤 Señal Débil"
        else: return 1.0, "🟢 Señal Humana"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# 3. HANDLERS DE COMANDOS (PUNTOS DE ENTRADA)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start: Inicia el onboarding estricto.
    """
    user = update.effective_user
    args = context.args
    ref_id = int(args[0]) if args and args[0].isdigit() else None
    
    # 1. Crear Usuario
    is_new = await db.create_user(user.id, user.first_name, user.username, ref_id)
    user_data = await db.get_user(user.id)
    
    # 2. Verificar Estado
    # Si ya pasó el captcha y tiene email, mandar al dashboard
    if user_data and user_data.get("email") and user_data.get("captcha_passed"):
        await show_dashboard(update, context)
        return

    # 3. Flujo de Iniciación (Captcha)
    captcha = SecurityEngine.generate_captcha()
    context.user_data['captcha'] = captcha
    context.user_data['step'] = 'captcha'
    
    txt = (
        f"🧬 **PROTOCOLO PANDORA: SECUENCIA DE INICIO**\n"
        f"────────────────────────────────\n"
        f"Sujeto: **{user.first_name}** (ID: `{user.id}`)\n\n"
        "Has sido seleccionado para la integración en el Enjambre.\n"
        "Este sistema monetiza tu tiempo y bio-ritmo.\n\n"
        "🛡️ **VERIFICACIÓN REQUERIDA**\n"
        "Para asignar tu ID de Larva, confirma tu humanidad:\n\n"
        f"🔒 CÓDIGO: `{captcha}`\n\n"
        "👇 **Escribe el código abajo:**"
    )
    
    try: await update.message.reply_photo(IMG_WELCOME, caption=txt, parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reset: Borra todos los datos (Dev Mode).
    """
    uid = update.effective_user.id
    await db.delete_user(uid)
    context.user_data.clear()
    await update.message.reply_text("🗑️ **HARD RESET EJECUTADO**\nDatos eliminados. Usa /start.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "📚 **DOCUMENTACIÓN DE OPERACIONES**\n\n"
        "1. **Minería (Tap):** Extrae Néctar. Tu ritmo define la ganancia.\n"
        "2. **Oxígeno:** Mantén tu nivel alto (>80%) o tus ingresos caerán.\n"
        "3. **Células:** Grupos de trabajo. Aumentan tu multiplicador.\n"
        "4. **Tiers:** Tareas externas que pagan en USD/Cripto.\n\n"
        "🔧 **Comandos:**\n"
        "/start - Reinicio\n"
        "/invitar - Red de referidos\n"
        "/reset - Borrar cuenta"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await team_menu(update, context)

# ==============================================================================
# 4. GESTOR DE MENSAJES (MÁQUINA DE ESTADOS)
# ==============================================================================

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja el flujo: Captcha -> Email -> Dashboard.
    """
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    # COMANDO MANUAL BYPASS
    if text.upper() == "/START":
        await start_command(update, context)
        return

    # --- PASO 1: CAPTCHA ---
    if step == 'captcha':
        expected = context.user_data.get('captcha')
        if text == expected:
            # Éxito
            context.user_data['step'] = 'email'
            user = await db.get_user(uid)
            user['captcha_passed'] = True
            await db.save_user(uid, user)
            
            kb = [[InlineKeyboardButton("✅ ACEPTAR VINCULACIÓN", callback_data="accept_legal")]]
            await update.message.reply_text(
                "✅ **IDENTIDAD BIOLÓGICA CONFIRMADA**\n\n"
                "Para recibir pagos del ecosistema (CPA/Crypto), debemos vincular una identidad digital.\n"
                "¿Aceptas sincronizarte con el Enjambre?",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ **ERROR DE ACCESO**\nCódigo incorrecto. Intenta de nuevo.")
        return

    # --- PASO 2: EMAIL ---
    if step == 'email_wait':
        try:
            # Validar email con librería robusta
            valid = validate_email(text)
            email = valid.normalized
            
            # Guardar
            await db.update_email(uid, email)
            context.user_data['step'] = 'done'
            
            # Bono de Bienvenida
            u = await db.get_user(uid)
            u['nectar'] += 150.0
            await db.save_user(uid, u)
            
            kb = [[InlineKeyboardButton("🚀 ENTRAR AL NÚCLEO", callback_data="go_dashboard")]]
            await update.message.reply_text(
                "🎉 **SINCRONIZACIÓN EXITOSA**\n\n"
                "• Identidad: Verificada\n"
                "• Billetera Interna: Creada\n"
                "• Bono: **+150 Néctar**\n\n"
                "Tu organismo está listo. Comienza la evolución.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
            
        except EmailNotValidError:
            await update.message.reply_text("⚠️ **EMAIL INVÁLIDO**\nPor favor ingresa un correo real.")
        return

    # FALLBACK
    user = await db.get_user(uid)
    if user and user.get("email"):
        await show_dashboard(update, context)

# ==============================================================================
# 5. DASHBOARD (HUD PRINCIPAL)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Renderiza el panel principal con todas las stats.
    """
    if update.callback_query:
        msg_func = update.callback_query.message.edit_text
        uid = update.callback_query.from_user.id
    else:
        msg_func = update.message.reply_text
        uid = update.effective_user.id

    user = await db.get_user(uid)
    if not user:
        await msg_func("⚠️ Error crítico de datos. Usa /reset.")
        return

    # Chequeo de seguridad: Si no tiene email, mandarlo a ponerlo
    if not user.get("email"):
        context.user_data['step'] = 'email_wait'
        await msg_func("⚠️ **ACCIÓN REQUERIDA**\nEscribe tu Email para continuar:")
        return

    # Procesar lógica de juego (Regenerar, Decaer)
    user = BioEngine.calculate_state(user)
    await db.save_user(uid, user)
    
    # Preparar visualización
    role = user['role']
    energy = int(user['energy'])
    max_e = int(user['max_energy'])
    oxy = float(user['oxygen'])
    nectar = float(user['nectar'])
    usd = float(user['usd_balance'])
    xp = int(user['role_xp'])
    
    # Renderizado de Barras
    oxy_icon = "🟢" if oxy > 70 else ("🟡" if oxy > 30 else "🔴")
    # Barra ASCII simple: 10 bloques
    filled = int((energy / max_e) * 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    # Info de Célula
    cell_info = "Sin Célula"
    if user.get("cell_id"):
        cell = await db.get_cell(user["cell_id"])
        if cell: cell_info = f"{cell['name']} (x{cell['synergy_level']:.2f})"

    txt = (
        f"🧬 **NÚCLEO PANDORA** | Rango: **{role}**\n"
        f"────────────────────────\n"
        f"🫁 **Oxígeno:** {oxy:.1f}% {oxy_icon}\n"
        f"⚡ **Energía:** `{bar}` {energy}/{max_e}\n"
        f"🦠 **Célula:** {cell_info}\n"
        f"────────────────────────\n"
        f"🪙 **Néctar:** `{nectar:.2f}`\n"
        f"💵 **Saldo:** `${usd:.2f}`\n"
        f"📈 **XP:** {xp}\n"
        f"────────────────────────\n"
        f"💡 *Mantén tu oxígeno alto para maximizar ganancias.*"
    )
    
    kb = [
        [InlineKeyboardButton("⛏️ SINTETIZAR (TAP)", callback_data="mine_action")],
        [InlineKeyboardButton("🧠 TAREAS", callback_data="tasks_menu"), InlineKeyboardButton("🦠 CÉLULA", callback_data="cell_menu")],
        [InlineKeyboardButton("🛒 TIENDA", callback_data="shop_menu"), InlineKeyboardButton("👥 EQUIPO", callback_data="team_menu")],
        [InlineKeyboardButton("🔄 REFRESCAR", callback_data="go_dashboard")]
    ]
    
    try: await msg_func(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: pass

# ==============================================================================
# 6. MECÁNICA DE MINADO (TAP)
# ==============================================================================

async def mine_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Acción principal de juego.
    Integra: Energía, Bio-Ritmo, Sinergia y Oxígeno.
    """
    query = update.callback_query
    uid = query.from_user.id
    
    # 1. Cargar y Actualizar
    user = await db.get_user(uid)
    user = BioEngine.calculate_state(user)
    
    # 2. Check Energía
    if user['energy'] < CONSTANTS["ENERGY_COST"]:
        await query.answer(f"⚡ Energía Agotada. Recarga o espera.", show_alert=True)
        return

    # 3. Consumo
    user['energy'] -= CONSTANTS["ENERGY_COST"]
    user['last_pulse'] = time.time() # Resetear decaimiento oxígeno
    
    # 4. Cálculo de Entropía (Anti-Bot)
    now = time.time()
    trace = user.get("entropy_trace", [])
    trace.append(now)
    if len(trace) > 15: trace.pop(0)
    user["entropy_trace"] = trace
    
    rhythm_mult, rhythm_msg = SecurityEngine.analyze_entropy(trace)
    
    # 5. Cálculo de Sinergia
    synergy_mult = 1.0
    if user.get("cell_id"):
        cell = await db.get_cell(user["cell_id"])
        if cell: synergy_mult = cell.get("synergy_level", 1.0)
            
    # 6. Fórmula Maestra
    # Ganancia = Base * Ritmo * Sinergia * (Oxígeno / 100)
    oxy_mult = user.get("oxygen", 100.0) / 100.0
    total_gain = CONSTANTS["BASE_REWARD"] * rhythm_mult * synergy_mult * oxy_mult
    
    # Aplicar
    user['nectar'] += total_gain
    user['role_xp'] += 1.0 * rhythm_mult # XP basada en habilidad
    user['oxygen'] = min(100.0, user['oxygen'] + 1.5) # Recuperar oxígeno
    
    # Guardar atómicamente
    await db.save_user(uid, user)
    
    # Feedback
    await query.answer(f"+{total_gain:.2f} | {rhythm_msg}")
    
    # Actualizar UI visualmente a veces (ahorrar API calls)
    if random.random() < 0.2:
        await show_dashboard(update, context)

# ==============================================================================
# 7. MENÚ DE TAREAS (TIER SYSTEM)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🟢 TIER 1 (Larvas)", callback_data="view_tier_1")],
        [InlineKeyboardButton("🟡 TIER 2 (Obreros)", callback_data="view_tier_2")],
        [InlineKeyboardButton("🔴 TIER 3 (Elite)", callback_data="view_tier_3")],
        [InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(
        "🧠 **MATRIZ DE TAREAS**\n\n"
        "Selecciona el nivel de complejidad.\n"
        "Los Tiers superiores pagan más pero requieren mayor rango.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
    )

async def view_tier_generic(update: Update, tier_key: str, min_role_idx: int):
    """Renderizador genérico de menús de Tiers."""
    query = update.callback_query
    uid = query.from_user.id
    user = await db.get_user(uid)
    
    # Check de Rol (Índice en lista de claves de ROLES_CONFIG)
    roles_list = list(ROLES_CONFIG.keys())
    user_role_idx = roles_list.index(user['role'])
    
    if user_role_idx < min_role_idx and not user.get('is_premium'):
        req_role = roles_list[min_role_idx]
        await query.answer(f"🔒 ACCESO DENEGADO. Requiere Rol: {req_role}", show_alert=True)
        return

    # Construir Botones dinámicamente desde LINKS_DB
    links_data = LINKS_DB.get(tier_key, {})
    buttons = []
    row = []
    
    for name, info in links_data.items():
        btn = InlineKeyboardButton(f"{name} ({info['payout']})", url=info['url'])
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_menu")])
    
    colors = {"TIER_1": "🟢", "TIER_2": "🟡", "TIER_3": "🔴"}
    
    await query.message.edit_text(
        f"{colors[tier_key]} **{tier_key.replace('_', ' ')}**\n"
        "Completa estas tareas para ganar USD y Cripto real.",
        reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN
    )

async def tier_1_handler(u, c): await view_tier_generic(u, "TIER_1", 0)
async def tier_2_handler(u, c): await view_tier_generic(u, "TIER_2", 1) # Obrero
async def tier_3_handler(u, c): await view_tier_generic(u, "TIER_3", 2) # Explorador

# ==============================================================================
# 8. CÉLULAS Y TIENDA
# ==============================================================================

async def cell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = await db.get_user(uid)
    
    if user.get("cell_id"):
        # Ver mi célula
        cell = await db.get_cell(user["cell_id"])
        txt = (
            f"🦠 **CÉLULA: {cell['name']}**\n"
            f"────────────────\n"
            f"👥 Miembros: {len(cell['members'])}\n"
            f"🔥 Sinergia: x{cell['synergy_level']:.2f}\n"
            f"🆔 ID: `{cell['id']}`\n\n"
            "Comparte el ID con otros para que se unan."
        )
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    else:
        # Menú sin célula
        txt = (
            "⚠️ **ORGANISMO AISLADO**\n\n"
            "Estás perdiendo el bono de Sinergia.\n"
            f"Crea tu propia célula por {CONSTANTS['CELL_COST']} Néctar."
        )
        kb = [
            [InlineKeyboardButton("➕ CREAR CÉLULA", callback_data="create_cell_logic")],
            [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
        ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_cell_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = query.from_user.id
    user = await db.get_user(uid)
    
    if user['nectar'] >= CONSTANTS['CELL_COST']:
        user['nectar'] -= CONSTANTS['CELL_COST']
        name = f"Squad-{random.randint(1000, 9999)}"
        cid = await db.create_cell(uid, name)
        user['cell_id'] = cid
        await db.save_user(uid, user)
        await query.answer("✅ Célula Fundada")
        await cell_menu(update, context)
    else:
        await query.answer("❌ Néctar insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton(f"⚡ RECARGA ({CONSTANTS['RECHARGE_COST']} Néctar)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 PREMIUM ($10 USD)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🛒 **MERCADO**", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = query.from_user.id
    user = await db.get_user(uid)
    
    if user['nectar'] >= CONSTANTS['RECHARGE_COST']:
        user['nectar'] -= CONSTANTS['RECHARGE_COST']
        cfg = ROLES_CONFIG.get(user['role'], ROLES_CONFIG['LARVA'])
        user['energy'] = cfg['max_energy']
        await db.save_user(uid, user)
        await query.answer("⚡ Recargado")
        await show_dashboard(update, context)
    else:
        await query.answer("❌ Sin fondos")

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        f"💎 **MEMBRESÍA GÉNESIS**\n\n"
        f"Envía ${CONSTANTS['PREMIUM_PRICE']} USDT (TRC20) a:\n"
        f"`{CRYPTO_WALLET_USDT}`\n\n"
        "Envía el hash al soporte: " + SUPPORT_CONTACT,
        parse_mode=ParseMode.MARKDOWN
    )

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = query.from_user.id
    user = await db.get_user(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    
    txt = (
        f"👥 **RED DE DESCENDENCIA**\n\n"
        f"Referidos: {len(user.get('referrals', []))}\n"
        f"Poder de Enjambre: x{user.get('swarm_power', 1.0):.2f}\n\n"
        f"🔗 **Tu Enlace:**\n`{link}`"
    )
    kb = [
        [InlineKeyboardButton("📤 COMPARTIR", url=f"https://t.me/share/url?url={link}")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# 9. DISPATCHER DE BOTONES
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "accept_legal":
        context.user_data['step'] = 'email_wait'
        await query.message.edit_text("📧 Escribe tu **EMAIL** para activar la cuenta:")
        return

    mapping = {
        "go_dashboard": show_dashboard, "mine_action": mine_action,
        "tasks_menu": tasks_menu, "view_tier_1": tier_1_handler,
        "view_tier_2": tier_2_handler, "view_tier_3": tier_3_handler,
        "cell_menu": cell_menu, "create_cell_logic": create_cell_logic,
        "shop_menu": shop_menu, "buy_energy": buy_energy,
        "buy_premium": buy_premium, "team_menu": team_menu
    }
    
    if data in mapping:
        await mapping[data](update, context)
        
    try: await query.answer()
    except: pass
