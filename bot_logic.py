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
# CONFIGURACIÓN PANDORA V314 (LAUNCH OPTIMIZED)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# Assets Visuales
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA ($HIVE) ---
CONST = {
    "COSTO_POLEN": 10,        # Costo Energía por Tap
    "RECOMPENSA_BASE": 0.50,  # Base HIVE ganada por Tap
    "DECAY_OXIGENO": 5.0,     # Penalización inactividad
    "COSTO_ENJAMBRE": 100,    # Costo crear Célula (Influencia)
    "COSTO_RECARGA": 200,     # Costo recarga (Prioridad)
    "BONO_REFERIDO": 500      # Valor virtual para Rango
}

# --- SISTEMA DE 5 RANGOS (JERARQUÍA SOCIAL) ---
RANGOS_CONFIG = {
    "OBRERO":     {"nivel": 1, "meta_hive": 0,      "max_energia": 500,  "bonus_tap": 1.0, "icono": "🔨"},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,   "max_energia": 1000, "bonus_tap": 1.2, "icono": "🔭"},
    "SOLDADO":    {"nivel": 3, "meta_hive": 20000,  "max_energia": 1500, "bonus_tap": 1.5, "icono": "⚔️"},
    "GUARDIAN":   {"nivel": 4, "meta_hive": 50000,  "max_energia": 2500, "bonus_tap": 2.0, "icono": "🛡️"},
    "REINA":      {"nivel": 5, "meta_hive": 200000, "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑"}
}

# --- MATRIZ DE PLATAFORMAS (30 TAREAS DE VALOR) ---
FORRAJEO_DB = {
    "TIER_1": [ # ACCIÓN REAL: PRODUCCIÓN DE TOKEN
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
    "TIER_2": [ # ACCIÓN REAL: MIXTO (SOLDADO+)
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
    "TIER_3": [ # ACCIÓN REAL: VALOR USD (GUARDIAN+)
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
# FUNCIONES VISUALES
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    """Renderiza barra de energía visual."""
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_progress_to_next_rank(hive: float, referrals: int) -> str:
    """Calcula el progreso en la jerarquía."""
    poder = hive + (referrals * CONST["BONO_REFERIDO"])
    niveles = list(RANGOS_CONFIG.values())
    siguiente = None
    for nivel in niveles:
        if nivel["meta_hive"] > poder:
            siguiente = nivel
            break
    if siguiente:
        falta = siguiente["meta_hive"] - poder
        return f"Meta: faltan {falta:,.0f}"
    return "NIVEL MÁXIMO"

# ==============================================================================
# MOTORES LÓGICOS (BIO ENGINE)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0)
        refs = len(node.get("referrals", []))
        
        # ROL = VALOR + INFLUENCIA
        poder = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango_actual = "OBRERO"
        stats = RANGOS_CONFIG["OBRERO"]
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
        
        if cv < 0.05: return 0.1, "🚫 BOT"
        if 0.05 <= cv <= 0.35: return 1.3, "⚡ COMBO"
        return 1.0, "✅"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# PASO 1: ENGANCHE (HOOK MODEL)
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
        
        txt = (
            "🐝 **BIENVENIDO A LA COLMENA**\n"
            "────────────────────\n"
            f"**{user.first_name}**, aquí cada acción cuenta.\n"
            "Cada tarea fortalece el panal.\n"
            "Cada miembro deja huella.\n\n"
            "Tu lugar ya existe.\n"
            "**¿Estás listo para ocuparlo?**\n\n"
            "🛡️ **VERIFICACIÓN:**\n"
            f"Copia este código: `{captcha}`"
        )
        try: await update.message.reply_photo(IMG_GENESIS, caption=txt, parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error en start: {e}")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ ACEPTO Y CONTINÚO", callback_data="accept_terms")]]
            await update.message.reply_text(
                "📜 **PROTOCOLO DE INGRESO**\n\n"
                "Para activar tu nodo, aceptas recibir actualizaciones y misiones.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Código incorrecto.")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0 # Recompensa Inmediata
            node['caste'] = "OBRERO"
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🚀 ACCESO AL PANAL", callback_data="go_dash")]]
            await update.message.reply_text(
                "🎉 **¡NODO ACTIVADO!**\n\n"
                "🎁 **Recompensa:** `+200 $HIVE`\n"
                "🔨 **Rango:** OBRERO\n\n"
                "Tu economía empieza ahora.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Email no válido.")
        return

    try:
        node = await db.db.get_node(uid)
        if node and node.get("email"): await show_dashboard(update, context)
    except: pass

# ==============================================================================
# PASO 4: DASHBOARD (PANAL CENTRAL - GRID 2x3)
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
        if not node: await msg("Cargando..."); return
        if not node.get("email"): context.user_data['step']='email_wait'; await msg("Falta Email"); return

        node = BioEngine.calculate_state(node)
        stats = await db.db.get_global_stats()
        await db.db.save_node(uid, node)
        
        rango = node['caste']
        info_rango = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["OBRERO"])
        icono = info_rango["icono"]
        refs = len(node.get("referrals", []))
        progreso = get_next_rank_progress(node['honey'], refs)
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        txt = (
            f"🏰 **PANAL CENTRAL**\n"
            f"────────────────\n"
            f"👤 **{node['username'] or 'Usuario'}** | {icono} {rango}\n"
            f"💰 **{node['honey']:,.2f} $HIVE**\n"
            f"⚡ **Energía:** {polen}/{max_p}\n"
            f"`{bar}`\n\n"
            f"📈 **Siguiente Nivel:** _{progreso}_\n"
            f"🌍 **Tesoro Global:** `{stats['honey']:,.0f}`\n"
            f"────────────────"
        )
        
        # GRID EXACTO 2x3
        kb = [
            [InlineKeyboardButton("⛏️ MINAR (TAP)", callback_data="forage")],
            # FILA 1
            [InlineKeyboardButton("📡 TAREAS", callback_data="tasks"), InlineKeyboardButton("🎖️ PROGRESO", callback_data="rank_info")],
            [InlineKeyboardButton("🐝 COLMENA", callback_data="squad")],
            # FILA 2
            [InlineKeyboardButton("💎 TOKEN", callback_data="shop"), InlineKeyboardButton("👥 EXPANSIÓN", callback_data="team")],
            [InlineKeyboardButton("🌍 ESTADO", callback_data="go_dash")]
        ]
        await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error Dashboard: {e}")

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # MENÚ INFORMATIVO
    txt = (
        "🎖️ **JERARQUÍA Y PODER**\n\n"
        "🔨 **OBRERO:** Inicio.\n"
        "🔭 **EXPLORADOR:** 5k HIVE. Acceso a Tier 2.\n"
        "⚔️ **SOLDADO:** 20k HIVE. Mayor Influencia.\n"
        "🛡️ **GUARDIÁN:** 50k HIVE. Acceso Total.\n"
        "👑 **REINA:** 200k HIVE. Prioridad Absoluta.\n\n"
        "💡 *Consejo: Las células (Squads) aceleran el proceso.*"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ACCIÓN REAL -> RECOMPENSA (OPTIMIZADO PARA NO CRASHEAR)
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Sin Energía. Compra Prioridad (Recarga) en Token.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        
        trace = node.get("entropy_trace", [])
        trace.append(time.time())
        if len(trace)>15: trace.pop(0)
        node["entropy_trace"] = trace
        mult, txt = SecurityEngine.analyze_entropy(trace)
        
        rango = node.get("caste", "OBRERO")
        bonus = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["OBRERO"])["bonus_tap"]
        
        oxy_mult = node['oxygen'] / 100.0
        syn = 1.0
        if node.get("enjambre_id"): 
            c = await db.db.get_cell(node["enjambre_id"])
            if c: syn = c.get("synergy", 1.0)
            
        yield_amt = CONST['RECOMPENSA_BASE'] * mult * bonus * syn * oxy_mult
        node['honey'] += yield_amt
        node['oxygen'] = min(100.0, node['oxygen'] + 1.0)
        
        await db.db.add_global_honey(yield_amt)
        await db.db.save_node(uid, node)
        
        # Feedback rápido
        await q.answer(f"+{yield_amt:.2f} HIVE ({txt})")
        # Update visual ocasional para evitar Rate Limit de Telegram
        if random.random() < 0.2: await show_dashboard(update, context)
        
    except Exception as e:
        logger.error(f"Error Forage: {e}")
        await q.answer("⚠️ Error de conexión", show_alert=True)

# ==============================================================================
# SUB-MÓDULOS (DIAGRAMA DE VALOR)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🪙 TIER 1 (HIVE Token)", callback_data="v_t1")],
        [InlineKeyboardButton("💵 TIER 2 (Mixto 🔒)", callback_data="v_t2")],
        [InlineKeyboardButton("💎 TIER 3 (USD/Stable 🔒)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "📡 **CENTRO DE PRODUCCIÓN**\n\n"
        "Tu trabajo genera valor:\n"
        "1. Selecciona Tarea.\n"
        "2. Ejecuta Acción.\n"
        "3. Recibe Recompensa.\n\n"
        "⚠️ *Más influencia desbloquea mejores Tiers.*"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    rango = node.get("caste", "OBRERO")
    nivel = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["OBRERO"])["nivel"]
    
    # LOCK SYSTEM (TIER GATING)
    if key == "TIER_2" and nivel < 3:
        await q.answer("🔒 BLOQUEADO: Requiere Rango SOLDADO", show_alert=True); return
    if key == "TIER_3" and nivel < 4:
        await q.answer("🔒 BLOQUEADO: Requiere Rango GUARDIÁN", show_alert=True); return

    links = FORRAJEO_DB.get(key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    tipo_pago = "Producción HIVE (Token)" if key == "TIER_1" else "Pago Externo (USD/Stable)"
    
    await q.message.edit_text(
        f"📍 **EJECUCIÓN: {key}**\n\n"
        f"💳 Tipo: {tipo_pago}\n"
        f"⏳ Validación: Automática tras completar.", 
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    # NARRATIVA: USUARIO -> CÉLULA -> COLMENA
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🐝 **CÉLULA ACTIVA: {cell['name']}**\n👥 Abejas: {len(cell['members'])}\n🔥 Sinergia: x{cell['synergy']:.2f}"
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = (
            "⚠️ **NODO AISLADO**\n\n"
            "Necesitas a otros para crecer.\n"
            "Forma una Célula para aumentar tu producción."
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
        await q.answer("✅ Célula Formada"); await squad_menu(update, context)
    else: await q.answer("❌ Saldo Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # FILOSOFÍA DEL TOKEN INTEGRADA
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA (200 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 PASE VIP ($10 USDT)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "💎 **TOKEN $HIVE**\n\n"
        "El Token representa tu Valor Acumulado.\n"
        "Úsalo para:\n\n"
        "🗝️ **Acceso:** Desbloquea Misiones PRO.\n"
        "🗣️ **Influencia:** Crea y lidera Células.\n"
        "⚡ **Prioridad:** Recargas de energía.\n"
        "💱 **Futuro Intercambio:** Q4 2025."
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Energía Restaurada"); await show_dashboard(update, context)
    else: await q.answer("❌ Saldo Insuficiente", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(f"💎 **INVERSIÓN**\n\nEnvía $10 USDT a:\n`{CRYPTO_WALLET_USDT}`", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    refs = len(node.get('referrals', []))
    txt = f"👥 **EXPANSIÓN**\n\nInvitados: {refs}\nEnlace: `{link}`"
    kb = [[InlineKeyboardButton("📤 INVITAR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await q.message.edit_text("✅ Aceptado. Escribe tu **EMAIL**:", parse_mode=ParseMode.MARKDOWN)
        return

    actions = {
        "go_dash": show_dashboard, "forage": forage_action, 
        "tasks": tasks_menu, "rank_info": rank_info_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "TIER_1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "TIER_2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "TIER_3", c),
        "squad": squad_menu, "mk_cell": create_squad_logic,
        "shop": shop_menu, "buy_energy": buy_energy,
        "buy_premium": buy_premium, "team": team_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 NODO REINICIADO")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("Pandora Protocol V314")
async def broadcast_cmd(u, c): pass
