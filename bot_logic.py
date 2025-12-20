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
# CONFIGURACIÓN: THE ONE HIVE (V4.0 GENESIS)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# Assets Visuales (Identidad The One Hive)
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA ORGÁNICA ---
CONST = {
    "COSTO_POLEN": 10,        # Costo Energía por Síntesis
    "RECOMPENSA_BASE": 0.50,  # Néctar base por Síntesis
    "DECAY_OXIGENO": 5.0,     # Castigo por inactividad (Bio-ritmo)
    "COSTO_ENJAMBRE": 100,    # Costo crear Colmena (Influencia)
    "COSTO_RECARGA": 200,     # Prioridad de Energía
    "BONO_REFERIDO": 500      # Valor Histórico para Evolución
}

# --- EVOLUCIÓN DE ROLES (JERARQUÍA VIVA) ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 1, "meta_nectar": 0,      "max_energia": 500,  "bonus": 1.0, "icono": "🐛"},
    "OBRERO":     {"nivel": 2, "meta_nectar": 5000,   "max_energia": 1000, "bonus": 1.2, "icono": "🐝"},
    "EXPLORADOR": {"nivel": 3, "meta_nectar": 20000,  "max_energia": 1500, "bonus": 1.5, "icono": "🔭"},
    "GUARDIAN":   {"nivel": 4, "meta_nectar": 50000,  "max_energia": 2500, "bonus": 2.0, "icono": "🛡️"},
    "REINA":      {"nivel": 5, "meta_nectar": 200000, "max_energia": 5000, "bonus": 3.5, "icono": "👑"}
}

# --- ARQUITECTURA DE PANALES (ECONOMÍA REAL) ---
FORRAJEO_DB = {
    "PANAL_VERDE": [ # Entrada Global, Baja Fricción
        {"name": "📺 Timebucks", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "💸 FreeCash", "url": "https://freecash.com/r/XYN98"},
        {"name": "🎮 GameHag", "url": "https://gamehag.com/r/NWUD9QNR"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"},
        {"name": "💧 FaucetPay", "url": "https://faucetpay.io/?r=123456"},
        {"name": "⚡ Cointiply", "url": "http://cointiply.com/r/Pandora"},
        {"name": "🖱️ BTCClicks", "url": "https://btcclicks.com/?r=Pandora"},
        {"name": "🔥 FireFaucet", "url": "https://firefaucet.win/ref/Pandora"}
    ],
    "PANAL_DORADO": [ # Ingresos Estables (Requiere Obrero)
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810"},
        {"name": "🌱 SproutGigs", "url": "https://sproutgigs.com/?a=83fb1bf9"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"},
        {"name": "🔋 Traffmonetizer", "url": "https://traffmonetizer.com/?aff=123"},
        {"name": "📱 Repocket", "url": "https://link.repocket.co/pandora"},
        {"name": "🌐 Peer2Profit", "url": "https://peer2profit.com/r/pandora"},
        {"name": "💻 LoadTeam", "url": "https://loadteam.com/signup?referral=pandora"},
        {"name": "🤖 2Captcha", "url": "https://2captcha.com?from=1234"}
    ],
    "PANAL_ROJO": [ # Premium / Partners (Requiere Guardián)
        {"name": "🔥 ByBit ($20)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🏦 Nexo", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"},
        {"name": "☁️ AirTM", "url": "https://app.airtm.com/ivt/jos3vkujiyj"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"},
        {"name": "🆗 OKX", "url": "https://www.okx.com/join/PANDORA"},
        {"name": "📈 KuCoin", "url": "https://www.kucoin.com/r/rf/PANDORA"},
        {"name": "🐂 Bitget", "url": "https://partner.bitget.com/bg/PANDORA"},
        {"name": "🔐 Ledger", "url": "https://shop.ledger.com/?r=pandora"},
        {"name": "🛡️ Trezor", "url": "https://trezor.io/?offer_id=12&aff_id=pandora"}
    ]
}

# ==============================================================================
# FUNCIONES VISUALES (INTERFAZ ORGÁNICA)
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_evolution_progress(nectar: float, referrals: int) -> str:
    """Calcula la distancia a la siguiente metamorfosis."""
    poder_total = nectar + (referrals * CONST["BONO_REFERIDO"])
    roles = list(RANGOS_CONFIG.values())
    siguiente = None
    
    for rol in roles:
        if rol["meta_nectar"] > poder_total:
            siguiente = rol
            break
            
    if siguiente:
        falta = siguiente["meta_nectar"] - poder_total
        return f"Metamorfosis en: {falta:,.0f} Néctar"
    
    return "🧬 EVOLUCIÓN COMPLETA"

# ==============================================================================
# MOTOR BIOLÓGICO (LÓGICA DEL ORGANISMO)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0) # Néctar
        refs = len(node.get("referrals", []))
        
        # Evolución basada en Valor Histórico (Balance + Influencia)
        poder_evolutivo = balance + (refs * CONST["BONO_REFERIDO"])
        
        rol_actual = "LARVA"
        stats_actuales = RANGOS_CONFIG["LARVA"]
        
        for nombre, data in RANGOS_CONFIG.items():
            if poder_evolutivo >= data["meta_nectar"]:
                rol_actual = nombre
                stats_actuales = data
        
        node["caste"] = rol_actual 
        node["max_polen"] = stats_actuales["max_energia"]
        
        # Regeneración de Energía
        if elapsed > 0:
            regen = elapsed * 0.8 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        # Decaimiento de Oxígeno (Castigo por inactividad)
        last_pulse = node.get("last_pulse", now)
        horas_inactivo = (now - last_pulse) / 3600
        if horas_inactivo > 1:
            decay = horas_inactivo * CONST["DECAY_OXIGENO"]
            node["oxygen"] = max(0.0, node.get("oxygen", 100.0) - decay)
        else:
            # Recupera oxígeno al interactuar
            node["oxygen"] = min(100.0, node.get("oxygen", 100.0) + 10.0)
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    @staticmethod
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        # Bio-ritmo: Detecta patrones no humanos
        if len(timestamps) < 5: return 1.0, ""
        deltas = [timestamps[i]-timestamps[i-1] for i in range(1,len(timestamps))]
        try:
            cv = statistics.stdev(deltas) / statistics.mean(deltas)
        except: return 1.0, ""
        
        if cv < 0.05: return 0.1, "🚫 BOT"
        if 0.05 <= cv <= 0.35: return 1.3, "⚡ SINCRONIZADO"
        return 1.0, "✅"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# ACTIVACIÓN (ONBOARDING VIRAL)
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

        captcha = SecurityEngine.generate_captcha()
        context.user_data['captcha'] = captcha
        context.user_data['step'] = 'captcha_wait'
        
        # COPYWRITING: ACTIVACIÓN GLOBAL
        txt = (
            "🐝 **THE ONE HIVE – ACTIVACIÓN GLOBAL**\n"
            "────────────────────\n"
            "Has sido invitado a una Colmena económica viva.\n\n"
            "Los primeros miembros obtienen ventajas irreversibles en la futura economía del Enjambre.\n\n"
            "⚠️ **Cupos limitados por Panal.**\n"
            "Confirma tu humanidad para ingresar.\n\n"
            f"🔒 Código de Acceso: `{captcha}`"
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

    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ CONFIRMAR INGRESO", callback_data="accept_terms")]]
            await update.message.reply_text(
                "🧬 **SINTONIZANDO BIO-RITMO**\n\n"
                "Para ser parte del organismo, aceptas:\n"
                "• Cooperar con tu Colmena.\n"
                "• Mantener actividad constante.\n"
                "• Recibir inteligencia del Enjambre.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Acceso Denegado.")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0
            node['caste'] = "LARVA" # Rol Inicial
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🧬 ENTRAR AL NÚCLEO", callback_data="go_dash")]]
            await update.message.reply_text(
                "🎉 **NODO ACTIVADO**\n\n"
                "Rol Asignado: **LARVA** 🐛\n"
                "Néctar Inicial: **+200**\n\n"
                "Comienza tu evolución.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Protocolo inválido (Email).")
        return

    try:
        node = await db.db.get_node(uid)
        if node and node.get("email"): await show_dashboard(update, context)
    except: pass

# ==============================================================================
# DASHBOARD (NÚCLEO DEL ORGANISMO)
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
        if not node: await msg("Sincronizando..."); return
        if not node.get("email"): context.user_data['step']='email_wait'; await msg("Falta Enlace (Email)"); return

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
        oxygen = int(node.get('oxygen', 100))
        
        txt = (
            f"🧬 **THE ONE HIVE** | NÚCLEO\n"
            f"────────────────\n"
            f"🆔 **{node['username'] or 'Nodo'}** | {icono} {rol}\n"
            f"🍯 **Néctar:** `{node['honey']:,.2f}`\n"
            f"🫁 **Oxígeno:** {oxygen}%\n"
            f"⚡ **Energía:** {polen}/{max_p}\n"
            f"`{bar}`\n\n"
            f"🧬 _{progreso}_\n"
            f"🌍 **Enjambre:** `{stats['nodes']:,}` nodos\n"
            f"────────────────"
        )
        
        # LAYOUT LÓGICO: SINTETIZAR | PANALES | COLMENA
        kb = [
            [InlineKeyboardButton("⚡ SINTETIZAR (TAP)", callback_data="forage")],
            # FILA 1: ACTIVIDAD
            [InlineKeyboardButton("🟢 PANALES", callback_data="tasks"), InlineKeyboardButton("🧬 EVOLUCIÓN", callback_data="rank_info")],
            # FILA 2: COMUNIDAD
            [InlineKeyboardButton("🐝 MI COLMENA", callback_data="squad")],
            # FILA 3: ECONOMÍA
            [InlineKeyboardButton("💎 MERCADO", callback_data="shop"), InlineKeyboardButton("👥 EXPANDIR", callback_data="team")],
            [InlineKeyboardButton("🌍 GLOBAL", callback_data="global_status")]
        ]
        
        try:
            await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except:
            await msg(txt.replace("*", "").replace("_", ""), reply_markup=InlineKeyboardMarkup(kb))
            
    except Exception as e:
        logger.error(f"Error Dashboard: {e}")

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # NARRATIVA DE EVOLUCIÓN
    txt = (
        "🧬 **CICLO EVOLUTIVO**\n\n"
        "🐛 **LARVA:** El inicio. Aprende.\n"
        "🐝 **OBRERO:** Produce. (5k Néctar)\n"
        "🔭 **EXPLORADOR:** Busca. (20k Néctar)\n"
        "🛡️ **GUARDIÁN:** Protege. (50k Néctar)\n"
        "👑 **REINA:** Gobierna. (200k Néctar)\n\n"
        "⚠️ *La evolución depende de Cooperación + Producción.*"
    )
    kb = [[InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dash")]]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def global_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    stats = await db.db.get_global_stats()
    await q.answer(
        f"🌍 CONCIENCIA COLECTIVA\n\n"
        f"👥 Nodos Activos: {stats['nodes']:,}\n"
        f"🍯 Reserva de Néctar: {stats['honey']:,.0f}\n"
        f"🟢 FASE 1: GÉNESIS", 
        show_alert=True
    )

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Energía Agotada. El organismo necesita reposo o Recarga.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        
        trace = node.get("entropy_trace", [])
        trace.append(time.time())
        if len(trace)>15: trace.pop(0)
        node["entropy_trace"] = trace
        mult, txt = SecurityEngine.analyze_entropy(trace)
        
        rol = node.get("caste", "LARVA")
        bonus = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["bonus"]
        
        # SINERGIA DE COLMENA
        syn = 1.0
        if node.get("enjambre_id"): 
            c = await db.db.get_cell(node["enjambre_id"])
            members = len(c.get("members", []))
            # Lógica de Multiplicador Viral
            if members >= 10: syn = 3.5
            elif members >= 5: syn = 2.0
            elif members >= 3: syn = 1.4
        
        # Fórmula: Base * AntiBot * Rango * Colmena * Oxígeno
        yield_amt = CONST['RECOMPENSA_BASE'] * mult * bonus * syn * (node.get('oxygen', 100)/100)
        node['honey'] += yield_amt
        
        await db.db.add_global_honey(yield_amt)
        await db.db.save_node(uid, node)
        
        await q.answer(f"+{yield_amt:.2f} Néctar ({txt})")
        if random.random() < 0.2: await show_dashboard(update, context)
        
    except Exception as e:
        logger.error(f"Error Forage: {e}")

# ==============================================================================
# SISTEMA DE PANALES (TAREAS / ECONOMÍA)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 PANAL VERDE (Entrada Global)", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 PANAL DORADO (Obrero 🔒)", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 PANAL ROJO (Guardián 🔒)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dash")]
    ]
    txt = (
        "🐝 **ARQUITECTURA DE PANALES**\n\n"
        "Cada Panal ofrece recursos distintos:\n"
        "🟢 **Verde:** Tareas rápidas, baja fricción.\n"
        "🟡 **Dorado:** Ingresos pasivos estables.\n"
        "🔴 **Rojo:** Economía externa, alto valor.\n\n"
        "⚠️ *Tu Rol biológico determina tu acceso.*"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    rol = node.get("caste", "LARVA")
    nivel = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["nivel"]
    
    # LOCK SYSTEM
    if key == "PANAL_DORADO" and nivel < 2: # Obrero
        await q.answer("🔒 BLOQUEADO: Requiere Evolución a OBRERO", show_alert=True); return
    if key == "PANAL_ROJO" and nivel < 4: # Guardian
        await q.answer("🔒 BLOQUEADO: Requiere Evolución a GUARDIÁN", show_alert=True); return

    # Mapeo de DB antigua a nombres nuevos
    db_key = "TIER_1" if key == "PANAL_VERDE" else ("TIER_2" if key == "PANAL_DORADO" else "TIER_3")
    links = FORRAJEO_DB.get(db_key, [])
    
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    desc = "Producción Rápida" if key == "PANAL_VERDE" else ("Ingreso Pasivo" if key == "PANAL_DORADO" else "Alto Valor USD")
    
    await q.message.edit_text(
        f"📍 **{key.replace('_', ' ')}**\n"
        f"📊 Tipo: {desc}\n"
        f"⏳ Ciclo: Continuo", 
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    # NARRATIVA DE VIRALIDAD OBLIGATORIA
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        count = len(cell['members'])
        mult_txt = "x1.0"
        if count >= 10: mult_txt = "x3.5 🔥"
        elif count >= 5: mult_txt = "x2.0 ⚡"
        elif count >= 3: mult_txt = "x1.4 ✨"
        
        txt = f"🐝 **COLMENA ACTIVA: {cell['name']}**\n👥 Nodos: {count}\n🔥 Multiplicador: {mult_txt}"
        kb = [[InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dash")]]
    else:
        txt = (
            "⚠️ **NODO AISLADO (Ineficiente)**\n\n"
            "Sin Colmena, tu progreso es lento (x1.0).\n\n"
            "**Multiplicadores de Colmena:**\n"
            "• 3 Nodos: x1.4\n"
            "• 5 Nodos: x2.0\n"
            "• 10+ Nodos: x3.5\n\n"
            "Forma una Colmena para sobrevivir."
        )
        kb = [[InlineKeyboardButton("➕ FORMAR COLMENA (100 Néctar)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Colmena Establecida"); await squad_menu(update, context)
    else: await q.answer("❌ Néctar Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⚡ RECARGA PRIORITARIA (200 Néctar)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 ESTATUS REINA ($10 USDT)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dash")]
    ]
    txt = (
        "💎 **ECONOMÍA DEL TOKEN**\n\n"
        "El Néctar ($HIVE) no se imprime, se **Sintetiza** con trabajo.\n\n"
        "1. **Supply:** Controlado por actividad humana.\n"
        "2. **Halving:** La dificultad sube con el tiempo.\n"
        "3. **Utilidad:** Acceso, Prioridad y Gobernanza.\n\n"
        "🔻 **USOS INMEDIATOS:**"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Energía Restaurada al 100%"); await show_dashboard(update, context)
    else: await q.answer("❌ Néctar Insuficiente", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(f"💎 **INVERSIÓN**\n\nEnvía $10 USDT a:\n`{CRYPTO_WALLET_USDT}`", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    refs = len(node.get('referrals', []))
    txt = f"👥 **EXPANSIÓN DEL ENJAMBRE**\n\nMás Influencia = Evolución más rápida\nInvitados: **{refs}**\n\n🔗 Enlace de Activación:\n`{link}`"
    kb = [[InlineKeyboardButton("📤 INVITAR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 NÚCLEO", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await q.message.edit_text("✅ Confirmado. Ingresa tu **EMAIL** para vincular:", parse_mode=ParseMode.MARKDOWN)
        return

    actions = {
        "go_dash": show_dashboard, 
        "forage": forage_action, 
        "tasks": tasks_menu, 
        "rank_info": rank_info_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "PANAL_VERDE", c),
        "v_t2": lambda u,c: view_tier_generic(u, "PANAL_DORADO", c),
        "v_t3": lambda u,c: view_tier_generic(u, "PANAL_ROJO", c),
        "squad": squad_menu, 
        "mk_cell": create_squad_logic,
        "shop": shop_menu, 
        "buy_energy": buy_energy,
        "buy_premium": buy_premium, 
        "team": team_menu,
        "global_status": global_status_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 NODO REINICIADO")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("The One Hive Protocol V4.0")
async def broadcast_cmd(u, c): pass
