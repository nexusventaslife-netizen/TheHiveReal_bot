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
# CONFIGURACIÓN PANDORA V314 (THE VIRTUOUS CYCLE)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# Assets
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA ($HIVE) ---
CONST = {
    "COSTO_POLEN": 10,        # Costo Energía por TAP
    "RECOMPENSA_BASE": 0.50,  # Base HIVE ganada por TAP
    "DECAY_OXIGENO": 5.0,     # Penalización inactividad
    "COSTO_ENJAMBRE": 100,    # Costo crear Célula
    "COSTO_RECARGA": 200,     # Recarga manual de energía
    "BONO_REFERIDO": 500      # Valor virtual para subir de Rango (Influencia)
}

# --- SISTEMA DE 5 RANGOS (ROLES SUPERIORES) ---
RANGOS_CONFIG = {
    "OBRERO":     {"nivel": 1, "meta_hive": 0,      "max_energia": 500,  "bonus_tap": 1.0, "icono": "🔨"},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,   "max_energia": 1000, "bonus_tap": 1.2, "icono": "🔭"},
    "SOLDADO":    {"nivel": 3, "meta_hive": 20000,  "max_energia": 1500, "bonus_tap": 1.5, "icono": "⚔️"},
    "GUARDIAN":   {"nivel": 4, "meta_hive": 50000,  "max_energia": 2500, "bonus_tap": 2.0, "icono": "🛡️"},
    "REINA":      {"nivel": 5, "meta_hive": 200000, "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑"}
}

# --- MATRIZ DE PLATAFORMAS (30 LINKS) ---
FORRAJEO_DB = {
    "TIER_1": [
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
    "TIER_2": [ # REQUISITO: SOLDADO (Acceso Restringido)
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
    "TIER_3": [ # REQUISITO: GUARDIAN (Acceso VIP)
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
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_progress_to_next_rank(hive: float, referrals: int) -> str:
    poder_total = hive + (referrals * CONST["BONO_REFERIDO"])
    niveles = list(RANGOS_CONFIG.values())
    siguiente = None
    
    for nivel in niveles:
        if nivel["meta_hive"] > poder_total:
            siguiente = nivel
            break
            
    if siguiente:
        falta = siguiente["meta_hive"] - poder_total
        # Sugerencia de Influencia (Referidos)
        ref_necesarios = math.ceil(falta / CONST["BONO_REFERIDO"])
        return f"Faltan {falta:,.0f} HIVE (o {ref_necesarios} amigos) para {siguiente['icono']}"
    
    return "👑 RANGO MÁXIMO ALCANZADO"

# ==============================================================================
# MOTORES LÓGICOS (BIO ENGINE)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        # Producción de Valor
        saldo_real = node.get("honey", 0)
        num_refs = len(node.get("referrals", []))
        
        # Influencia = Saldo + (Amigos * Bono)
        poder_de_ascenso = saldo_real + (num_refs * CONST["BONO_REFERIDO"])
        
        rango_actual = "OBRERO"
        stats_actuales = RANGOS_CONFIG["OBRERO"]
        
        for nombre_rango, datos in RANGOS_CONFIG.items():
            if poder_de_ascenso >= datos["meta_hive"]:
                rango_actual = nombre_rango
                stats_actuales = datos
        
        node["caste"] = rango_actual 
        node["max_polen"] = stats_actuales["max_energia"]
        
        # Regeneración (Prioridad)
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
        
        if cv < 0.05: return 0.1, "🔴 BOT"
        if 0.05 <= cv <= 0.35: return 1.3, "⚡ COMBO"
        return 1.0, "🟢 OK"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# FLUJO DE INICIO (HOOK)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    await db.db.create_node(user.id, user.first_name, user.username, ref)
    node = await db.db.get_node(user.id)
    
    # Paso 4: Acceso directo si ya existe
    if node.get("email"):
        await show_dashboard(update, context)
        return

    # Paso 1: Acción Simple (Captcha)
    captcha = SecurityEngine.generate_captcha()
    context.user_data['captcha'] = captcha
    context.user_data['step'] = 'captcha_wait'
    
    txt = (
        "🐝 **BIENVENIDO A LA COLMENA**\n"
        "────────────────────\n"
        f"Hola, **{user.first_name}**.\n\n"
        "Aquí, cada acción cuenta.\n"
        "Cada tarea fortalece el panal.\n"
        "Cada miembro deja huella.\n\n"
        "Tu lugar ya existe.\n"
        "**¿Estás listo para ocuparlo?**\n\n"
        "🛡️ **VERIFICACIÓN HUMANA:**\n"
        f"Copia este código: `{captcha}`"
    )
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    # Captcha -> Opt-in Legal
    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ ACEPTO Y CONTINÚO", callback_data="accept_terms")]]
            await update.message.reply_text(
                "📜 **PROTOCOLO DE COMUNICACIÓN**\n\n"
                "Para vincular tu neuro-enlace, debes aceptar recibir:\n"
                "• Actualizaciones críticas de la Colmena.\n"
                "• Propaganda de aliados estratégicos.\n"
                "• Información sobre recompensas y airdrops.\n\n"
                "¿Aceptas las condiciones para proceder?",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Código incorrecto.")
        return

    # Paso 2: Recompensa Inmediata
    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0
            node['caste'] = "OBRERO"
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🚀 ENTRAR AL PANAL", callback_data="go_dash")]]
            await update.message.reply_text(
                "🎉 **NODO ACTIVADO**\n\n"
                "Has recibido: **+200 $HIVE**\n"
                "Rango Inicial: **OBRERO** 🔨\n\n"
                "Tu producción de valor comienza ahora.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Email no válido.")
        return

    node = await db.db.get_node(uid)
    if node and node.get("email"): await show_dashboard(update, context)

# ==============================================================================
# DASHBOARD (PANAL CENTRAL - GRID 2x3)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    progreso_txt = calculate_progress_to_next_rank(node['honey'], refs)
    
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
        f"📈 **Siguiente Nivel:** _{progreso_txt}_\n"
        f"🌍 **Tesoro Global:** `{stats['honey']:,.0f}`\n"
        f"────────────────"
    )
    
    # GRID 2x3 EXACTO
    kb = [
        [InlineKeyboardButton("⛏️ MINAR (TAP)", callback_data="forage")], # Acción Principal
        
        [InlineKeyboardButton("📡 TAREAS", callback_data="tasks"), InlineKeyboardButton("🎖️ PROGRESO", callback_data="rank_info")],
        [InlineKeyboardButton("🐝 COLMENA", callback_data="squad"), InlineKeyboardButton("💎 TOKEN", callback_data="shop")],
        [InlineKeyboardButton("👥 EXPANSIÓN", callback_data="team"), InlineKeyboardButton("📊 ESTADO", callback_data="go_dash")]
    ]
    try: await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: pass

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    txt = (
        "🎖️ **TABLA DE RANGOS**\n\n"
        "🔨 **OBRERO:** Inicio\n"
        "🔭 **EXPLORADOR:** 5,000 HIVE\n"
        "⚔️ **SOLDADO:** 20,000 HIVE\n"
        "🛡️ **GUARDIÁN:** 50,000 HIVE\n"
        "👑 **REINA:** 200,000 HIVE\n\n"
        "💡 *Tu Influencia (Referidos) acelera el ascenso.*"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await q.answer(f"+{yield_amt:.2f} HIVE ({txt})")
    if random.random() < 0.2: await show_dashboard(update, context)

# ==============================================================================
# SUB-MÓDULOS (LÓGICA ECONÓMICA)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 TIER 1 (HIVE Token)", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 TIER 2 (Soldado 🔒)", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 TIER 3 (Guardián 🔒)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "📡 **SELECCIÓN DE TAREAS**\n\n"
        "🔹 **Tier 1:** Producción de Token (Lenta)\n"
        "🔸 **Tier 3:** Pago Externo Inmediato (USD/Stable)\n\n"
        "⚠️ *Los niveles altos requieren Rango (Acceso).* "
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    rango = node.get("caste", "OBRERO")
    nivel = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["OBRERO"])["nivel"]
    
    # LOCK SYSTEM (TIER GATING = ACCESO)
    if key == "TIER_2" and nivel < 3:
        await q.answer("🔒 BLOQUEADO: Requiere Rango SOLDADO", show_alert=True); return
    if key == "TIER_3" and nivel < 4:
        await q.answer("🔒 BLOQUEADO: Requiere Rango GUARDIÁN", show_alert=True); return

    links = FORRAJEO_DB.get(key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    tipo_pago = "Producción HIVE (Token)" if key == "TIER_1" else "Pago Externo (USD/Stable)"
    
    await q.message.edit_text(
        f"📍 **EJECUCIÓN: {key}**\n"
        f"💳 Tipo: {tipo_pago}\n"
        f"⏳ Validación: Automática tras completar.", 
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🐝 **COLMENA ACTIVA: {cell['name']}**\n👥 Abejas: {len(cell['members'])}\n🔥 Sinergia: x{cell['synergy']:.2f}"
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        # AQUÍ INTEGRO TU DIAGRAMA DE CRECIMIENTO
        txt = (
            "⚠️ **Necesitas otros para crecer.**\n\n"
            "[Usuario] → [Célula] → [Colmena]\n\n"
            "Forma una Célula para aumentar producción."
        )
        kb = [[InlineKeyboardButton("➕ CREAR CÉLULA (100 HIVE)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Célula Fundada"); await squad_menu(update, context)
    else: await q.answer("❌ Saldo insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # MENÚ "TOKEN" SEGÚN DIAGRAMA (ACCESO / PRIORIDAD)
    txt = (
        "💎 **UTILIDAD DEL TOKEN ($HIVE)**\n\n"
        "1. **Acceso:** Desbloquea Tiers de Misión.\n"
        "2. **Prioridad:** Recarga Energía al instante.\n"
        "3. **Futuro:** Intercambio por Stablecoin.\n\n"
        "🔻 **GASTAR HIVE:**"
    )
    kb = [
        [InlineKeyboardButton("⚡ COMPRAR PRIORIDAD (Recarga 200 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 STATUS VIP ($10 USDT)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Prioridad Adquirida: Energía Full"); await show_dashboard(update, context)
    else: await q.answer("❌ Saldo Insuficiente", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(f"💎 **INVERSIÓN**\n\nEnvía $10 USDT a:\n`{CRYPTO_WALLET_USDT}`", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    refs = len(node.get('referrals', []))
    # AQUÍ INTEGRO TU DIAGRAMA DE INFLUENCIA
    txt = (
        f"👥 **EXPANSIÓN DE INFLUENCIA**\n\n"
        f"Más Influencia = Más Oportunidades\n"
        f"Invitados: **{refs}**\n\n"
        f"🔗 Enlace: `{link}`"
    )
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
