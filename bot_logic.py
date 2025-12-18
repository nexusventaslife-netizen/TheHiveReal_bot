import logging
import asyncio
import random
import time
import math
import statistics
import os
import ujson as json
# AQUI ESTABA EL ERROR: AGREGUE Dict Y List EXPLICITAMENTE
from typing import Tuple, List, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from loguru import logger
import database as db 
from email_validator import validate_email, EmailNotValidError

# ==============================================================================
# CONFIGURACIÓN PANDORA V303 (FULL)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

FORRAJEO_DB = {
    "TIER_1": [
        {"name": "📺 Timebucks", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "💸 FreeCash", "url": "https://freecash.com/r/XYN98"}
    ],
    "TIER_2": [
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810"}
    ],
    "TIER_3": [
        {"name": "🔥 ByBit ($20)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🏦 Nexo", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"}
    ]
}

CASTAS_CONFIG = {
    "RECOLECTOR": {"desc": "Prod +50%", "bonus_honey": 1.5, "max_polen": 500},
    "GUARDIAN":   {"desc": "Resistencia Max", "bonus_honey": 1.0, "max_polen": 1000},
    "EXPLORADOR": {"desc": "Suerte x2", "bonus_honey": 0.8, "max_polen": 600}
}

CONST = {
    "COSTO_POLEN": 10,
    "RECOMPENSA_BASE": 0.50,
    "DECAY_OXIGENO": 5.0,
    "COSTO_ENJAMBRE": 100,
    "COSTO_RECARGA": 200
}

# ==============================================================================
# FUNCIONES AUXILIARES GLOBALES
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    """Renderiza barra visual. Crucial para el Dashboard."""
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "⬢" * fill + "⬡" * (length - fill)

# ==============================================================================
# MOTORES LÓGICOS (AQUI DABA EL ERROR PORQUE FALTABA Dict)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        casta = node.get("caste")
        specs = CASTAS_CONFIG.get(casta, CASTAS_CONFIG["RECOLECTOR"])
        node["max_polen"] = specs["max_polen"]
        
        # Regenerar
        if elapsed > 0:
            regen = elapsed * 0.5 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        # Decaer
        last_pulse = node.get("last_pulse", now)
        if (now - last_pulse) > 3600:
            decay = ((now - last_pulse) / 3600) * CONST["DECAY_OXIGENO"]
            node["oxygen"] = max(5.0, node.get("oxygen", 100.0) - decay)
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    @staticmethod
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        if len(timestamps) < 5: return 1.0, "Sintonizando..."
        deltas = [timestamps[i]-timestamps[i-1] for i in range(1,len(timestamps))]
        try:
            cv = statistics.stdev(deltas) / statistics.mean(deltas)
        except: return 1.0, ""
        
        if cv < 0.05: return 0.1, "🔴 ARTIFICIAL"
        if 0.05 <= cv <= 0.35: return 1.3, "🌊 FLUJO VITAL"
        return 1.0, "🟢 ORGÁNICO"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# HANDLERS (FLUJO)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    await db.db.create_node(user.id, user.first_name, user.username, ref)
    node = await db.db.get_node(user.id)
    
    if node.get("email") and node.get("caste"):
        await show_dashboard(update, context)
        return

    captcha = SecurityEngine.generate_captcha()
    context.user_data['captcha'] = captcha
    context.user_data['step'] = 'captcha_wait'
    
    txt = (
        "🟡 **PROTOCOLO PANDORA: ACTIVACIÓN**\n"
        "────────────────────\n"
        f"Nodo: **{user.first_name}**\n\n"
        "Sistema biológico detectado.\n"
        "La Colmena requiere **ACTIVACIÓN DIARIA**.\n\n"
        f"🛡️ CÓDIGO DE ENLACE: `{captcha}`"
    )
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'caste_select_wait'
            kb = [
                [InlineKeyboardButton("🐝 RECOLECTOR", callback_data="sel_RECOLECTOR")],
                [InlineKeyboardButton("🛡️ GUARDIÁN", callback_data="sel_GUARDIAN")],
                [InlineKeyboardButton("🧭 EXPLORADOR", callback_data="sel_EXPLORADOR")]
            ]
            await update.message.reply_text(
                "✅ **SEÑAL CONFIRMADA**\n\nConfigura tu genética. Decisión irreversible.",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await update.message.reply_text("❌ Código inválido.")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 200.0
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("📡 CONECTAR", callback_data="go_dash")]]
            await update.message.reply_text("🎉 **NODO ACTIVADO**\nBono: +200 Miel.", reply_markup=InlineKeyboardMarkup(kb))
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Email inválido.")
        return

    node = await db.db.get_node(uid)
    if node and node.get("email"): await show_dashboard(update, context)

# ==============================================================================
# DASHBOARD
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        msg = update.callback_query.message.edit_text
        uid = update.callback_query.from_user.id
    else:
        msg = update.message.reply_text
        uid = update.effective_user.id

    node = await db.db.get_node(uid)
    if not node: await msg("Error. /start"); return
    
    if not node.get("caste"): await start_command(update, context); return
    if not node.get("email"):
        context.user_data['step'] = 'email_wait'
        await msg("⚠️ Escribe tu Email:"); return

    node = BioEngine.calculate_state(node)
    stats = await db.db.get_global_stats()
    await db.db.save_node(uid, node)
    
    polen = int(node['polen'])
    max_p = int(node['max_polen'])
    bar = render_bar(polen, max_p)
    oxy = node['oxygen']
    
    txt = (
        f"🌍 **RED GLOBAL**\n"
        f"Nodos: `{stats['nodes']:,}` | Miel: `{stats['honey']:,.2f}`\n"
        f"────────────────\n"
        f"🧬 **NODO:** `{uid}` | Casta: **{node['caste']}**\n"
        f"⚡ **Polen:** `{bar}` {polen}/{max_p}\n"
        f"🫁 **Eficiencia:** {oxy:.1f}%\n"
        f"🍯 **Reserva:** `{node['honey']:.2f}`"
    )
    
    kb = [
        [InlineKeyboardButton("🌼 FORRAJEAR", callback_data="forage")],
        [InlineKeyboardButton("📡 MISIONES", callback_data="tasks"), InlineKeyboardButton("🦠 ENJAMBRE", callback_data="squad")],
        [InlineKeyboardButton("🛒 TIENDA", callback_data="shop"), InlineKeyboardButton("👥 EXPANSION", callback_data="team")],
        [InlineKeyboardButton("🔄 SINTONIZAR", callback_data="go_dash")]
    ]
    try: await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: pass

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    node = BioEngine.calculate_state(node)
    
    if node['polen'] < CONST['COSTO_POLEN']:
        await q.answer("🥀 Sin Polen.", show_alert=True); return

    node['polen'] -= CONST['COSTO_POLEN']
    node['last_pulse'] = time.time()
    
    trace = node.get("entropy_trace", [])
    trace.append(time.time())
    if len(trace)>15: trace.pop(0)
    node["entropy_trace"] = trace
    mult, txt = SecurityEngine.analyze_entropy(trace)
    
    caste_mult = CASTAS_CONFIG[node['caste']]["bonus_honey"]
    oxy_mult = node['oxygen'] / 100.0
    syn = 1.0
    if node.get("enjambre_id"):
        c = await db.db.get_cell(node["enjambre_id"])
        if c: syn = c.get("synergy", 1.0)
        
    yield_amt = CONST['RECOMPENSA_BASE'] * mult * caste_mult * syn * oxy_mult
    node['honey'] += yield_amt
    node['oxygen'] = min(100.0, node['oxygen'] + 1.0)
    
    await db.db.add_global_honey(yield_amt)
    await db.db.save_node(uid, node)
    await q.answer(f"+{yield_amt:.2f} 🍯 | {txt}")
    
    if random.random() < 0.15: await show_dashboard(update, context)

# ==============================================================================
# SUB-MENÚS
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 FRECUENCIA 1", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 FRECUENCIA 2", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 FRECUENCIA 3", callback_data="v_t3")],
        [InlineKeyboardButton("🔙", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text("📡 **TRANSMISIONES EXTERNAS**", reply_markup=InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str):
    links = FORRAJEO_DB.get(key, [])
    kb = [[InlineKeyboardButton(l["name"], url=l["url"])] for l in links]
    kb.append([InlineKeyboardButton("🔙", callback_data="tasks")])
    await update.callback_query.message.edit_text(f"📍 **CANAL {key}**", reply_markup=InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🦠 **ENJAMBRE: {cell['name']}**\nSinergia: x{cell['synergy']:.2f}\nID: `{cell['id']}`"
        kb = [[InlineKeyboardButton("🔙", callback_data="go_dash")]]
    else:
        txt = "⚠️ **NODO AISLADO**\nCrea un enjambre por 100 Miel."
        kb = [[InlineKeyboardButton("➕ CREAR", callback_data="mk_cell")], [InlineKeyboardButton("🔙", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(1000, 9999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Creado"); await squad_menu(update, context)
    else: await q.answer("❌ Miel insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⚡ SOBRECARGA (200 Miel)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 PREMIUM ($10)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text("🛒 **SUMINISTROS**", reply_markup=InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Listo"); await show_dashboard(update, context)
    else: await q.answer("❌ Pobre", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(f"💎 Envía $10 USDT a:\n`{CRYPTO_WALLET_USDT}`", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    txt = f"👥 **EXPANSIÓN**\nConectados: {len(node.get('referrals', []))}\n🔗 `{link}`"
    kb = [[InlineKeyboardButton("📤 INVITAR", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# ROUTER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d.startswith("sel_"):
        caste = d.split("_")[1]
        uid = q.from_user.id
        node = await db.db.get_node(uid)
        
        specs = CASTAS_CONFIG[caste]
        node["caste"] = caste
        node["max_polen"] = specs["max_polen"]
        node["polen"] = specs["max_polen"]
        await db.db.save_node(uid, node)
        
        context.user_data['step'] = 'email_wait'
        await q.message.edit_text("🧬 **GENÉTICA ESTABLECIDA**\nEscribe tu **EMAIL**:", parse_mode=ParseMode.MARKDOWN)
        return

    actions = {
        "go_dash": show_dashboard, 
        "forage": forage_action, 
        "tasks": tasks_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "TIER_1"),
        "v_t2": lambda u,c: view_tier_generic(u, "TIER_2"),
        "v_t3": lambda u,c: view_tier_generic(u, "TIER_3"),
        "squad": squad_menu, 
        "mk_cell": create_squad_logic, 
        "shop": shop_menu, 
        "buy_energy": buy_energy,
        "buy_premium": buy_premium, 
        "team": team_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 NODO PURGADO")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("Pandora Protocol V303")
async def broadcast_cmd(u, c): pass
