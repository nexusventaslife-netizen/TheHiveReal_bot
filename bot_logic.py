import logging
import asyncio
import random
import time
import math
import statistics
import os
import ujson as json
from typing import Tuple, List, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from loguru import logger
import database as db 
from email_validator import validate_email, EmailNotValidError

# ==============================================================================
# 🐝 THE ONE HIVE: DAY 0 LAUNCH CONFIGURATION
# ==============================================================================

logger = logging.getLogger("HiveMind")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# Assets Visuales (Misterio y "Fase Temprana")
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE CALIBRACIÓN (DÍA 0) ---
CONST = {
    "COSTO_POLEN": 10,        # Energía por acción
    "RECOMPENSA_BASE": 0.50,  # Emisión inicial (Alta para enganchar)
    "DECAY_OXIGENO": 4.0,     # Presión suave de inactividad
    "COSTO_ENJAMBRE": 100,    # Barrera baja para viralizar
    "COSTO_RECARGA": 200,     # Prioridad
    "BONO_REFERIDO": 500,     # Incentivo fuerte
    "PRECIO_ACELERADOR": 9.99 # USD
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 300,  "bonus_tap": 0.8, "icono": "🐛"},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 500,  "bonus_tap": 1.0, "icono": "🐝"},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 1000, "bonus_tap": 1.2, "icono": "🔭"},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 2000, "bonus_tap": 1.5, "icono": "🛡️"},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑"}
}

# --- PANALES ACTIVOS (MONETIZACIÓN DÍA 0) ---
FORRAJEO_DB = {
    "TIER_1": [ # PANAL VERDE (Tráfico)
        {"name": "⚡ ACCIÓN PATROCINADA (Prioridad)", "url": "https://t.me/AnuncianteDeTurno"}, 
        {"name": "📺 Timebucks (Video)", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC (Click)", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "💸 FreeCash (Rápido)", "url": "https://freecash.com/r/XYN98"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"}
    ],
    "TIER_2": [ # PANAL DORADO (Retención)
        {"name": "🐝 Honeygain (Pasivo)", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810"},
        {"name": "🌱 SproutGigs", "url": "https://sproutgigs.com/?a=83fb1bf9"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"}
    ],
    "TIER_3": [ # PANAL ROJO (High Ticket)
        {"name": "🔥 ByBit (+20 USDT)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🏦 Nexo (Yield)", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"},
        {"name": "🆗 OKX", "url": "https://www.okx.com/join/PANDORA"}
    ]
}

# ==============================================================================
# FUNCIONES VISUALES
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_evolution_progress(hive: float, referrals: int) -> str:
    poder = hive + (referrals * CONST["BONO_REFERIDO"])
    niveles = list(RANGOS_CONFIG.values())
    siguiente = None
    for nivel in niveles:
        if nivel["meta_hive"] > poder:
            siguiente = nivel
            break
    if siguiente:
        falta = siguiente["meta_hive"] - poder
        return f"Evolución: Faltan {falta:,.0f}"
    return "ORGANISMO PERFECCIONADO"

# ==============================================================================
# MOTOR BIOLÓGICO
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0)
        refs = len(node.get("referrals", []))
        poder = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango_actual = "LARVA"
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder >= data["meta_hive"]:
                rango_actual = nombre
                stats = data
        
        node["caste"] = rango_actual 
        node["max_polen"] = stats["max_energia"]
        
        if elapsed > 0:
            regen = elapsed * 0.8 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        last_pulse = node.get("last_pulse", now)
        if (now - last_pulse) > 3600:
            decay = ((now - last_pulse) / 3600) * CONST["DECAY_OXIGENO"]
            node["oxygen"] = max(5.0, node.get("oxygen", 100.0) - decay)
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    @staticmethod
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        if len(timestamps) < 5: return 1.0, ""
        deltas = [timestamps[i]-timestamps[i-1] for i in range(1,len(timestamps))]
        try:
            cv = statistics.stdev(deltas) / statistics.mean(deltas)
        except: return 1.0, ""
        
        if cv < 0.05: return 0.1, "🚫 ANOMALÍA"
        if 0.05 <= cv <= 0.35: return 1.3, "🔥 ACTIVO"
        return 1.0, "✅"

    @staticmethod
    def generate_access_code() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# ONBOARDING (CONSENTIMIENTO LEGAL + ENGANCHE)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    try:
        await db.db.create_node(user.id, user.first_name, user.username, ref)
        node = await db.db.get_node(user.id)
        
        if node.get("email"):
            await show_dashboard(update, context)
            return

        code = SecurityEngine.generate_access_code()
        context.user_data['captcha'] = code
        context.user_data['step'] = 'captcha_wait'
        
        # COPYWRITING: FASE TEMPRANA (DÍA 0)
        txt = (
            "🐝 **THE ONE HIVE**\n"
            "────────────────────\n"
            "Bienvenido a The One Hive.\n\n"
            "Esto no es un juego.\n"
            "No es una promesa rápida.\n"
            "Es una fase temprana de un sistema vivo.\n\n"
            "Cada acción deja rastro.\n"
            "Cada miembro fortalece la colmena.\n\n"
            "Entras ahora cuando todo todavía se está formando.\n"
            f"🔐 **Validación:** `{code}`"
        )
        try: await update.message.reply_photo(IMG_GENESIS, caption=txt, parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error start: {e}")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    # PASO 1: CAPTCHA
    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            
            # CONSENTIMIENTO EXPLÍCITO (MARKETING/INFO)
            kb = [[InlineKeyboardButton("👉 Entrar a la Colmena", callback_data="accept_terms")]]
            await update.message.reply_text(
                "📡 **PROTOCOLO DE SINCRONIZACIÓN**\n\n"
                "Para ingresar, debes aceptar la conexión neural.\n"
                "Recibirás datos críticos, ofertas del enjambre y actualizaciones de fase.\n\n"
                "¿Confirmas?",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Código incorrecto.")
        return

    # PASO 2: EMAIL (SOLO DESPUÉS DE ACEPTAR)
    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0
            node['caste'] = "LARVA"
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🟢 ACCEDER AL NÚCLEO", callback_data="go_dash")]]
            await update.message.reply_text(
                "🎉 **NODO ACTIVADO**\n\n"
                "Rol Inicial: **LARVA** 🐛\n"
                "Estado: **VIVO**\n\n"
                "Lo que hagas hoy importa más que lo que hagas mañana.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Email inválido.")
        return

    try:
        node = await db.db.get_node(uid)
        if node and node.get("email"): await show_dashboard(update, context)
    except: pass

# ==============================================================================
# DASHBOARD (NÚCLEO VIVO - DÍA 0)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.callback_query:
            msg = update.callback_query.message.edit_text
            uid = update.callback_query.from_user.id
        else:
            msg = update.message.reply_text
            uid = update.effective_user.id

        node = await db.db.get_node(uid)
        if not node: await msg("Conectando..."); return
        if not node.get("email"): context.user_data['step']='email_wait'; await msg("Falta ID (Email)"); return

        node = BioEngine.calculate_state(node)
        stats = await db.db.get_global_stats()
        await db.db.save_node(uid, node)
        
        rol = node['caste']
        info_rol = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])
        icono = info_rol["icono"]
        
        progreso = calculate_evolution_progress(node['honey'], len(node.get("referrals", [])))
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        # MENSAJE DÍA 0
        txt = (
            f"🏰 **THE ONE HIVE** | {icono} {rol}\n"
            f"────────────────\n"
            f"Estado de la Colmena: **ACTIVA**\n\n"
            f"⚡ **Energía del Enjambre:** {polen}/{max_p}\n"
            f"`{bar}`\n\n"
            f"🍯 **Néctar Acumulado:** `{node['honey']:,.2f}`\n"
            f"📈 _{progreso}_\n\n"
            f"• Reglas en ajuste\n"
            f"• Accesos tempranos abiertos\n"
            f"• Recompensas en calibración\n"
            f"────────────────"
        )
        
        # GRID OPERATIVO (DÍA 0)
        kb = [
            [InlineKeyboardButton("🧬 ACCIÓN RÁPIDA (TAP)", callback_data="forage")],
            # ZONA DE TRABAJO
            [InlineKeyboardButton("🟢 PANALES (TAREAS)", callback_data="tasks"), InlineKeyboardButton("🧬 EVOLUCIÓN", callback_data="rank_info")],
            # ZONA SOCIAL
            [InlineKeyboardButton("🐝 MI COLMENA", callback_data="squad")],
            # ZONA ECONÓMICA
            [InlineKeyboardButton("🚀 ACCESO PREMIUM", callback_data="shop"), InlineKeyboardButton("👥 EXPANDIR", callback_data="team")],
            [InlineKeyboardButton("📡 RED GLOBAL", callback_data="global_stats")]
        ]
        
        try: await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except: await msg(txt.replace("*", "").replace("_", ""), reply_markup=InlineKeyboardMarkup(kb))
            
    except Exception as e:
        logger.error(f"Dashboard Error: {e}")

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Energía agotada. Usa el Acelerador.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        
        trace = node.get("entropy_trace", [])
        trace.append(time.time())
        if len(trace)>15: trace.pop(0)
        node["entropy_trace"] = trace
        mult, txt = SecurityEngine.analyze_entropy(trace)
        
        rol = node.get("caste", "LARVA")
        bonus = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["bonus_tap"]
        
        syn = 1.0
        if node.get("enjambre_id"): 
            c = await db.db.get_cell(node["enjambre_id"])
            members = len(c.get("members", []))
            if members >= 3: syn = 1.4 # Incentivo inicial bajo
            
        yield_amt = CONST['RECOMPENSA_BASE'] * mult * bonus * syn
        node['honey'] += yield_amt
        
        await db.db.add_global_honey(yield_amt)
        await db.db.save_node(uid, node)
        
        # ACTIVIDAD RECIENTE (Simulación de vida)
        min_rand = random.randint(1, 9)
        msg_vida = f"• Un miembro completó una acción hace {min_rand} min"
        
        await q.answer(f"+{yield_amt:.2f} Néctar\n{msg_vida}", show_alert=False)
        if random.random() < 0.15: await show_dashboard(update, context)
        
    except Exception: pass

# ==============================================================================
# SUB-MENÚS (ECONOMÍA DÍA 0)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 ACCIÓN RÁPIDA", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 ACCIÓN DE EXPLORACIÓN", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 ACCIÓN PATROCINADA", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "🏗️ **PANALES DE ACTIVIDAD**\n\n"
        "Elige tu sector. Tu Rol determina tu acceso.\n\n"
        "🟢 **Acción Rápida:** Flujo constante.\n"
        "🟡 **Exploración:** Ingresos estables.\n"
        "🔴 **Patrocinada:** Oportunidades VIP.\n\n"
        "⚠️ *La eficiencia depende de la Colmena.*"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    rol = node.get("caste", "LARVA")
    nivel = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["nivel"]
    
    if key == "TIER_2" and nivel < 1: # Obrero
        await q.answer("🔒 BLOQUEADO. Requiere Rol: OBRERO.", show_alert=True); return
    if key == "TIER_3" and nivel < 3: # Guardian
        await q.answer("🔒 BLOQUEADO. Requiere Rol: GUARDIÁN.", show_alert=True); return

    links = FORRAJEO_DB.get(key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    nombre_panal = "PANAL VERDE" if key == "TIER_1" else ("PANAL DORADO" if key == "TIER_2" else "PANAL ROJO")
    
    await q.message.edit_text(
        f"📍 **{nombre_panal}**\n\n"
        f"Realiza las acciones para generar valor.", 
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🐝 **CÉLULA ACTIVA: {cell['name']}**\n👥 Nodos: {len(cell['members'])}\n🔥 Sinergia: x{cell['synergy']:.2f}"
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = (
            "⚠️ **EFICIENCIA BAJA**\n\n"
            "Un nodo aislado produce x1.0\n"
            "Una Célula de 3 produce x1.4\n\n"
            "**No puedes crecer solo.**"
        )
        kb = [[InlineKeyboardButton("➕ FORMAR CÉLULA (100 HIVE)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Célula Iniciada"); await squad_menu(update, context)
    else: await q.answer("❌ Néctar Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # MONETIZACIÓN HÍBRIDA
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA (200 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("🚀 ACELERADOR ($9.99)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "💎 **ECONOMÍA**\n\n"
        "• El Néctar es escaso.\n"
        "• El Acelerador optimiza tu tiempo.\n\n"
        "🔻 **GASTAR NÉCTAR:**"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Prioridad Adquirida"); await show_dashboard(update, context)
    else: await q.answer("❌ Néctar Insuficiente", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(
        f"🚀 **ACCESO PREMIUM**\n\n"
        "Ventajas:\n"
        "• Menos espera\n"
        "• Más acciones visibles\n"
        "• Prioridad en futuras funciones\n\n"
        f"Envía $9.99 USDT (TRC20) a:\n`{CRYPTO_WALLET_USDT}`", 
        parse_mode=ParseMode.MARKDOWN
    )

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    refs = len(node.get('referrals', []))
    txt = (
        f"👥 **EXPANSIÓN**\n\n"
        "Entré a una fase temprana de The One Hive.\n"
        "Todavía están ajustando las reglas.\n\n"
        f"Nodos Asimilados: **{refs}**\n\n"
        f"🔗 Enlace: `{link}`"
    )
    kb = [[InlineKeyboardButton("📤 EXPANDIR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🧬 **CICLO EVOLUTIVO**\n\n"
        "Tu rol en la colmena cambió.\n"
        "Ahora tus acciones pesan más.\n\n"
        "🐛 **LARVA:** Inicio.\n"
        "🐝 **OBRERO:** 1k HIVE.\n"
        "🔭 **EXPLORADOR:** 5k HIVE.\n"
        "🛡️ **GUARDIÁN:** 20k HIVE.\n"
        "👑 **REINA:** 100k HIVE."
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def global_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await db.db.get_global_stats()
    await update.callback_query.answer(
        f"🌍 ESTADO GLOBAL\n\n"
        f"📡 Nodos: {stats['nodes']:,}\n"
        f"💰 Tesoro: {stats['honey']:,.0f} HIVE\n"
        f"⚠️ Fase Temprana", 
        show_alert=True
    )

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await q.message.edit_text("✅ Confirmado. Escribe tu **EMAIL** para recibir instrucciones:", parse_mode=ParseMode.MARKDOWN)
        return

    actions = {
        "go_dash": show_dashboard, 
        "forage": forage_action, 
        "tasks": tasks_menu, 
        "rank_info": rank_info_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "TIER_1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "TIER_2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "TIER_3", c),
        "squad": squad_menu, 
        "mk_cell": create_squad_logic,
        "shop": shop_menu, 
        "buy_energy": buy_energy,
        "buy_premium": buy_premium, 
        "team": team_menu,
        "global_stats": global_stats_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 NODO REINICIADO")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("The One Hive Protocol V6.0")
async def broadcast_cmd(u, c): pass
