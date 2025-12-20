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
# CONFIGURACIÓN PANDORA V307 (RANGOS DINÁMICOS & HIVE TOKEN)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# Assets Visuales (Banners)
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA ($HIVE) ---
CONST = {
    "COSTO_POLEN": 10,        # Costo de energía por TAP
    "RECOMPENSA_BASE": 0.50,  # HIVE base por TAP
    "DECAY_OXIGENO": 5.0,     # Pérdida de salud por inactividad
    "COSTO_ENJAMBRE": 100,    # Costo crear enjambre
    "COSTO_RECARGA": 200,     # Costo recargar energía manual
    "BONO_REFERIDO": 500      # HIVE "Virtual" que descuenta para subir de rango
}

# --- SISTEMA DE RANGOS EVOLUTIVOS ---
# La meta es HIVE acumulado.
# Cada referido cuenta como 'BONO_REFERIDO' (500) HIVE virtuales para alcanzar la meta antes.
RANGOS_CONFIG = {
    "OBRERO": {
        "meta_hive": 0,         # Inicio
        "max_energia": 500,     
        "bonus_tap": 1.0,       
        "icono": "🔨"
    },
    "EXPLORADOR": {
        "meta_hive": 2000,      # Requiere 2000 HIVE (o menos si tienes referidos)
        "max_energia": 1000,    
        "bonus_tap": 1.2,       # +20% ganancia
        "icono": "🔭"
    },
    "SOLDADO": {
        "meta_hive": 5000,      
        "max_energia": 1500,    
        "bonus_tap": 1.5,       # +50% ganancia
        "icono": "⚔️"
    },
    "GUARDIAN": {
        "meta_hive": 15000,     
        "max_energia": 2500,    
        "bonus_tap": 2.0,       # x2 ganancia
        "icono": "🛡️"
    },
    "REINA": {
        "meta_hive": 50000,     # Nivel Máximo
        "max_energia": 5000,    
        "bonus_tap": 3.0,       # x3 ganancia
        "icono": "👑"
    }
}

# --- MATRIZ DE 30 PLATAFORMAS (Recursos Externos) ---
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
    "TIER_2": [
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
    "TIER_3": [
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
    """Barra de Energía Visual."""
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_progress_to_next_rank(hive: float, referrals: int) -> str:
    """
    Calcula cuánto falta para el siguiente rango considerando el descuento por referidos.
    """
    # HIVE "Virtual" = HIVE Real + (Referidos * Bono)
    poder_total = hive + (referrals * CONST["BONO_REFERIDO"])
    
    niveles = list(RANGOS_CONFIG.values())
    siguiente = None
    
    for nivel in niveles:
        if nivel["meta_hive"] > poder_total:
            siguiente = nivel
            break
            
    if siguiente:
        falta = siguiente["meta_hive"] - poder_total
        # Sugerencia dinámica
        ref_necesarios = math.ceil(falta / CONST["BONO_REFERIDO"])
        return f"Faltan {falta:.0f} HIVE (o {ref_necesarios} amigos) para {siguiente['icono']}"
    
    return "👑 RANGO MÁXIMO ALCANZADO"

# ==============================================================================
# MOTORES LÓGICOS (BIO ENGINE ACTUALIZADO)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        # 1. CÁLCULO DE RANGO DINÁMICO
        # Rango basado en Trabajo (HIVE) + Viralidad (Referidos)
        saldo_real = node.get("honey", 0)
        num_refs = len(node.get("referrals", []))
        
        # El poder para subir de rango es la suma de tu HIVE + un bono por cada amigo
        poder_de_ascenso = saldo_real + (num_refs * CONST["BONO_REFERIDO"])
        
        rango_actual = "OBRERO"
        stats_actuales = RANGOS_CONFIG["OBRERO"]
        
        # Buscar el rango más alto que cumple el criterio
        for nombre_rango, datos in RANGOS_CONFIG.items():
            if poder_de_ascenso >= datos["meta_hive"]:
                rango_actual = nombre_rango
                stats_actuales = datos
        
        # Aplicar nuevo rango y sus stats
        node["caste"] = rango_actual
        node["max_polen"] = stats_actuales["max_energia"]
        
        # 2. REGENERACIÓN DE ENERGÍA (DUAL: TIEMPO)
        if elapsed > 0:
            regen = elapsed * 0.8 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        # 3. SALUD (OXÍGENO)
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
        
        if cv < 0.05: return 0.1, "🔴 BOT DETECTADO"
        if 0.05 <= cv <= 0.35: return 1.3, "⚡ COMBO X1.3"
        return 1.0, "🟢 OK"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# FLUJO DE INICIO (ONBOARDING)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    await db.db.create_node(user.id, user.first_name, user.username, ref)
    node = await db.db.get_node(user.id)
    
    # Si ya está registrado, vamos al Dashboard
    if node.get("email"):
        await show_dashboard(update, context)
        return

    captcha = SecurityEngine.generate_captcha()
    context.user_data['captcha'] = captcha
    context.user_data['step'] = 'captcha_wait'
    
    txt = (
        "🟡 **PROTOCOLO PANDORA: INICIANDO...**\n"
        "────────────────────\n"
        f"Usuario: **{user.first_name}**\n\n"
        "Estás entrando a la Colmena Digital.\n"
        "Aquí tu rango (Obrero, Soldado, Reina) depende de tu **TRABAJO**.\n\n"
        "🛡️ **DEMUESTRA QUE ERES HUMANO:**\n"
        f"Copia este código: `{captcha}`"
    )
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    # PASO 1: CAPTCHA
    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            # Sin selección de casta manual. Todos empiezan como OBRERO.
            context.user_data['step'] = 'email_wait'
            await update.message.reply_text(
                "✅ **VERIFICACIÓN EXITOSA**\n\n"
                "Para guardar tus $HIVE y progreso en la nube:\n"
                "📧 **ESCRIBE TU EMAIL:**",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Código incorrecto.")
        return

    # PASO 2: EMAIL
    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0 # Bono Bienvenida
            node['caste'] = "OBRERO" # Rango Base
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🚀 ENTRAR A LA COLMENA", callback_data="go_dash")]]
            await update.message.reply_text(
                "🎉 **REGISTRO COMPLETO**\n\n"
                "Has recibido: **+200 $HIVE**\n"
                "Rango Inicial: **OBRERO** 🔨\n\n"
                "Invita amigos para ascender más rápido.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Email no válido.")
        return

    node = await db.db.get_node(uid)
    if node and node.get("email"): await show_dashboard(update, context)

# ==============================================================================
# DASHBOARD (NÚCLEO DEL JUEGO)
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

    # Recalcular Rango y Energía
    node = BioEngine.calculate_state(node)
    stats = await db.db.get_global_stats()
    await db.db.save_node(uid, node)
    
    # Datos para mostrar
    rango = node['caste']
    info_rango = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["OBRERO"])
    icono = info_rango["icono"]
    
    # Progreso al siguiente nivel (Gamificación)
    progreso_txt = calculate_progress_to_next_rank(node['honey'], len(node.get('referrals', [])))
    
    # Barra de Energía
    polen = int(node['polen'])
    max_p = int(node['max_polen'])
    bar = render_bar(polen, max_p)
    
    txt = (
        f"🌍 **ESTADO GLOBAL**\n"
        f"👥 Nodos: `{stats['nodes']:,}` | 💰 Treasury: `{stats['honey']:,.0f} HIVE`\n"
        f"────────────────\n"
        f"🛡️ **{node['username'] or 'Usuario'}**\n"
        f"🎖️ Rango: **{rango}** {icono}\n"
        f"📈 _{progreso_txt}_\n\n"
        f"⚡ **Energía:** {polen}/{max_p}\n"
        f"`{bar}`\n\n"
        f"💵 **BALANCE:** `{node['honey']:.2f} $HIVE`\n"
        f"────────────────"
    )
    
    kb = [
        [InlineKeyboardButton("⛏️ TRABAJAR (TAP)", callback_data="forage")],
        [InlineKeyboardButton("📡 MISIONES", callback_data="tasks"), InlineKeyboardButton("🐝 ENJAMBRE", callback_data="squad")],
        [InlineKeyboardButton("💎 MERCADO", callback_data="shop"), InlineKeyboardButton("👥 EXPANSIÓN", callback_data="team")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="go_dash")]
    ]
    try: await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: pass

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción de Minería / Trabajo."""
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    node = BioEngine.calculate_state(node)
    
    if node['polen'] < CONST['COSTO_POLEN']:
        await q.answer("⚡ Sin energía. Recarga o espera.", show_alert=True); return

    node['polen'] -= CONST['COSTO_POLEN']
    node['last_pulse'] = time.time()
    
    # Anti-bot
    trace = node.get("entropy_trace", [])
    trace.append(time.time())
    if len(trace)>15: trace.pop(0)
    node["entropy_trace"] = trace
    mult, txt = SecurityEngine.analyze_entropy(trace)
    
    # BONOS POR RANGO (Escalafón)
    rango_actual = node.get("caste", "OBRERO")
    bonus_rango = RANGOS_CONFIG.get(rango_actual, RANGOS_CONFIG["OBRERO"])["bonus_tap"]
    
    oxy_mult = node['oxygen'] / 100.0
    syn = 1.0
    if node.get("enjambre_id"): 
        c = await db.db.get_cell(node["enjambre_id"])
        if c: syn = c.get("synergy", 1.0)
        
    # Fórmula Final de Ganancia
    yield_amt = CONST['RECOMPENSA_BASE'] * mult * bonus_rango * syn * oxy_mult
    node['honey'] += yield_amt
    node['oxygen'] = min(100.0, node['oxygen'] + 1.0)
    
    await db.db.add_global_honey(yield_amt)
    await db.db.save_node(uid, node)
    
    await q.answer(f"+{yield_amt:.2f} HIVE ({txt})")
    
    if random.random() < 0.2: await show_dashboard(update, context)

# ==============================================================================
# MENÚS SECUNDARIOS
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 FÁCIL", callback_data="v_t1"), InlineKeyboardButton("🟡 MEDIO", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 DIFÍCIL (PRO)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text("📡 **MISIONES DE CAMPO**\nCompleta tareas para ganar HIVE:", reply_markup=InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str):
    links = FORRAJEO_DB.get(key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    await update.callback_query.message.edit_text(f"📍 **TAREAS DISPONIBLES: {key}**", reply_markup=InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = (
            f"🐝 **TU ENJAMBRE: {cell['name']}**\n"
            f"────────────────\n"
            f"👥 Integrantes: {len(cell['members'])}\n"
            f"🔥 Sinergia: x{cell['synergy']:.2f}\n"
            f"🆔 ID: `{cell['id']}`"
        )
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = "⚠️ **SIN ENJAMBRE**\n\nTrabajar solo es duro.\nFunda un enjambre para aumentar la producción."
        kb = [[InlineKeyboardButton("➕ FUNDAR ENJAMBRE (100 HIVE)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Enjambre Fundado"); await squad_menu(update, context)
    else: await q.answer("❌ HIVE Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        # Opcion de Energía Dual (Pagar HIVE para recargar al instante)
        [InlineKeyboardButton("⚡ RECARGA INSTANTÁNEA (200 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 PASE VIP ($10 USDT)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text("💎 **MERCADO DE LA COLMENA**", reply_markup=InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen'] # Recarga total pagada
        await db.db.save_node(uid, node)
        await q.answer("⚡ Energía Restaurada al 100%"); await show_dashboard(update, context)
    else: await q.answer("❌ Te falta HIVE", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(f"💎 **APOYA EL PROYECTO**\n\nEnvía $10 USDT a:\n`{CRYPTO_WALLET_USDT}`", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    
    refs = len(node.get('referrals', []))
    descuento_rango = refs * CONST["BONO_REFERIDO"]
    
    txt = (
        f"👥 **EXPANSIÓN DE COLMENA**\n\n"
        f"¡Trae nuevos nodos al sistema!\n"
        f"🔗 **Enlace:**\n`{link}`\n\n"
        f"📊 Invitados: **{refs}**\n"
        f"🚀 Impulso de Rango: **+{descuento_rango} HIVE Virtuales**"
    )
    kb = [[InlineKeyboardButton("📤 COMPARTIR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# ROUTER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    actions = {
        "go_dash": show_dashboard, "forage": forage_action, "tasks": tasks_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "TIER_1"),
        "v_t2": lambda u,c: view_tier_generic(u, "TIER_2"),
        "v_t3": lambda u,c: view_tier_generic(u, "TIER_3"),
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
async def help_cmd(u, c): await u.message.reply_text("Pandora Protocol V307")
async def broadcast_cmd(u, c): pass
