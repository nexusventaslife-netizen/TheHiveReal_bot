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
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from loguru import logger
import database as db 
from email_validator import validate_email, EmailNotValidError

# ==============================================================================
# 🐝 THE ONE HIVE: V9.0 (LAUNCH READY BLUEPRINT)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# --- IDENTIDAD VISUAL ---
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA ---
CONST = {
    "COSTO_POLEN": 10,        
    "RECOMPENSA_BASE": 0.05,  # Emisión baja (Escasez percibida)
    "DECAY_OXIGENO": 4.0,     
    "COSTO_ENJAMBRE": 100,    
    "COSTO_RECARGA": 50,      
    "BONO_REFERIDO": 500,     # Poder de Rango
    "PRECIO_ACELERADOR": 9.99,
    "TRIGGER_EMAIL_HONEY": 50 # Gatillo emocional de protección
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 200,  "bonus_tap": 1.0, "icono": "🐛", "acceso": 0},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 400,  "bonus_tap": 1.1, "icono": "🐝", "acceso": 1},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 800,  "bonus_tap": 1.2, "icono": "🔭", "acceso": 2},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 1500, "bonus_tap": 1.5, "icono": "🛡️", "acceso": 3},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑", "acceso": 3}
}

# --- MENSAJES VIRALES (ESTRATEGIA FILTRACIÓN) ---
VIRAL_TEXTS = [
    "Esto no es un airdrop. No es inversión.\nEstán midiendo influencia real.\nEntré antes del ajuste.\n\n{link}",
    "No debería compartir esto.\nEl sistema busca nodos orgánicos, no bots.\nAsegura tu posición antes del bloque 100k.\n\n{link}",
    "Hamster infló números.\nEsto mide comportamiento real.\nNo es para todos.\n\n{link}",
    "No está abierto oficialmente.\nTodavía están calibrando el sistema.\nDespués no se entra igual.\n\n{link}"
]

# --- PANALES ACTIVOS (MONETIZACIÓN) ---
FORRAJEO_DB = {
    "TIER_1": [ 
        {"name": "⚡ PRIORIDAD DE RED", "url": "https://t.me/AnuncianteDeTurno"}, 
        {"name": "📺 Timebucks", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"}
    ],
    "TIER_2": [ 
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"}
    ],
    "TIER_3": [ 
        {"name": "🔥 ByBit (+20 USDT)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"}
    ]
}

# ==============================================================================
# UTILIDADES & NARRATIVA
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
        return f"Siguiente Fase: -{falta:,.0f} pts"
    return "JERARQUÍA MÁXIMA"

def generate_live_feed() -> str:
    """EVENT ENGINE: Mensajes de sistema vivo y ambiguo."""
    eventos_sistema = [
        "⚠️ Parámetro del enjambre ajustado",
        "⏳ Ventana alfa activa",
        "🔒 Acceso temprano reducido",
        "⚖️ Rebalance interno ejecutado",
        "📡 Señal comportamental registrada"
    ]
    
    if random.random() < 0.25: # 25% de mensajes son del sistema (FOMO)
        return f"SYSTEM: {random.choice(eventos_sistema)}"
        
    acciones = ["validó nodo", "sintetizó bloque", "aseguró posición", "expandió red"]
    minutos = random.randint(1, 7)
    return f"• Nodo anónimo {random.choice(acciones)} hace {minutos} min"

async def smart_edit(update: Update, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    except BadRequest as e:
        if "message is not modified" in str(e): return
        try:
            await update.callback_query.message.delete()
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        except: pass

async def request_email_protection(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """
    Pide email con la narrativa de PROTECCIÓN y CONSENTIMIENTO.
    """
    code = SecurityEngine.generate_access_code()
    context.user_data['captcha'] = code
    context.user_data['step'] = 'captcha_wait'
    context.user_data['pending_action'] = reason
    
    txt = (
        f"⚠️ **ACCIÓN INTERRUMPIDA: {reason}**\n\n"
        "Tu nodo opera en modo volátil. El sistema requiere estabilidad.\n"
        "Protege tu progreso ahora para continuar.\n\n"
        f"Copia tu llave de seguridad:\n`{code}`"
    )
    # Sin botones para forzar el flujo
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

# ==============================================================================
# BIO ENGINE
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0)
        refs = len(node.get("referrals", []))
        poder_total = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango = "LARVA"
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder_total >= data["meta_hive"]:
                rango = nombre
                stats = data
        
        node["caste"] = rango 
        node["max_polen"] = stats["max_energia"]
        
        if elapsed > 0:
            regen = elapsed * 0.8 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    @staticmethod
    def generate_access_code() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# SECUENCIA DE INICIO (DIRECTA)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    try: await db.db.create_node(user.id, user.first_name, user.username, ref)
    except: pass
    
    # INTRO DEL BOT (FILTRO DE CALIDAD)
    txt = (
        "Bienvenido a The One Hive.\n\n"
        "No es un juego.\n"
        "No es un airdrop.\n"
        "No es inversión.\n\n"
        "Es un sistema activo donde cada acción deja rastro.\n"
        "Tu progreso depende de tu comportamiento, no de promesas.\n\n"
        "Explorá. El sistema se adapta."
    )
    kb = [[InlineKeyboardButton("👉 Entrar a la Colmena", callback_data="go_dash")]]
    
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# DASHBOARD CENTRAL
# ==============================================================================

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.callback_query: uid = update.callback_query.from_user.id
        else: uid = update.effective_user.id

        user = update.effective_user
        try: await db.db.create_node(user.id, user.first_name, user.username, None)
        except: pass
        
        node = await db.db.get_node(uid)
        node = BioEngine.calculate_state(node)
        await db.db.save_node(uid, node)
        
        rango = node['caste']
        info = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])
        live_activity = generate_live_feed()
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        # STATUS DE RIESGO (GATILLO EMOCIONAL)
        if not node.get("email"):
            if node['honey'] >= CONST['TRIGGER_EMAIL_HONEY'] or rango != "LARVA":
                status_msg = "⚠️ PROGRESO EN RIESGO (Asegurar ahora)"
            else:
                status_msg = "⚪ MODO INVITADO"
        else:
            status_msg = "🟢 NODO BLINDADO"
        
        txt = (
            f"🏰 **THE ONE HIVE** | {info['icono']} **{rango}**\n"
            f"────────────────\n"
            f"Estado: {status_msg}\n\n"
            f"⚡ Energía: `{bar}`\n"
            f"🍯 Néctar: `{node['honey']:.4f}`\n\n"
            f"📊 **Feed:**\n{live_activity}\n\n"
            f"📝 _La emisión es limitada. El acceso es escaso._\n"
            f"────────────────"
        )
        
        kb = [
            [InlineKeyboardButton("⚡ MINAR (TAP)", callback_data="forage")],
            [InlineKeyboardButton("🟢 ACTIVIDAD", callback_data="tasks"), InlineKeyboardButton("🧬 EVOLUCIÓN", callback_data="rank_info")],
            [InlineKeyboardButton("🐝 COLMENA", callback_data="squad"), InlineKeyboardButton("👥 EXPANDIR", callback_data="team")],
            [InlineKeyboardButton("🛡️ ESTABILIZAR NODO ($)", callback_data="shop")]
        ]
        await smart_edit(update, txt, InlineKeyboardMarkup(kb))
            
    except Exception as e:
        logger.error(f"Dash Error: {e}")

# ==============================================================================
# FLUJO DE PROTECCIÓN (EMAIL & CONSENTIMIENTO)
# ==============================================================================

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    # CAPTCHA -> CONSENTIMIENTO LEGAL
    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ VINCULAR Y ACEPTAR", callback_data="accept_terms")]]
            # TEXTO LEGAL ÓPTIMO
            await update.message.reply_text(
                "📜 **PROTOCOLO DE VINCULACIÓN**\n\n"
                "Al vincular tu email aceptás recibir:\n"
                "– Actualizaciones del enjambre\n"
                "– Eventos críticos del sistema\n"
                "– Acciones patrocinadas relevantes\n\n"
                "Esto asegura tu nodo y permite comunicación directa.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Llave incorrecta.")
        return

    # EMAIL -> DESBLOQUEO DE ACCIÓN
    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 15.0 # Reward por vincular
            await db.db.save_node(uid, node)
            
            action_name = context.user_data.get('pending_action', 'Acceso')
            
            kb = [[InlineKeyboardButton("🟢 CONTINUAR", callback_data="go_dash")]]
            await update.message.reply_text(
                f"✅ **NODO ASEGURADO**\n\n"
                f"Acceso '{action_name}' concedido.\n"
                "Tu progreso ahora es permanente.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text("⚠️ Formato inválido.")
        return

    try:
        node = await db.db.get_node(uid)
        if node: await show_dashboard(update, context)
    except: pass

# ==============================================================================
# ACCIONES PRINCIPALES
# ==============================================================================

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        
        # GATILLO DE PROGRESO: Si tiene mucho saldo y NO tiene email -> Aviso sutil (no bloqueo)
        if node['honey'] > CONST['TRIGGER_EMAIL_HONEY'] and not node.get("email"):
            # Aquí podríamos mandar un toast, pero por ahora solo dejamos que el Dash avise "En Riesgo"
            pass

        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Energía inestable. Espera o estabiliza.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        
        yield_amt = CONST['RECOMPENSA_BASE'] * RANGOS_CONFIG[node['caste']]['bonus_tap']
        node['honey'] += yield_amt
        
        await db.db.save_node(uid, node)
        await q.answer(f"✅ Minado: +{yield_amt:.4f}")
        if random.random() < 0.2: await show_dashboard(update, context)
    except Exception: pass

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 ACCIÓN RÁPIDA (Abierto)", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 EXPLORACIÓN (Bloqueado 🔒)", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 PATROCINADA (Prioridad 🔒)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "📡 **SEÑALES DE COMPORTAMIENTO**\n\n"
        "Tu actividad valida el nodo.\n\n"
        "🟢 **Verde:** Baja señal, acceso libre.\n"
        "🟡 **Amarillo:** Señal media (Requiere Explorador).\n"
        "🔴 **Rojo:** Alta prioridad (Requiere Guardián).\n\n"
        "⚠️ *Completar tareas falsas degrada tu nodo.*"
    )
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    # TRIGGER 1: TIER 2+ REQUIERE EMAIL (ANTES DE MONETIZAR)
    if (key == "v_t2" or key == "v_t3") and not node.get("email"):
        await request_email_protection(update, context, "Acceso a Tareas Avanzadas")
        return

    rol = node.get("caste", "LARVA")
    lvl = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["acceso"]
    
    db_key = "TIER_1"; req_lvl = 0
    if key == "v_t2": db_key = "TIER_2"; req_lvl = 2; req_pts = 5000
    if key == "v_t3": db_key = "TIER_3"; req_lvl = 3; req_pts = 20000
    
    if lvl < req_lvl:
        balance_actual = node.get("honey", 0) + (len(node.get("referrals", [])) * CONST["BONO_REFERIDO"])
        falta = req_pts - balance_actual
        invites = math.ceil(falta / CONST["BONO_REFERIDO"])
        await q.answer(f"🔒 DENEGADO. Faltan {falta:.0f} pts. Invita a {invites} personas.", show_alert=True)
        return
        
    links = FORRAJEO_DB.get(db_key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    await smart_edit(update, f"📍 **NODO ACTIVO: {db_key}**\n\nCompleta para validar.", InlineKeyboardMarkup(kb))

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    refs = len(node.get("referrals", []))
    honey = node.get("honey", 0)
    poder = honey + (refs * CONST["BONO_REFERIDO"])
    
    txt = (
        f"🧬 **ESTRUCTURA DE NODO**\n\n"
        f"🍯 Saldo Minado: **{honey:.4f}**\n"
        f"👥 Influencia: **{refs} x 500 = {refs*500} pts**\n"
        f"⚡ **PODER TOTAL: {poder:.2f}**\n\n"
        "**ESCALAFÓN:**\n"
        "🐛 LARVA: 0\n"
        "🐝 OBRERO: 1,000\n"
        "🔭 EXPLORADOR: 5,000\n"
        "🛡️ GUARDIÁN: 20,000\n"
        "👑 REINA: 100,000"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TRIGGER 2: COLMENA REQUIERE EMAIL
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🐝 **ENJAMBRE ACTIVO: {cell['name']}**\n👥 Nodos: {len(cell['members'])}\n🔥 Sinergia: ACTIVA"
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = "⚠️ **NODO AISLADO**\n\nLa minería individual es ineficiente.\nForma un clúster para potenciar la señal."
        kb = [[InlineKeyboardButton(f"➕ FORMAR CLÚSTER ({CONST['COSTO_ENJAMBRE']} HIVE)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if not node.get("email"):
        await request_email_protection(update, context, "Creación de Colmena")
        return

    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Cluster-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Clúster Iniciado"); await squad_menu(update, context)
    else: await q.answer("❌ HIVE Insuficiente", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TRIGGER 3: COMPRA REQUIERE EMAIL
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if not node.get("email"):
        await request_email_protection(update, context, "Acceso a Estabilización")
        return

    kb = [
        [InlineKeyboardButton(f"🛡️ ESTABILIZAR NODO (${CONST['PRECIO_ACELERADOR']})", callback_data="buy_premium")],
        [InlineKeyboardButton("🔋 RECARGA EMERGENCIA (50 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "🛡️ **ESTABILIZACIÓN DE NODO (PREMIUM)**\n\n"
        "El sistema es lento a propósito.\n"
        "Los nodos no estabilizados pierden eficiencia.\n\n"
        "**Al estabilizar ($9.99):**\n"
        "✅ Evitas degradación de energía.\n"
        "✅ Prioridad de señal en la red.\n"
        "✅ Acceso a eventos cerrados.\n\n"
        "No compras rango. Compras control de riesgo."
    )
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Energía inyectada"); await show_dashboard(update, context)
    else: await q.answer(f"❌ Necesitas {CONST['COSTO_RECARGA']} HIVE", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = f"🛡️ **PROTOCOLO DE ESTABILIZACIÓN**\n\nEnvía ${CONST['PRECIO_ACELERADOR']} USDT (TRC20) a:\n`{CRYPTO_WALLET_USDT}`\n\n(Envía comprobante al admin para activar)"
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    # TRIGGER 4: VIRALIDAD REQUIERE EMAIL (FILTRO ANTIBOT)
    if not node.get("email"):
        await request_email_protection(update, context, "Generación de Enlace Único")
        return

    link = f"https://t.me/{context.bot.username}?start={uid}"
    share_text = random.choice(VIRAL_TEXTS).format(link=link)
    share_url = f"https://t.me/share/url?url={share_text}"
    
    txt = f"👥 **EXPANSIÓN DE RED**\n\n1 Referido = 500 Puntos de Influencia.\nLa forma más rápida de evolucionar.\n\n🔗 Enlace de Nodo:\n`{link}`"
    kb = [[InlineKeyboardButton("📤 INYECTAR EN LA RED", url=share_url)], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await smart_edit(update, "✅ Confirma con tu **EMAIL**:", InlineKeyboardMarkup([]))
        return

    actions = {
        "go_dash": show_dashboard, "forage": forage_action, "tasks": tasks_menu,
        "rank_info": rank_info_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "v_t1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "v_t2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "v_t3", c),
        "squad": squad_menu, "mk_cell": create_squad_logic,
        "shop": shop_menu, "buy_energy": buy_energy, "buy_premium": buy_premium, 
        "team": team_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("V9.0 Launch Ready")
async def broadcast_cmd(u, c): pass
