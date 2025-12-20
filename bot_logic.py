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
# CONFIGURACIÓN: THE ONE HIVE (MASTER V5.0)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# IDENTIDAD VISUAL MAESTRA
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ECONOMÍA ORGÁNICA (CONSTANTES) ---
CONST = {
    "COSTO_POLEN": 10,        # Gasto Energético
    "RECOMPENSA_BASE": 0.50,  # Emisión Escasa
    "DECAY_OXIGENO": 5.0,     # Presión Evolutiva (Inactividad)
    "COSTO_ENJAMBRE": 100,    # Barrera de Entrada Social
    "COSTO_RECARGA": 200,     # Costo de Prioridad
    "BONO_REFERIDO": 500,     # Valor de Influencia
    "PRECIO_ACELERADOR": 10   # USD (Monetización Premium)
}

# --- JERARQUÍA BIOLÓGICA (ROLES) ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 300,  "bonus_tap": 0.8, "icono": "🐛"},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 500,  "bonus_tap": 1.0, "icono": "🔨"},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 1000, "bonus_tap": 1.2, "icono": "🔭"},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 2000, "bonus_tap": 1.5, "icono": "🛡️"},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑"}
}

# --- ARQUITECTURA DE PANALES (ECONOMÍA REAL) ---
FORRAJEO_DB = {
    "TIER_1": [ # PANAL VERDE: Flujo Rápido
        {"name": "📺 Timebucks (Video)", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC (Click)", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "💸 FreeCash (Rápido)", "url": "https://freecash.com/r/XYN98"},
        {"name": "🎮 GameHag", "url": "https://gamehag.com/r/NWUD9QNR"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"},
        {"name": "💧 FaucetPay", "url": "https://faucetpay.io/?r=123456"},
        {"name": "⚡ Cointiply", "url": "http://cointiply.com/r/Pandora"},
        {"name": "🖱️ BTCClicks", "url": "https://btcclicks.com/?r=Pandora"},
        {"name": "🔥 FireFaucet", "url": "https://firefaucet.win/ref/Pandora"}
    ],
    "TIER_2": [ # PANAL DORADO: Ingreso Pasivo (Requiere Explorador)
        {"name": "🐝 Honeygain (Pasivo)", "url": "https://join.honeygain.com/ALEJOE9F32"},
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
    "TIER_3": [ # PANAL ROJO: High Value (Requiere Guardián)
        {"name": "🔥 ByBit ($20 Bono)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🏦 Nexo (Yield)", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"},
        {"name": "☁️ AirTM", "url": "https://app.airtm.com/ivt/jos3vkujiyj"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"},
        {"name": "🆗 OKX", "url": "https://www.okx.com/join/PANDORA"},
        {"name": "📈 KuCoin", "url": "https://www.kucoin.com/r/rf/PANDORA"},
        {"name": "🐂 Bitget", "url": "https://partner.bitget.com/bg/PANDORA"},
        {"name": "🔐 Ledger (Cold)", "url": "https://shop.ledger.com/?r=pandora"},
        {"name": "🛡️ Trezor", "url": "https://trezor.io/?offer_id=12&aff_id=pandora"}
    ]
}

# ==============================================================================
# FUNCIONES VISUALES (INTERFAZ MAESTRA)
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_evolution_progress(hive: float, referrals: int) -> str:
    """Calcula la distancia a la siguiente evolución biológica."""
    poder = hive + (referrals * CONST["BONO_REFERIDO"])
    niveles = list(RANGOS_CONFIG.values())
    siguiente = None
    
    for nivel in niveles:
        if nivel["meta_hive"] > poder:
            siguiente = nivel
            break
            
    if siguiente:
        falta = siguiente["meta_hive"] - poder
        return f"Evolución: Faltan {falta:,.0f} pts"
    return "ORGANISMO PERFECCIONADO (MAX)"

# ==============================================================================
# MOTOR BIOLÓGICO (CORE ENGINE)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0)
        refs = len(node.get("referrals", []))
        
        # PROGRESO = MERITO + INFLUENCIA
        poder = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango_actual = "LARVA" # Default
        stats = RANGOS_CONFIG["LARVA"]
        
        for nombre, data in RANGOS_CONFIG.items():
            if poder >= data["meta_hive"]:
                rango_actual = nombre
                stats = data
        
        node["caste"] = rango_actual 
        node["max_polen"] = stats["max_energia"]
        
        # Regeneración Energética
        if elapsed > 0:
            regen = elapsed * 0.8 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        # Presión Evolutiva (Decay de Oxígeno)
        last_pulse = node.get("last_pulse", now)
        if (now - last_pulse) > 3600:
            decay = ((now - last_pulse) / 3600) * CONST["DECAY_OXIGENO"]
            node["oxygen"] = max(5.0, node.get("oxygen", 100.0) - decay)
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    @staticmethod
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        # Detecta patrones humanos vs mecánicos
        if len(timestamps) < 5: return 1.0, ""
        deltas = [timestamps[i]-timestamps[i-1] for i in range(1,len(timestamps))]
        try:
            cv = statistics.stdev(deltas) / statistics.mean(deltas)
        except: return 1.0, ""
        
        if cv < 0.05: return 0.1, "🚫 SINTÉTICO DETECTADO"
        if 0.05 <= cv <= 0.35: return 1.3, "🔥 SINCRONIZADO"
        return 1.0, "✅"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# FLUJO DE ENTRADA (ENGANCHE PSICOLÓGICO)
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
        
        # COPY MAESTRO: CURIOSIDAD + PERTENENCIA
        txt = (
            "🐝 **THE ONE HIVE — INICIO DEL SISTEMA**\n"
            "────────────────────\n"
            "Bienvenido a la infraestructura.\n\n"
            "Cada acción fortalece la colmena.\n"
            "No todos progresan igual.\n"
            "El sistema mide constancia, ritmo y decisión.\n\n"
            "Tu evolución comienza ahora.\n"
            f"🔐 **Validación:** `{captcha}`"
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
                "📜 **PROTOCOLO DE LA COLMENA**\n\n"
                "Al unirte, aceptas contribuir activamente.\n"
                "La inactividad reduce tu estatus.\n\n"
                "¿Aceptas las reglas del organismo?",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Verificación fallida.")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0 # Incentivo inicial
            node['caste'] = "LARVA" # Comienza desde abajo
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🚀 ENTRAR AL NÚCLEO", callback_data="go_dash")]]
            await update.message.reply_text(
                "🎉 **NODO ACTIVADO**\n\n"
                "Rol Inicial: **LARVA** 🐛\n"
                "Estado: **VIVO**\n\n"
                "El sistema te está observando.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Formato inválido.")
        return

    try:
        node = await db.db.get_node(uid)
        if node and node.get("email"): await show_dashboard(update, context)
    except: pass

# ==============================================================================
# DASHBOARD (PANAL CENTRAL)
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
        
        rango = node['caste']
        info_rango = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])
        icono = info_rango["icono"]
        refs = len(node.get("referrals", []))
        progreso_txt = calculate_evolution_progress(node['honey'], refs)
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        # UI MAESTRA: DATOS CLAROS
        txt = (
            f"🏰 **THE ONE HIVE** | {icono} **{rango}**\n"
            f"────────────────\n"
            f"👤 **{node['username'] or 'Nodo Anónimo'}**\n"
            f"⚡ **Energía:** {polen}/{max_p}\n"
            f"`{bar}`\n\n"
            f"🍯 **Néctar:** `{node['honey']:,.2f} $HIVE`\n"
            f"📈 _{progreso_txt}_\n\n"
            f"🌍 **Tesoro Global:** `{stats['honey']:,.0f}`\n"
            f"────────────────"
        )
        
        # GRID OPERATIVO (DISTRIBUCIÓN FINAL)
        kb = [
            [InlineKeyboardButton("🧬 SINTETIZAR (TAP)", callback_data="forage")],
            # FILA 1: ACTIVIDAD
            [InlineKeyboardButton("🟢 PANALES", callback_data="tasks"), InlineKeyboardButton("🧬 EVOLUCIÓN", callback_data="rank_info")],
            # FILA 2: ESTRUCTURA
            [InlineKeyboardButton("🐝 MI COLMENA", callback_data="squad")],
            # FILA 3: ECONOMÍA
            [InlineKeyboardButton("🚀 ACELERADOR", callback_data="shop"), InlineKeyboardButton("👥 EXPANSIÓN", callback_data="team")],
            # FILA 4: DATOS
            [InlineKeyboardButton("📡 ESTADO DEL SISTEMA", callback_data="global_stats")]
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
            await q.answer("⚡ Energía Agotada. Usa el Acelerador para continuar.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        
        trace = node.get("entropy_trace", [])
        trace.append(time.time())
        if len(trace)>15: trace.pop(0)
        node["entropy_trace"] = trace
        mult, txt_sec = SecurityEngine.analyze_entropy(trace)
        
        rango = node.get("caste", "LARVA")
        bonus = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])["bonus_tap"]
        
        # Sinergia de Colmena (Viralidad Estructural)
        syn = 1.0
        if node.get("enjambre_id"): 
            c = await db.db.get_cell(node["enjambre_id"])
            members = len(c.get("members", []))
            if members >= 10: syn = 3.5
            elif members >= 5: syn = 2.0
            elif members >= 3: syn = 1.4
            
        yield_amt = CONST['RECOMPENSA_BASE'] * mult * bonus * syn
        node['honey'] += yield_amt
        
        await db.db.add_global_honey(yield_amt)
        await db.db.save_node(uid, node)
        
        await q.answer(f"+{yield_amt:.2f} Néctar ({txt_sec})")
        if random.random() < 0.15: await show_dashboard(update, context)
        
    except Exception: pass

# ==============================================================================
# SUB-MENÚS (ECONOMÍA DE PANAL)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 PANAL VERDE (Abierto)", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 PANAL DORADO (Explorador 🔒)", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 PANAL ROJO (Guardián 🔒)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "🏗️ **CENTRO DE RECOLECCIÓN**\n\n"
        "Elige tu sector de trabajo:\n\n"
        "🟢 **Panal Verde:** Tareas rápidas, flujo constante.\n"
        "🟡 **Panal Dorado:** Ingresos estables y pasivos.\n"
        "🔴 **Panal Rojo:** Alto valor, oportunidades VIP.\n\n"
        "⚠️ *Tu Rol determina tu acceso.*"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    rango = node.get("caste", "LARVA")
    nivel = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])["nivel"]
    
    # GATING POR ROL
    if key == "TIER_2" and nivel < 2:
        await q.answer("🔒 BLOQUEADO. Requiere Rol: EXPLORADOR.", show_alert=True); return
    if key == "TIER_3" and nivel < 3:
        await q.answer("🔒 BLOQUEADO. Requiere Rol: GUARDIÁN.", show_alert=True); return

    links = FORRAJEO_DB.get(key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    nombre_panal = "PANAL VERDE" if key == "TIER_1" else ("PANAL DORADO" if key == "TIER_2" else "PANAL ROJO")
    
    await q.message.edit_text(
        f"📍 **{nombre_panal}**\n\n"
        f"Realiza las acciones para generar Néctar y Valor Real.", 
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
        # VIRALIDAD ESTRUCTURAL
        txt = (
            "⚠️ **EFICIENCIA BAJA**\n\n"
            "Un nodo aislado produce x1.0\n"
            "Una Célula de 3 produce x1.4\n"
            "Una Colmena de 10 produce x3.5\n\n"
            "**No puedes crecer solo.**"
        )
        kb = [[InlineKeyboardButton("➕ FORMAR CÉLULA (100 HIVE)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Célula-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Célula Iniciada"); await squad_menu(update, context)
    else: await q.answer("❌ Néctar Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # MONETIZACIÓN HÍBRIDA
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA (200 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("🚀 ACELERADOR ($10 USDT)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "💎 **ECONOMÍA DEL TOKEN**\n\n"
        "El Token no es solo dinero, es **Infraestructura**.\n"
        "Su valor depende del trabajo real del enjambre.\n\n"
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
    await update.callback_query.message.edit_text(f"🚀 **ACELERADOR DEL PANAL**\n\nReduce tiempos de espera y optimiza el flujo.\n\nEnvía $10 USDT (TRC20) a:\n`{CRYPTO_WALLET_USDT}`", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    refs = len(node.get('referrals', []))
    txt = f"👥 **EXPANSIÓN**\n\nInvitados: **{refs}**\nTu influencia crece con cada nodo que conectas.\n\n🔗 Enlace: `{link}`"
    kb = [[InlineKeyboardButton("📤 EXPANDIR COLMENA", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🧬 **EVOLUCIÓN BIOLÓGICA**\n\n"
        "🐛 **LARVA:** Recién llegado. Capacidad mínima.\n"
        "🔨 **OBRERO:** 1k HIVE. Productor estándar.\n"
        "🔭 **EXPLORADOR:** 5k HIVE. Acceso Panal Dorado.\n"
        "🛡️ **GUARDIÁN:** 20k HIVE. Acceso Panal Rojo.\n"
        "👑 **REINA:** 100k HIVE. Control total.\n\n"
        "💡 *Se evoluciona trabajando y cooperando.*"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def global_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await db.db.get_global_stats()
    clima = "☀️ Óptimo"
    await update.callback_query.answer(
        f"🌍 RED GLOBAL\n\n"
        f"📡 Nodos: {stats['nodes']:,}\n"
        f"💰 Tesoro: {stats['honey']:,.0f} HIVE\n"
        f"🌩️ Clima: {clima}", 
        show_alert=True
    )

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await q.message.edit_text("✅ Confirmado. Ingresa tu **EMAIL**:", parse_mode=ParseMode.MARKDOWN)
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
async def help_cmd(u, c): await u.message.reply_text("The One Hive V5.0 Master")
async def broadcast_cmd(u, c): pass
