import logging
import asyncio
import random
import time
import math
import os
import ujson as json
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timedelta

from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel, validator, Field
from aiolimiter import AsyncLimiter
from email_validator import validate_email

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes, Application
# CORRECCIÓN AQUÍ: Cambiado 'RateLimited' por 'RetryAfter' (Versión 20.x standard)
from telegram.error import BadRequest, RetryAfter 
from loguru import logger

# IMPORTAMOS TU BASE DE DATOS REDIS
from database import db 

# ==============================================================================
# 🐝 THE ONE HIVE: V13.5 (SCALABLE FIX)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# VARIABLES DE DINERO
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")
LINK_PAYPAL_HARDCODED = "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC"

# --- IDENTIDAD VISUAL ---
IMG_GENESIS = "https://i.postimg.cc/hv2HXWkN/photo-2025-12-22-16-00-42.jpg"
IMG_DASHBOARD = "https://i.postimg.cc/hv2HXWkN/photo-2025-12-22-16-00-42.jpg"

# --- CONSTANTES DE ECONOMÍA (TOKENOMICS ACTIVO) ---
CONST = {
    "COSTO_POLEN": 10,        
    "RECOMPENSA_BASE": 0.05,
    "DECAY_OXIGENO": 4.0,     
    "COSTO_ENJAMBRE": 100,    
    "COSTO_RECARGA": 50,      
    "BONO_REFERIDO": 500,
    "PRECIO_ACELERADOR": 9.99,
    "TRIGGER_EMAIL_HONEY": 50,
    "SQUAD_MULTIPLIER": 0.05,
    
    # ESTRATEGIA DEFLACIONARIA
    "HSP_BASE": 1.0,
    "STREAK_BONUS": 1.1,
    "COMBO_DAILY_MAX": 1000,
    "TAP_RATE_LIMIT": 0.3,     # Anti-bot scale protection
    "VIRAL_FACTOR": 0.05,
    "BURN_RATE_TAP": 0.10,     # Quema 10% (Deflación)
    "HALVING_FACTOR": 1.0,     # Futuro Halving
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 200,  "bonus_tap": 1.0, "hsp_mult": 1.0, "icono": "🐛", "acceso": 0},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 400,  "bonus_tap": 1.1, "hsp_mult": 1.2, "icono": "🐝", "acceso": 1},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 800,  "bonus_tap": 1.2, "hsp_mult": 1.5, "icono": "🔭", "acceso": 2},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 1500, "bonus_tap": 1.5, "hsp_mult": 2.0, "icono": "🛡️", "acceso": 3},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "hsp_mult": 5.0, "icono": "👑", "acceso": 3}
}

# --- RATE LIMITERS (SCALE PROTECTION) ---
rate_limiters = {}

async def get_limiter(uid: int) -> AsyncLimiter:
    if uid not in rate_limiters:
        # Permite 15 acciones por minuto por usuario (evita sobrecarga de CPU)
        rate_limiters[uid] = AsyncLimiter(15, 60) 
    return rate_limiters[uid]

# --- MODELO PYDANTIC ---
class NodeModel(BaseModel):
    honey: float = Field(default=0.0, ge=0.0)
    polen: float = Field(default=200.0, ge=0.0)
    max_polen: float = Field(default=200.0, ge=1.0)
    iil: float = 1.0
    hsp: float = 1.0
    streak: int = 0
    last_tap: float = 0.0
    last_regen: float = Field(default_factory=time.time)
    caste: str = "LARVA"
    squad_id: Optional[str] = None
    email: Optional[str] = None
    ton_wallet: Optional[str] = None 
    nft_boost: float = 0.0           
    joined_at: float = Field(default_factory=time.time)
    referrals: List[int] = Field(default_factory=list)
    hive_staked: float = 0.0

    class Config:
        arbitrary_types_allowed = True

# ==============================================================================
# 🌐 MOTOR DE TRADUCCIÓN
# ==============================================================================
TEXTS = {
    "es": {
        "intro_caption": "Bienvenido a The One Hive V13.\n\nEsto no es un airdrop.\nEsto no es una inversión.\n\nEs un sistema vivo midiendo participación e influencia.",
        "btn_enter": "👉 Acceder al Sistema",
        "intro_step2": "**AVISO DE RED:**\n\nTu progreso es relativo a la actividad de la red.\n\nLos nodos más activos son priorizados en esta fase.",
        "btn_status": "👉 Verificar Nodo",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NODO ESTÁNDAR",
        "status_safe": "✅ NODO VERIFICADO",
        "lbl_energy": "⚡ Energía",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Red:**",
        "footer_msg": "📝 _Prioridad de red calculada en tiempo real._",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 PANALES",
        "btn_rank": "🧬 EVOLUCIÓN",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ PRIORIDAD ($)",
        "btn_preds": "🧠 PREDICCIONES",
        "btn_combo": "🔥 COMBO",
        "btn_lb": "🏆 TOP 10",
        "btn_wallet": "💼 CONNECT WALLET",
        "viral_1": "El acceso temprano sigue abierto.\n\n{link}",
        "viral_2": "No todos deberían entrar.\n\n{link}",
        "sys_event_1": "⚠️ Prioridad reasignada a nodos activos",
        "sys_event_2": "⏳ Ventana de expansión abierta",
        "sys_event_3": "🔒 Capacidad de fase alcanzando límite",
        "feed_action_1": "aseguró posición",
        "feed_action_2": "expandió conexión",
        "lock_msg": "🔒 FASE RESTRINGIDA. Nivel {lvl} requerido.",
        "protect_title": "⚠️ **ASEGURA TU NODO: {reason}**",
        "protect_body": "Al registrar un email:\n• Preservas tu progreso\n\nNo vendemos cuentas.",
        "email_prompt": "🛡️ **REGISTRO DE NODO**\n\nIngresa tu EMAIL para asegurar persistencia:",
        "email_success": "✅ **NODO ASEGURADO**",
        "shop_title": "🛡️ **ACCESO PRIORITARIO MENSUAL**",
        "shop_body": "Mejora velocidad y acceso.\n\nIncluye (30 Días):\n✅ Regeneración rápida\n✅ Acceso a tareas avanzadas",
        "btn_buy_prem": "🛡️ PRIORIDAD (30 DÍAS) - ${price}",
        "btn_buy_energy": "🔋 RECARGA ({cost} HIVE)",
        "pay_txt": "🛡️ **ACCESO PRIORITARIO (30 DÍAS)**\n\n🔹 **Cripto (USDT)**\n`{wallet}`\n\n🔹 **PayPal**\nBotón abajo.",
        "btn_paypal": "💳 Pagar con PayPal",
        "team_title": "👥 **EXPANSIÓN DE RED**",
        "team_body": "Nodos con conexiones activas avanzan más rápido.\n\n🔗 Tu Enlace de Nodo:\n`{link}`",
        "tasks_title": "📡 **ZONAS DE ACTIVIDAD**",
        "tasks_body": "Selecciona el Panal según tu rango:",
        "btn_back": "🔙 VOLVER",
        "green_hive": "PANAL VERDE",
        "gold_hive": "PANAL DORADO",
        "red_hive": "PANAL ROJO",
        "squad_none_title": "⚠️ NODO INDIVIDUAL",
        "squad_none_body": "Los nodos individuales tienen menor prioridad.\nConecta con otros para escalar.",
        "btn_create_squad": "➕ CONECTAR ({cost} HIVE)",
        "squad_active": "🐝 **CONEXIÓN ACTIVA**\n👥 Nodos: {members}\n🔥 IIL Boost: ACTIVO",
        "no_balance": "❌ HIVE Insuficiente",
        "hsp_lbl": "🌐 HSP: x{hsp:.2f}",
        "daily_combo": "🔥 **COMBO DIARIO**\n\nEncuentra la secuencia secreta.\nIngresa los 3 emojis correctos en el chat.",
        "combo_success": "🚀 **COMBO CORRECTO**\n+{amt} HIVE! Streak aumentado.",
        "leaderboard": "🏆 **TOP HSP GLOBAL**\n\n{top10}",
        "predictions": "🧠 **PREDICCIONES HIVE**\n\nEvento: {evento}",
        "streak_lbl": "🔥 Racha: {streak}",
        "pred_vote_ok": "✅ Voto registrado. Si aciertas, tu HSP subirá.",
        "wallet_prompt": "💼 **CONEXIÓN TON**\n\nEnvía tu dirección de Wallet TON (Address) en el chat para recibir el Airdrop futuro.\n\nEjemplo: `UQ...`"
    },
    "en": {
         "intro_caption": "Welcome to The One Hive.",
        "btn_enter": "👉 Access System",
        "intro_step2": "**NETWORK NOTICE:** Active nodes are prioritized.",
        "btn_status": "👉 Verify Node",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ STANDARD NODE",
        "status_safe": "✅ VERIFIED NODE",
        "lbl_energy": "⚡ Energy",
        "lbl_honey": "🍯 Nectar",
        "lbl_feed": "📊 **Network:**",
        "footer_msg": "📝 _Network priority calculated in real-time._",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 HIVES",
        "btn_rank": "🧬 EVOLUTION",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 EXPAND",
        "btn_shop": "🛡️ PRIORITY ($)",
        "btn_preds": "🧠 PREDS",
        "btn_combo": "🔥 COMBO",
        "btn_lb": "🏆 TOP 10",
        "btn_wallet": "💼 CONNECT WALLET",
        "viral_1": "Early access is open.\n\n{link}",
        "viral_2": "Not everyone should enter.\n\n{link}",
        "sys_event_1": "⚠️ Priority reassigned",
        "sys_event_2": "⏳ Window open",
        "sys_event_3": "🔒 Capacity limit",
        "feed_action_1": "secured position",
        "feed_action_2": "expanded connection",
        "lock_msg": "🔒 RESTRICTED. Level {lvl} required.",
        "protect_title": "⚠️ **SECURE NODE: {reason}**",
        "protect_body": "Register email to save progress.",
        "email_prompt": "🛡️ **NODE REGISTRATION**\n\nEnter EMAIL:",
        "email_success": "✅ **SECURED**",
        "shop_title": "🛡️ **PRIORITY ACCESS**",
        "shop_body": "Faster regen & access.",
        "btn_buy_prem": "🛡️ PRIORITY - ${price}",
        "btn_buy_energy": "🔋 RECHARGE ({cost} HIVE)",
        "pay_txt": "🛡️ **PRIORITY ACCESS**\n\n🔹 USDT: `{wallet}`\n🔹 PayPal below.",
        "btn_paypal": "💳 Pay with PayPal",
        "team_title": "👥 **EXPANSION**",
        "team_body": "Link:\n`{link}`",
        "tasks_title": "📡 **ZONES**",
        "tasks_body": "Select Hive:",
        "btn_back": "🔙 BACK",
        "green_hive": "GREEN HIVE",
        "gold_hive": "GOLD HIVE",
        "red_hive": "RED HIVE",
        "squad_none_title": "⚠️ ISOLATED",
        "squad_none_body": "Connect to scale.",
        "btn_create_squad": "➕ CONNECT ({cost} HIVE)",
        "squad_active": "🐝 **ACTIVE**\nNodes: {members}",
        "no_balance": "❌ Insufficient Funds",
        "hsp_lbl": "🌐 HSP: x{hsp:.2f}",
        "daily_combo": "🔥 **DAILY COMBO**\n\nFind the secret sequence.",
        "combo_success": "🚀 **COMBO MATCH**\n+{amt} HIVE!",
        "leaderboard": "🏆 **GLOBAL TOP**\n\n{top10}",
        "predictions": "🧠 **PREDICTIONS**\n\nEvent: {evento}",
        "streak_lbl": "🔥 Streak: {streak}",
        "pred_vote_ok": "✅ Vote registered.",
        "wallet_prompt": "💼 **TON CONNECT**\n\nSend your TON Wallet Address in chat for future Airdrop."
    }
}

def get_text(lang_code: str, key: str, **kwargs) -> str:
    if lang_code and len(lang_code) > 2:
        lang_code = lang_code[:2]
    lang_dict = TEXTS.get(lang_code, TEXTS["en"])
    text = lang_dict.get(key, TEXTS["en"].get(key, f"_{key}_"))
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

# --- PANALES ACTIVOS ---
FORRAJEO_DB = {
    "PANAL_VERDE": [ 
        {"name": "⚡ ADS PRIORITY", "url": "https://t.me/AnuncianteDeTurno"}, 
        {"name": "📺 Timebucks", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"},
        {"name": "💸 FreeCash", "url": "https://freecash.com/r/XYN98"},
        {"name": "🌀 FaucetPay", "url": "https://faucetpay.io/?r=12345"},
        {"name": "💎 Cointiply", "url": "http://cointiply.com/r/12345"},
        {"name": "🕹️ Gamee", "url": "https://www.gamee.com/"},
        {"name": "📱 LootUp", "url": "https://lootup.me/"},
        {"name": "🛍️ Swagbucks", "url": "https://www.swagbucks.com/"},
        {"name": "📥 InboxDollars", "url": "https://www.inboxdollars.com/"},
        {"name": "🦅 StormGain", "url": "https://app.stormgain.com/"},
        {"name": "🔹 RollerCoin", "url": "https://rollercoin.com/"}
    ],
    "PANAL_DORADO": [ 
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"},
        {"name": "🌱 SproutGigs", "url": "https://sproutgigs.com/?a=83fb1bf9"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810"}
    ],
    "PANAL_ROJO": [ 
        {"name": "🔥 ByBit (+20 USDT)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"},
        {"name": "🏦 Nexo", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"},
        {"name": "🆗 OKX", "url": "https://www.okx.com/join/PANDORA"}
    ]
}

# ==============================================================================
# UTILIDADES
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def generate_live_feed(lang: str) -> str:
    acciones = ["conectado", "minando", "HSP UP", "Combo OK", "Wallet Linked"]
    return f"• ID-{random.randint(100,999)} {random.choice(acciones)} ({random.randint(1,9)}m)"

def generate_daily_combo() -> str:
    combos = ["🐝👑🔥", "🍯⚡🛡️", "🔭🐛🟢", "🐝🍯💰", "👑🛡️⚡"]
    today = datetime.now().strftime("%Y%m%d")
    seed = hash(today) % len(combos)
    return combos[seed]

async def get_evento_diario() -> Dict:
    eventos = [
        {"id": "btc_up", "desc": "BTC > $100k today?", "outcome": None},
        {"id": "eth_up", "desc": "ETH > $3k today?", "outcome": None}
    ]
    return random.choice(eventos)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def db_op(fn, *args, **kwargs):
    return await fn(*args, **kwargs)

async def smart_edit(update: Update, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    except (BadRequest, RetryAfter) as e: # CORRECCIÓN VITAL: RetryAfter
        logger.error(f"Error SmartEdit Rescue: {e}")
        try: await update.callback_query.message.delete()
        except: pass
        try: await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        except Exception: pass

# ==============================================================================
# BIO ENGINE (OPTIMIZADO V13.4 - CRYPTO FACTOR)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_iil(balance: float, refs_count: int, joined_at: float) -> float:
        days_alive = (time.time() - joined_at) / 86400
        if days_alive < 0: days_alive = 0
        act_score = math.log1p(balance) * 0.4
        ref_score = math.log1p(refs_count) * 0.4
        time_score = days_alive * 0.2
        return 1.0 + act_score + ref_score + time_score

    @staticmethod
    def calculate_hsp(node_dict: Dict, iil: float) -> float:
        # HSP = IIL * Rango * Squad * (1 + NFT_Boost)
        rango = node_dict.get("caste", "LARVA")
        mult = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])["hsp_mult"]
        squad_bonus = 0.1 if node_dict.get("squad_id") else 0.0
        nft_bonus = float(node_dict.get("nft_boost", 0.0)) # Tokenomics NFT

        return iil * mult * (1 + squad_bonus + nft_bonus)

    @staticmethod
    def calculate_state(node_data: Dict) -> Dict:
        try:
            model = NodeModel(**node_data)
            node = model.dict()
        except Exception as e:
            logger.error(f"Pydantic Error: {e}")
            node = node_data
            if "honey" not in node: node["honey"] = 0.0

        now = time.time()
        last_regen = node.get("last_regen", now)
        elapsed = now - last_regen
        
        balance = float(node.get("honey", 0))
        refs_count = len(node.get("referrals") or [])
        joined_at = node.get("joined_at", now)
        
        # 1. Calc IIL
        iil_score = BioEngine.calculate_iil(balance, refs_count, joined_at)
        
        # 2. Rango
        poder_total = balance + (refs_count * CONST["BONO_REFERIDO"])
        rango = "LARVA"
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder_total >= data["meta_hive"]:
                rango = nombre
                stats = data
        
        node["caste"] = rango 
        node["max_polen"] = stats["max_energia"]
        
        # 3. HSP
        node["hsp"] = BioEngine.calculate_hsp(node, iil_score)

        # 4. Regen
        if elapsed > 0:
            base_regen_rate = 0.8
            final_regen_rate = base_regen_rate * (node["hsp"] * 0.3) 
            if final_regen_rate < 0.1: final_regen_rate = 0.1
            regen_amount = elapsed * final_regen_rate
            current_polen = float(node.get("polen", 0))
            node["polen"] = min(node["max_polen"], current_polen + int(regen_amount))
            
        node["last_regen"] = now
        node["iil"] = iil_score 
        
        return node

class SecurityEngine:
    @staticmethod
    def generate_access_code() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

async def request_email_protection(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    user = update.effective_user
    lang = user.language_code
    code = SecurityEngine.generate_access_code()
    context.user_data['captcha'] = code
    context.user_data['step'] = 'captcha_wait'
    context.user_data['pending_action'] = reason
    
    txt = (
        f"{get_text(lang, 'protect_title', reason=reason)}\n\n"
        f"{get_text(lang, 'protect_body')}\n"
        f"`{code}`"
    )
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

# ==============================================================================
# STARTUP
# ==============================================================================
async def on_startup(application: Application):
    logger.info("🚀 INICIANDO SISTEMA HIVE V13.5 (SCALABLE & FIXED)")
    await db.connect() 

async def on_shutdown(application: Application):
    await db.close()

# ==============================================================================
# FLUJOS PRINCIPALES
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    ref_id = int(args[0]) if args and args[0].isdigit() else None
    
    try: await db.create_node(user.id, user.first_name, user.username, ref_id)
    except: pass
    
    txt = get_text(lang, "intro_caption")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_enter"), callback_data="intro_step_2")]]
    
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def intro_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = q.from_user.language_code
    await q.answer("...")
    await asyncio.sleep(1.0)
    try: await q.message.delete()
    except: pass

    txt = get_text(lang, "intro_step2")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_status"), callback_data="go_dash")]]
    await q.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    lang = user.language_code
    uid = user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    if context.user_data.get('waiting_combo') and text == context.user_data.get('daily_combo_target'):
        node = await db.get_node(uid)
        bonus = CONST['COMBO_DAILY_MAX'] * random.uniform(0.5, 1.0)
        node['honey'] += bonus
        node['streak'] = node.get('streak', 0) + 5
        await db.save_node(uid, node)
        await update.message.reply_text(get_text(lang, "combo_success", amt=int(bonus)), parse_mode=ParseMode.MARKDOWN)
        context.user_data.pop('waiting_combo', None)
        return

    # WALLET CONNECT
    if context.user_data.get('waiting_wallet'):
        if len(text) > 40: # Validación básica TON
            await db.link_wallet(uid, text)
            await update.message.reply_text("✅ Wallet Linked! Airdrop Ready.")
            context.user_data.pop('waiting_wallet', None)
        else:
            await update.message.reply_text("❌ Invalid TON Address")
        return

    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ OK", callback_data="accept_terms")]]
            await update.message.reply_text("✅ OK", reply_markup=InlineKeyboardMarkup(kb))
        else: await update.message.reply_text("❌ X")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.get_node(uid)
            if node:
                node['honey'] += 15.0 
                await db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🟢 ACCESS SYSTEM", callback_data="go_dash")]]
            await update.message.reply_text(get_text(lang, "email_success"), reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text("⚠️ Email Error")
        return

    try:
        node = await db.get_node(uid)
        if node: await show_dashboard(update, context)
    except: pass

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.callback_query: 
            uid = update.callback_query.from_user.id
            lang = update.callback_query.from_user.language_code
            user = update.callback_query.from_user
        else: 
            uid = update.effective_user.id
            lang = update.effective_user.language_code
            user = update.effective_user
        
        try: await db.create_node(uid, user.first_name, user.username)
        except: pass
        
        node_raw = await db_op(db.get_node, uid)
        if not node_raw: return

        node = BioEngine.calculate_state(node_raw)
        await db_op(db.save_node, uid, node)
        
        rango = node['caste']
        info = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])
        status_msg = get_text(lang, "status_unsafe") if not node.get("email") else get_text(lang, "status_safe")
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        
        hsp = node.get("hsp", 1.0)
        streak = node.get("streak", 0)
        
        bar = render_bar(polen, max_p)
        header = get_text(lang, "dash_header")
        lbl_e = get_text(lang, "lbl_energy")
        lbl_h = get_text(lang, "lbl_honey")
        lbl_hsp = get_text(lang, "hsp_lbl", hsp=hsp)
        lbl_streak = get_text(lang, "streak_lbl", streak=streak)
        lbl_f = get_text(lang, "lbl_feed")
        footer = get_text(lang, "footer_msg")
        live = generate_live_feed(lang)
        
        txt = (
            f"{header} | {info['icono']} **{rango}**\n"
            f"────────────────\n"
            f"{status_msg}\n\n"
            f"{lbl_e}: `{bar}`\n"
            f"{lbl_h}: `{node['honey']:.4f}`\n"
            f"{lbl_hsp} | {lbl_streak} \n\n"
            f"{lbl_f}\n{live}\n\n"
            f"{footer}\n"
            f"────────────────"
        )
        
        kb = [
            [InlineKeyboardButton(get_text(lang, "btn_mine"), callback_data="forage")],
            [InlineKeyboardButton(get_text(lang, "btn_preds"), callback_data="preds"), InlineKeyboardButton(get_text(lang, "btn_combo"), callback_data="combo")],
            [InlineKeyboardButton(get_text(lang, "btn_lb"), callback_data="lb"), InlineKeyboardButton(get_text(lang, "btn_squad"), callback_data="squad")],
            [InlineKeyboardButton(get_text(lang, "btn_wallet"), callback_data="connect_wallet")],
            [InlineKeyboardButton(get_text(lang, "btn_tasks"), callback_data="tasks"), InlineKeyboardButton(get_text(lang, "btn_shop"), callback_data="shop")],
            [InlineKeyboardButton(get_text(lang, "btn_team"), callback_data="team")]
        ]
        await smart_edit(update, txt, InlineKeyboardMarkup(kb))
    except Exception as e: logger.error(f"Dash Error: {e}")

# ==============================================================================
# SUB-MENÚS 
# ==============================================================================

async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    txt = get_text(lang, "wallet_prompt")
    context.user_data['waiting_wallet'] = True
    kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    kb = [
        [InlineKeyboardButton(f"🟢 {get_text(lang, 'green_hive')}", callback_data="v_t1")],
        [InlineKeyboardButton(f"🟡 {get_text(lang, 'gold_hive')} 🔒", callback_data="v_t2")],
        [InlineKeyboardButton(f"🔴 {get_text(lang, 'red_hive')} 🔒", callback_data="v_t3")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    txt = f"{get_text(lang, 'tasks_title')}\n\n{get_text(lang, 'tasks_body')}"
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    
    if (key == "v_t2" or key == "v_t3") and not node.get("email"):
        await request_email_protection(update, context, "TIER ACCESS")
        return

    rol = node.get("caste", "LARVA")
    lvl = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["acceso"]
    
    db_key = "PANAL_VERDE"; req_lvl = 0; dict_key = "green_hive"
    if key == "v_t2": db_key = "PANAL_DORADO"; req_lvl = 2; dict_key = "gold_hive"
    if key == "v_t3": db_key = "PANAL_ROJO"; req_lvl = 3; dict_key = "red_hive"
    
    if lvl < req_lvl:
        msg = get_text(lang, "lock_msg", lvl=req_lvl)
        await q.answer(msg, show_alert=True)
        return
        
    links = FORRAJEO_DB.get(db_key, [])
    kb = []
    for item in links:
        kb.append([InlineKeyboardButton(f"{item['name']}", url=item["url"])])
    kb.append([InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="tasks")])
    title = get_text(lang, dict_key)
    await smart_edit(update, f"📍 **{title}**", InlineKeyboardMarkup(kb))

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    
    limiter = await get_limiter(uid)
    async with limiter:
        try:
            node_raw = await db.get_node(uid)
            node = BioEngine.calculate_state(node_raw)
            
            if node['polen'] < CONST['COSTO_POLEN']:
                await q.answer("⚡ Low Energy", show_alert=True)
                return

            node['polen'] -= CONST['COSTO_POLEN']
            
            streak_mult = CONST['STREAK_BONUS'] ** min(node.get('streak', 0), 10)
            
            # DEFLACIÓN (TOKENOMICS)
            gross_yield = CONST['RECOMPENSA_BASE'] * RANGOS_CONFIG[node['caste']]['bonus_tap'] * node['hsp'] * streak_mult * CONST['HALVING_FACTOR']
            burn_amount = gross_yield * CONST['BURN_RATE_TAP']
            net_yield = gross_yield - burn_amount
            
            node['honey'] += net_yield
            
            now = time.time()
            last = node.get('last_tap', 0)
            if now - last < 15:
                node['streak'] = node.get('streak', 0) + 1
            else:
                node['streak'] = 1 
            
            node['last_tap'] = now
            
            await db.save_node(uid, node)
            await q.answer(f"✅ +{net_yield:.4f} (Burned: {burn_amount:.4f})")
            
            if random.random() < 0.1: await show_dashboard(update, context)
            
        except Exception as e:
            logger.error(f"Forage Error: {e}")
            pass

# --- MENUS V13 ---

async def daily_combo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    combo = generate_daily_combo()
    context.user_data['daily_combo_target'] = combo
    context.user_data['waiting_combo'] = True
    txt = get_text(lang, "daily_combo")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def predictions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    evento = await get_evento_diario()
    context.user_data['active_event'] = evento
    txt = get_text(lang, "predictions", evento=evento['desc'])
    kb = [
        [InlineKeyboardButton("✅ YES", callback_data="pred_yes"), InlineKeyboardButton("❌ NO", callback_data="pred_no")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def prediction_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    await update.callback_query.answer(get_text(lang, "pred_vote_ok"))

async def leaderboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    tops = await db.get_top_hsp(10)
    if not tops:
        top10 = "1. HiveMaster\n2. AlphaNode"
    else:
        top10 = "\n".join([f"{i+1}. {name}: {score:.2f} HSP" for i, (name, score) in enumerate(tops)])
        
    txt = get_text(lang, "leaderboard", top10=top10)
    kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    cell_id = node.get("cell_id") or node.get("enjambre_id")
    
    if cell_id:
        cell = await db.get_cell(cell_id)
        if cell:
            members_count = len(cell.get('members', []))
            txt = f"🐝 **SQUAD ACTIVO**\n👥 Miembros: {members_count}\n⚡ Boost HSP: +10%"
            kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
            await smart_edit(update, txt, InlineKeyboardMarkup(kb))
            return

    txt = f"{get_text(lang, 'squad_none_title')}\n\n{get_text(lang, 'squad_none_body')}"
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_create_squad", cost=CONST['COSTO_ENJAMBRE']), callback_data="mk_cell")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    
    if not node.get("email"):
        await request_email_protection(update, context, "SQUAD")
        return
        
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cell_name = f"Hive-{random.randint(100,999)}"
        cell_id = await db.create_cell(uid, cell_name)
        if cell_id:
            node['enjambre_id'] = cell_id
            node['cell_id'] = cell_id
            await db.save_node(uid, node)
            await q.answer("✅"); await squad_menu(update, context)
        else: await q.answer("❌ Error DB", show_alert=True)
    else: await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    if not node.get("email"):
        await request_email_protection(update, context, "SHOP")
        return
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_buy_prem", price=CONST['PRECIO_ACELERADOR']), callback_data="buy_premium")],
        [InlineKeyboardButton(get_text(lang, "btn_buy_energy", cost=CONST['COSTO_RECARGA']), callback_data="buy_energy")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    txt = f"{get_text(lang, 'shop_title')}\n\n{get_text(lang, 'shop_body')}"
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.save_node(uid, node)
        await q.answer("⚡ OK"); await show_dashboard(update, context)
    else: await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    txt = get_text(lang, "pay_txt", price=CONST['PRECIO_ACELERADOR'], wallet=CRYPTO_WALLET_USDT)
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_paypal"), url=LINK_PAYPAL_HARDCODED)],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="shop")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    if not node.get("email"):
        await request_email_protection(update, context, "EXPAND")
        return
    link = f"https://t.me/{context.bot.username}?start={uid}"
    share_url = f"https://t.me/share/url?url={link}"
    txt = get_text(lang, "team_body", bonus=CONST['BONO_REFERIDO'], link=link)
    title = get_text(lang, "team_title")
    kb = [[InlineKeyboardButton("📤 SHARE", url=share_url)], [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, f"{title}\n\n{txt}", InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    lang = q.from_user.language_code

    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await smart_edit(update, get_text(lang, "email_prompt"), InlineKeyboardMarkup([]))
        return

    actions = {
        "intro_step_2": intro_step_2,
        "go_dash": show_dashboard, 
        "forage": forage_action, 
        "tasks": tasks_menu,
        "squad": squad_menu, "mk_cell": create_squad_logic,
        "shop": shop_menu, "buy_energy": buy_energy, "buy_premium": buy_premium, 
        "team": team_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "v_t1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "v_t2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "v_t3", c),
        "combo": daily_combo_menu,
        "preds": predictions_menu,
        "pred_yes": prediction_vote,
        "pred_no": prediction_vote,
        "lb": leaderboard_menu,
        "connect_wallet": wallet_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 Node Purged")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("V13.5 SCALABLE & FIXED")
async def broadcast_cmd(u, c): pass
