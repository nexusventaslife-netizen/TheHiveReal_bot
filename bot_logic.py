import logging
import asyncio
import random
import time
import math
import statistics
import os
import ujson as json
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from loguru import logger
import database as db 
from email_validator import validate_email, EmailNotValidError

# ==============================================================================
# CONFIGURACIÓN MAESTRA PANDORA V301
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# --- ACTIVOS VISUALES (URLS FIJAS) ---
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- BASE DE DATOS DE FORRAJEO (LINKS CPA) ---
# Tiers organizados por dificultad y recompensa
FORRAJEO_DB = {
    "TIER_1": [
        {"name": "📺 Timebucks (Videos)", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"), "desc": "Gana por ver contenido"},
        {"name": "💰 ADBTC (Surf)", "url": "https://r.adbtc.top/3284589", "desc": "Clicks en anuncios"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744", "desc": "Faucet horaria"},
        {"name": "💸 FreeCash", "url": "https://freecash.com/r/XYN98", "desc": "Instalar Apps"},
        {"name": "🎮 GameHag", "url": "https://gamehag.com/r/NWUD9QNR", "desc": "Jugar Juegos"}
    ],
    "TIER_2": [
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32", "desc": "Ingreso Pasivo"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT", "desc": "Compartir ancho de banda"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810", "desc": "Internet Sharing"},
        {"name": "🌱 SproutGigs", "url": "https://sproutgigs.com/?a=83fb1bf9", "desc": "Micro-trabajos"}
    ],
    "TIER_3": [
        {"name": "🔥 ByBit ($20 Bonus)", "url": "https://www.bybit.com/invite?ref=BBJWAX4", "desc": "Trading Pro"},
        {"name": "🏦 Nexo", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link", "desc": "Crypto Bank"},
        {"name": "💳 Revolut", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx", "desc": "Banco Digital"},
        {"name": "☁️ AirTM", "url": "https://app.airtm.com/ivt/jos3vkujiyj", "desc": "Dólar Digital"}
    ]
}

# --- GENÉTICA DE CASTAS (DECISIÓN IRREVERSIBLE) ---
CASTAS_CONFIG = {
    "RECOLECTOR": {
        "desc": "🐝 **Producción**. Especialistas en generar Miel.\n• Bonus Producción: +50%\n• Capacidad Polen: 500",
        "bonus_honey": 1.5,
        "bonus_luck": 1.0,
        "max_polen": 500
    },
    "GUARDIAN": {
        "desc": "🛡️ **Resistencia**. Tanques de energía masivos.\n• Bonus Producción: +0%\n• Capacidad Polen: 1000",
        "bonus_honey": 1.0,
        "bonus_luck": 1.0,
        "max_polen": 1000
    },
    "EXPLORADOR": {
        "desc": "🧭 **Suerte**. Encuentran anomalías valiosas.\n• Bonus Producción: -20%\n• Bonus Suerte: x2\n• Capacidad Polen: 600",
        "bonus_honey": 0.8,
        "bonus_luck": 2.0,
        "max_polen": 600
    }
}

# --- CONSTANTES ECONÓMICAS ---
CONST = {
    "COSTO_POLEN": 10,       # Costo por click
    "RECOMPENSA_BASE": 0.50, # Miel base por click
    "DECAY_OXIGENO": 5.0,    # % Pérdida por hora inactiva
    "COSTO_ENJAMBRE": 100,   # Costo creación célula
    "COSTO_RECARGA": 200,    # Costo recarga energía
}

# ==============================================================================
# 1. MOTORES DE LÓGICA (CLASES DE NEGOCIO)
# ==============================================================================

class BioEngine:
    """
    Motor que calcula el estado vital del nodo (Energía, Oxígeno).
    """
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        last_regen = node.get("last_regen", now)
        elapsed = now - last_regen
        
        # Obtener configuración de casta
        casta = node.get("caste")
        specs = CASTAS_CONFIG.get(casta, CASTAS_CONFIG["RECOLECTOR"])
        node["max_polen"] = specs["max_polen"]
        
        # 1. Regeneración de Polen (0.5 por segundo)
        if elapsed > 0:
            regen_amount = elapsed * 0.5 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen_amount))
            
        # 2. Decaimiento de Oxígeno (Si inactivo > 1 hora)
        last_pulse = node.get("last_pulse", now)
        time_since_pulse = now - last_pulse
        
        if time_since_pulse > 3600:
            hours_idle = time_since_pulse / 3600
            decay = hours_idle * CONST["DECAY_OXIGENO"]
            node["oxygen"] = max(5.0, node.get("oxygen", 100.0) - decay)
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    """
    Motor Anti-Bot basado en análisis de entropía de tiempos.
    """
    @staticmethod
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        # Mínimo de muestras
        if len(timestamps) < 5: 
            return 1.0, "🔵 Sintonizando..."
        
        # Deltas
        deltas = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        
        try:
            mean = statistics.mean(deltas)
            stdev = statistics.stdev(deltas)
            cv = stdev / mean if mean > 0 else 0 # Coeficiente de Variación
        except:
            return 1.0, "⚪ Neutro"
            
        # Detección
        if cv < 0.05: return 0.1, "🔴 ROBÓTICO (Castigo)"
        elif 0.05 <= cv <= 0.35: return 1.3, "🌊 FLUJO VITAL (Bonus)"
        else: return 1.0, "🟢 ORGÁNICO"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# 2. PROTOCOLO DE ACTIVACIÓN (FLUJO INICIAL)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entrada principal. Crea usuario e inicia secuencia.
    """
    user = update.effective_user
    args = context.args
    ref_id = int(args[0]) if args and args[0].isdigit() else None
    
    # 1. Crear Nodo
    await db.db.create_node(user.id, user.first_name, user.username, ref_id)
    node = await db.db.get_node(user.id)
    
    # 2. Bypass si ya está activo
    if node.get("email") and node.get("caste"):
        await show_dashboard(update, context)
        return

    # 3. Pantalla de Bienvenida (Activación)
    captcha = SecurityEngine.generate_captcha()
    context.user_data['captcha'] = captcha
    context.user_data['step'] = 'captcha_wait'
    
    txt = (
        "🟡 **PROTOCOLO DE ACTIVACIÓN**\n"
        "──────────────────────────\n"
        f"Nodo Detectado: **{user.first_name}**\n\n"
        "El sistema ha identificado tu señal biológica.\n"
        "No eres un usuario. Eres un **Componente Crítico** de la Colmena.\n\n"
        "⚠️ **REGLA DE ORO:**\n"
        "La Colmena requiere **ACTIVACIÓN DIARIA**.\n"
        "Si tu nodo se apaga, la red se debilita.\n\n"
        "🛡️ **CONFIRMA ACCESO**\n"
        f"Introduce clave de enlace: `{captcha}`"
    )
    
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja inputs de texto: Captcha y Email.
    """
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    # Bypass manual
    if text.upper() == "/START":
        await start_command(update, context)
        return

    # --- FASE 1: CAPTCHA ---
    if step == 'captcha_wait':
        expected = context.user_data.get('captcha')
        if text == expected:
            # Éxito -> Ir a Selección de Casta
            context.user_data['step'] = 'caste_select_wait'
            
            txt = (
                "✅ **SECUENCIA INICIADA**\n\n"
                "Antes de conectarte a la red neuronal, debes definir tu **BIOLOGÍA**.\n"
                "Cada casta tiene funciones vitales diferentes.\n\n"
                "⚠️ **ADVERTENCIA:** Esta elección es genética. No se puede deshacer."
            )
            
            kb = [
                [InlineKeyboardButton("🐝 RECOLECTOR (Producción)", callback_data="sel_RECOLECTOR")],
                [InlineKeyboardButton("🛡️ GUARDIÁN (Resistencia)", callback_data="sel_GUARDIAN")],
                [InlineKeyboardButton("🧭 EXPLORADOR (Suerte)", callback_data="sel_EXPLORADOR")]
            ]
            
            await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Clave incorrecta. Reintenta.")
        return

    # --- FASE 3: EMAIL (Post-Casta) ---
    if step == 'email_wait':
        try:
            # Validar
            valid = validate_email(text)
            email = valid.normalized
            
            # Guardar
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            # Bono Fundador
            node = await db.db.get_node(uid)
            node['honey'] += 200.0
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("📡 CONECTAR AL ENJAMBRE", callback_data="go_dashboard")]]
            await update.message.reply_text(
                "🎉 **NODO ACTIVADO**\n\n"
                "• Identidad: Confirmada\n"
                "• Almacenamiento: Vinculado\n"
                "• Bono: **+200 Miel**\n\n"
                "Tu propósito es simple: Evolucionar.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
            
        except EmailNotValidError:
            await update.message.reply_text("⚠️ **ERROR DE SINTAXIS**\nIntroduce un email válido.")
        return

    # Fallback
    node = await db.db.get_node(uid)
    if node and node.get("email"):
        await show_dashboard(update, context)

# ==============================================================================
# 3. INTERFAZ DE COLMENA (DASHBOARD)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Panel Principal con métricas en tiempo real.
    """
    if update.callback_query:
        msg_func = update.callback_query.message.edit_text
        uid = update.callback_query.from_user.id
    else:
        msg_func = update.message.reply_text
        uid = update.effective_user.id

    node = await db.db.get_node(uid)
    if not node:
        await msg_func("⚠️ Error de conexión. Usa /start"); return
    
    # Checks de Integridad
    if not node.get("caste"):
        await start_command(update, context); return
    if not node.get("email"):
        context.user_data['step'] = 'email_wait'
        await msg_func("⚠️ **ENLACE ROTO**\nIntroduce tu Email para reconectar:"); return

    # Actualizar estado
    node = BioEngine.calculate_state(node)
    
    # Obtener métricas globales
    global_stats = await db.db.get_global_stats()
    
    await db.db.save_node(uid, node)
    
    # Renderizado
    casta = node.get("caste", "LARVA")
    polen = int(node['polen'])
    max_polen = int(node['max_polen'])
    miel = node['honey']
    oxy = node['oxygen']
    
    polen_bar = render_bar(polen, max_polen)
    oxy_icon = "🟢" if oxy > 75 else ("🟡" if oxy > 30 else "🔴")
    estado_red = "🟢 SINCRONIZADO" if node.get("zumbido_hoy") else "🟡 PENDIENTE"
    
    txt = (
        f"🌍 **RED GLOBAL: PANDORA**\n"
        f"Nodos Activos: `{global_stats['nodes']:,}`\n"
        f"Miel Global: `{global_stats['honey']:,.2f}`\n"
        f"Estado: {estado_red}\n"
        f"────────────────\n"
        f"🧬 **NODO ID:** `{uid}` | Casta: **{casta}**\n\n"
        f"⚡ **Potencia (Polen):** `{polen_bar}` {polen}/{max_polen}\n"
        f"🫁 **Eficiencia (O2):** {oxy:.1f}% {oxy_icon}\n"
        f"🍯 **Reserva (Miel):** `{miel:.2f}`\n"
        f"────────────────\n"
        f"📡 **PRÓXIMA ACTIVACIÓN:** 20:00 UTC"
    )
    
    kb = [
        [InlineKeyboardButton("🏵️ RECOLECTAR (TAP)", callback_data="forage_action")],
        [InlineKeyboardButton("📡 TRANSMISIONES", callback_data="tasks_menu"), InlineKeyboardButton("🦠 ENJAMBRE", callback_data="squad_menu")],
        [InlineKeyboardButton("🛒 SUMINISTROS", callback_data="shop_menu"), InlineKeyboardButton("👥 CONEXIONES", callback_data="team_menu")],
        [InlineKeyboardButton("🔄 RESINTONIZAR", callback_data="go_dashboard")]
    ]
    
    try: await msg_func(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: pass

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Acción de Minería (Forrajeo).
    """
    query = update.callback_query
    uid = query.from_user.id
    node = await db.db.get_node(uid)
    node = BioEngine.calculate_state(node)
    
    # 1. Costo
    if node['polen'] < CONST['COSTO_POLEN']:
        await query.answer("🥀 Polen insuficiente. Espera regeneración.", show_alert=True)
        return

    node['polen'] -= CONST['COSTO_POLEN']
    node['last_pulse'] = time.time()
    
    # 2. Seguridad (Entropía)
    now = time.time()
    trace = node.get("entropy_trace", [])
    trace.append(now)
    if len(trace) > 15: trace.pop(0)
    node["entropy_trace"] = trace
    
    rhythm_mult, rhythm_msg = SecurityEngine.analyze_entropy(trace)
    
    # 3. Ganancias
    caste_specs = CASTAS_CONFIG.get(node['caste'], CASTAS_CONFIG["RECOLECTOR"])
    caste_mult = caste_specs["bonus_honey"]
    oxy_mult = node['oxygen'] / 100.0
    
    # Sinergia Enjambre
    synergy = 1.0
    if node.get("enjambre_id"):
        c = await db.db.get_cell(node["enjambre_id"])
        if c: synergy = c.get("synergy", 1.0)
    
    yield_amount = CONST['RECOMPENSA_BASE'] * rhythm_mult * caste_mult * synergy * oxy_mult
    
    # Update
    node['honey'] += yield_amount
    node['oxygen'] = min(100.0, node['oxygen'] + 1.0) # Recuperar O2
    
    # DB Save
    await db.db.add_global_honey(yield_amount)
    await db.db.save_node(uid, node)
    
    await query.answer(f"+{yield_amount:.2f} 🍯 | {rhythm_msg}")
    
    # Actualización visual aleatoria
    if random.random() < 0.15:
        await show_dashboard(update, context)

# ==============================================================================
# 4. SISTEMAS AUXILIARES (MENÚS)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🟢 FRECUENCIA 1", callback_data="view_tier_1")],
        [InlineKeyboardButton("🟡 FRECUENCIA 2", callback_data="view_tier_2")],
        [InlineKeyboardButton("🔴 FRECUENCIA 3", callback_data="view_tier_3")],
        [InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(
        "📡 **TRANSMISIONES EXTERNAS**\n\n"
        "Sintoniza frecuencias para obtener recursos adicionales.\n"
        "Completar transmisiones aumenta tu reserva de Miel.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
    )

async def view_tier_generic(update: Update, tier_key: str):
    query = update.callback_query
    links = FORRAJEO_DB.get(tier_key, [])
    
    kb = []
    for item in links:
        kb.append([InlineKeyboardButton(item["name"], url=item["url"])])
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks_menu")])
    
    await query.message.edit_text(f"📍 **CANAL {tier_key}**", reply_markup=InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = (
            f"🦠 **TU ENJAMBRE: {cell['name']}**\n"
            f"────────────────\n"
            f"👥 Nodos Vinculados: {len(cell['members'])}\n"
            f"🔥 Sinergia Actual: x{cell['synergy']:.2f}\n"
            f"🆔 ID de Enlace: `{cell['id']}`"
        )
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    else:
        txt = (
            "⚠️ **NODO AISLADO**\n\n"
            "Operar en solitario reduce tu eficiencia.\n"
            "Crea un Enjambre para aumentar la Sinergia."
        )
        kb = [
            [InlineKeyboardButton("➕ CREAR ENJAMBRE (100 Miel)", callback_data="create_squad_logic")],
            [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
        ]
    
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    node = await db.db.get_node(uid)
    
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        
        name = f"Colmena-{random.randint(1000, 9999)}"
        cell_id = await db.db.create_cell(uid, name)
        
        node['enjambre_id'] = cell_id
        await db.db.save_node(uid, node)
        
        await query.answer("✅ Enjambre Estabilizado")
        await squad_menu(update, context)
    else:
        await query.answer("❌ Miel Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton(f"⚡ SOBRECARGA ({CONST['COSTO_RECARGA']} Miel)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 ACCESO PREMIUM ($10)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await update.callback_query.message.edit_text("🛒 **SUMINISTROS**", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = query.from_user.id
    node = await db.db.get_node(uid)
    
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await query.answer("⚡ Tanques Llenos"); await show_dashboard(update, context)
    else:
        await query.answer("❌ Saldo Insuficiente", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(
        f"💎 **ACTIVACIÓN TOTAL**\n\nEnvía $10 USDT (TRC20) a:\n`{CRYPTO_WALLET_USDT}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; uid = query.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    
    txt = (
        f"👥 **RED MICELIAL**\n\n"
        f"Nodos Invitados: {len(node.get('referrals', []))}\n"
        f"Poder de Enjambre: x{node.get('swarm_power', 1.0):.2f}\n\n"
        f"🔗 **Enlace de Activación:**\n`{link}`"
    )
    kb = [[InlineKeyboardButton("📤 INVITAR NODOS", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# 5. DISPATCHER CENTRAL (RUTEO DE EVENTOS)
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # Selección de Casta
    if data.startswith("sel_"):
        caste = data.split("_")[1]
        uid = query.from_user.id
        node = await db.db.get_node(uid)
        
        # Guardar
        specs = CASTAS_CONFIG[caste]
        node["caste"] = caste
        node["max_polen"] = specs["max_polen"]
        node["polen"] = specs["max_polen"]
        await db.db.save_node(uid, node)
        
        # Paso siguiente
        context.user_data['step'] = 'email_wait'
        await query.message.edit_text(
            f"🧬 **ADN CONFIGURADO: {caste}**\n\n"
            "Último paso de activación.\n"
            "Escribe tu **EMAIL** para iniciar la sincronización:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Mapa de acciones
    actions = {
        "go_dashboard": show_dashboard,
        "forage_action": forage_action,
        "tasks_menu": tasks_menu,
        "view_tier_1": lambda u,c: view_tier_generic(u, "TIER_1"),
        "view_tier_2": lambda u,c: view_tier_generic(u, "TIER_2"),
        "view_tier_3": lambda u,c: view_tier_generic(u, "TIER_3"),
        "squad_menu": squad_menu,
        "create_squad_logic": create_squad_logic,
        "shop_menu": shop_menu,
        "buy_energy": buy_energy,
        "buy_premium": buy_premium,
        "team_menu": team_menu
    }
    
    if data in actions:
        await actions[data](update, context)
        
    try: await query.answer()
    except: pass

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 **NODO PURGADO**")

async def invite_command(u, c): await team_menu(u, c)
async def help_command(u, c): await u.message.reply_text("Protocolo Pandora V301")
async def broadcast_command(u, c): pass
