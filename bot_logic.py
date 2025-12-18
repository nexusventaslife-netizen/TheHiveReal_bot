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
# CONFIGURACIÓN PANDORA V305 (UI PRO HAMSTER-STYLE)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# Assets Visuales
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- MATRIZ DE 30 PLATAFORMAS (Monetización) ---
FORRAJEO_DB = {
    "TIER_1": [
        {"name": "📺 Timebucks (Videos)", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC (Clicks)", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "💸 FreeCash (Apps)", "url": "https://freecash.com/r/XYN98"},
        {"name": "🎮 GameHag", "url": "https://gamehag.com/r/NWUD9QNR"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"},
        {"name": "💧 FaucetPay", "url": "https://faucetpay.io/?r=123456"},
        {"name": "⚡ Cointiply", "url": "http://cointiply.com/r/Pandora"},
        {"name": "🖱️ BTCClicks", "url": "https://btcclicks.com/?r=Pandora"},
        {"name": "🔥 FireFaucet", "url": "https://firefaucet.win/ref/Pandora"}
    ],
    "TIER_2": [
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

# Configuración de Roles (Castas)
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
    """Barra de progreso visual estilo juego."""
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    # Usamos caracteres más sólidos para la barra
    return "▓" * fill + "░" * (length - fill)

# ==============================================================================
# MOTORES LÓGICOS (Backend del juego)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        casta = node.get("caste")
        specs = CASTAS_CONFIG.get(casta, CASTAS_CONFIG["RECOLECTOR"])
        node["max_polen"] = specs["max_polen"]
        
        # Regenerar Energía
        if elapsed > 0:
            regen = elapsed * 0.5 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        # Decaer Salud (Oxígeno)
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
        
        if cv < 0.05: return 0.1, "🔴 DETECTADO: AUTO-CLICKER"
        if 0.05 <= cv <= 0.35: return 1.3, "🔥 RITMO PERFECTO (x1.3)"
        return 1.0, "🟢 TAP VALIDADO"

    @staticmethod
    def generate_captcha() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# HANDLERS (FLUJO DEL USUARIO)
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
        "🟡 **BIENVENIDO A PANDORA**\n"
        "────────────────────\n"
        f"👋 Hola, **{user.first_name}**.\n\n"
        "Estás a punto de entrar a la Colmena Mundial.\n"
        "Esto no es solo un juego, es un sistema de minería social.\n\n"
        "🔐 **COPIA ESTE CÓDIGO PARA ENTRAR:**\n"
        f"`{captcha}`"
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
                [InlineKeyboardButton("🐝 RECOLECTOR (Más Miel)", callback_data="sel_RECOLECTOR")],
                [InlineKeyboardButton("🛡️ GUARDIÁN (Más Energía)", callback_data="sel_GUARDIAN")],
                [InlineKeyboardButton("🧭 EXPLORADOR (Más Suerte)", callback_data="sel_EXPLORADOR")]
            ]
            await update.message.reply_text(
                "🧬 **ELIGE TU CLASE**\n\nEsta decisión es permanente. Define tu rol en la economía.",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await update.message.reply_text("❌ Código incorrecto. Intenta de nuevo.")
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
            
            kb = [[InlineKeyboardButton("🚀 ENTRAR AL DASHBOARD", callback_data="go_dash")]]
            await update.message.reply_text("🎉 **REGISTRO COMPLETO**\nHas recibido +200 Miel de bono.", reply_markup=InlineKeyboardMarkup(kb))
        except EmailNotValidError:
            await update.message.reply_text("⚠️ Email inválido. Por favor verifica.")
        return

    node = await db.db.get_node(uid)
    if node and node.get("email"): await show_dashboard(update, context)

# ==============================================================================
# DASHBOARD (DISEÑO MEJORADO)
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        msg = update.callback_query.message.edit_text
        uid = update.callback_query.from_user.id
    else:
        msg = update.message.reply_text
        uid = update.effective_user.id

    node = await db.db.get_node(uid)
    if not node: await msg("⚠️ Error. Usa /start"); return
    
    if not node.get("caste"): await start_command(update, context); return
    if not node.get("email"):
        context.user_data['step'] = 'email_wait'
        await msg("📧 Faltó un paso: Escribe tu Email:"); return

    node = BioEngine.calculate_state(node)
    stats = await db.db.get_global_stats()
    await db.db.save_node(uid, node)
    
    # Datos visuales
    polen = int(node['polen'])
    max_p = int(node['max_polen'])
    bar = render_bar(polen, max_p)
    oxy = node['oxygen']
    
    # Nuevo Texto Profesional
    txt = (
        f"🌍 **ESTADO DE LA RED MUNDIAL**\n"
        f"👥 Usuarios: `{stats['nodes']:,}` | 💰 Miel Total: `{stats['honey']:,.2f}`\n"
        f"────────────────────────\n"
        f"👤 **TU PERFIL** ({node['caste']})\n"
        f"🍯 **SALDO:** `{node['honey']:.2f} MIEL`\n\n"
        f"⚡ **ENERGÍA:** {polen}/{max_p}\n"
        f"`{bar}`\n\n"
        f"❤️ **SALUD:** {oxy:.1f}%\n"
        f"────────────────────────\n"
        f"💡 *Toca 'Minar' para generar recursos.*"
    )
    
    # Botones más claros y directos
    kb = [
        [InlineKeyboardButton("⛏️ MINAR MIEL (TAP)", callback_data="forage")],
        [InlineKeyboardButton("💰 GANAR +", callback_data="tasks"), InlineKeyboardButton("🏰 CLAN / SQUAD", callback_data="squad")],
        [InlineKeyboardButton("🛒 TIENDA", callback_data="shop"), InlineKeyboardButton("👥 AMIGOS", callback_data="team")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="go_dash")]
    ]
    try: await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: pass

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    node = BioEngine.calculate_state(node)
    
    if node['polen'] < CONST['COSTO_POLEN']:
        await q.answer("💤 Sin energía. Descansa un poco.", show_alert=True); return

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
    
    # Feedback en la alerta (Toaster)
    await q.answer(f"✅ +{yield_amt:.2f} Miel | {txt}")
    
    # Refrescar dashboard aleatoriamente para efecto visual
    if random.random() < 0.15: await show_dashboard(update, context)

# ==============================================================================
# SUB-MENÚS (Con textos mejorados)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 TAREAS FÁCILES", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 INGRESOS PASIVOS", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 OFERTAS CRYPTO", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text("💰 **ZONA DE GANANCIAS**\nElige una categoría para ganar Miel extra:", reply_markup=InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str):
    links = FORRAJEO_DB.get(key, [])
    kb = []
    for item in links:
        # Formato: Nombre de la tarea
        kb.append([InlineKeyboardButton(f"{item['name']}", url=item["url"])])
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    await update.callback_query.message.edit_text(f"📂 **TAREAS DISPONIBLES: {key}**", reply_markup=InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🏰 **TU CLAN: {cell['name']}**\n\n👥 Miembros: {len(cell['members'])}\n🔥 Multiplicador: x{cell['synergy']:.2f}\n🆔 ID: `{cell['id']}`"
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = "⚠️ **SIN CLAN**\n\nJugar solo es ineficiente.\nCrea tu propio Clan por 100 Miel para aumentar tus ganancias."
        kb = [[InlineKeyboardButton("➕ CREAR CLAN (100 Miel)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Clan-{random.randint(1000, 9999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ ¡Clan Fundado!"); await squad_menu(update, context)
    else: await q.answer("❌ Te falta Miel para crear un Clan.", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⚡ LLENAR ENERGÍA (200 Miel)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 COMPRAR VIP ($10 USDT)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    await update.callback_query.message.edit_text("🛒 **TIENDA DE RECURSOS**", reply_markup=InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ ¡Energía al máximo!"); await show_dashboard(update, context)
    else: await q.answer("❌ No tienes suficiente Miel.", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(f"💎 **MEMBRESÍA VIP**\n\nEnvía $10 USDT (Red TRC20) a:\n`{CRYPTO_WALLET_USDT}`\n\nLuego contacta a soporte.", parse_mode=ParseMode.MARKDOWN)

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    txt = f"👥 **SISTEMA DE REFERIDOS**\n\nInvita amigos y gana **+100 Miel** por cada uno.\n\n🔗 **Tu Enlace:**\n`{link}`\n\nAmigos invitados: {len(node.get('referrals', []))}"
    kb = [[InlineKeyboardButton("📤 COMPARTIR ENLACE", url=f"https://t.me/share/url?url={link}")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
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
        await q.message.edit_text("🧬 **ROL CONFIRMADO**\n\nÚltimo paso: Escribe tu **EMAIL** para guardar tu progreso:", parse_mode=ParseMode.MARKDOWN)
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
    await update.message.reply_text("💀 CUENTA BORRADA. Escribe /start para reiniciar.")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("Ayuda: Usa los botones del menú para navegar.")
async def broadcast_cmd(u, c): pass
