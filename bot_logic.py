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
# 🐝 THE ONE HIVE: V8.2 (STABILITY FIX - NO CRASHES)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# --- IDENTIDAD VISUAL ---
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ESCASEZ ---
CONST = {
    "COSTO_POLEN": 10,        # Costo Energía
    "RECOMPENSA_BASE": 0.05,  # Emisión MUY baja (Escasez)
    "DECAY_OXIGENO": 4.0,     # Penalización
    "COSTO_ENJAMBRE": 100,    # Barrera social
    "COSTO_RECARGA": 50,      # Quema de tokens
    "BONO_REFERIDO": 500,     # PODER (Viralidad)
    "PRECIO_ACELERADOR": 9.99 # USD (Monetización)
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 200,  "bonus_tap": 1.0, "icono": "🐛", "acceso": 1},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 400,  "bonus_tap": 1.1, "icono": "🐝", "acceso": 1},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 800,  "bonus_tap": 1.2, "icono": "🔭", "acceso": 2},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 1500, "bonus_tap": 1.5, "icono": "🛡️", "acceso": 3},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑", "acceso": 3}
}

# --- PANALES ACTIVOS ---
FORRAJEO_DB = {
    "TIER_1": [ # ABIERTO
        {"name": "⚡ ACCIÓN PATROCINADA", "url": "https://t.me/AnuncianteDeTurno"}, 
        {"name": "📺 Timebucks", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"}
    ],
    "TIER_2": [ # BLOQUEADO
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"}
    ],
    "TIER_3": [ # BLOQUEADO
        {"name": "🔥 ByBit (+20 USDT)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🏦 Nexo (Yield)", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"}
    ]
}

# ==============================================================================
# UTILIDADES & VISUALES
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
        return f"Evolución: Faltan {falta:,.2f} pts"
    return "ORGANISMO PERFECCIONADO"

def generate_live_feed() -> str:
    eventos = [
        "completó una acción", "desbloqueó acceso", "sintetizó néctar", 
        "aseguró su posición", "entró a la colmena", "subió de rango",
        "⚠️ Parámetro ajustado por tráfico", "🔥 Nodo destacado por actividad",
        "⏳ Rebalance inminente detectado"
    ]
    if random.random() < 0.3: 
        return f"SYSTEM: {random.choice(eventos[6:])}"
    minutos = random.randint(1, 9)
    return f"• Un miembro {random.choice(eventos[:6])} hace {minutos} min"

def get_viral_share_text(uid: int, bot_username: str) -> str:
    link = f"https://t.me/{bot_username}?start={uid}"
    variantes = [
        f"Esto no parece un airdrop.\nEstán midiendo influencia real.\nEntré antes del ajuste.\n\n{link}",
        f"No está abierto oficialmente.\nTodavía están calibrando el sistema.\nDespués no se entra igual.\n\n{link}",
        f"Hamster regala números.\nEsto mide comportamiento.\nNo es para todos.\n\n{link}"
    ]
    return random.choice(variantes)

async def smart_edit(update: Update, text: str, reply_markup: InlineKeyboardMarkup):
    """
    CORRECCIÓN DE CRASH: Si el Markdown falla (por guiones bajos u otros caracteres),
    lo reenvía como texto plano para que el usuario nunca se quede trabado.
    """
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        # Fallback 1: Intentar borrar y enviar nuevo con Markdown
        try:
            await update.callback_query.message.delete()
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            # Fallback 2 (SEGURIDAD TOTAL): Enviar sin formato si el Markdown falla
            try:
                clean_text = text.replace("*", "").replace("_", " ") # Limpiar caracteres problemáticos
                await update.callback_query.message.reply_text(clean_text, reply_markup=reply_markup)
            except: pass

async def request_email_protection(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    code = SecurityEngine.generate_access_code()
    context.user_data['captcha'] = code
    context.user_data['step'] = 'captcha_wait'
    context.user_data['pending_action'] = reason
    
    txt = (
        f"⚠️ **ACCIÓN RESTRINGIDA: {reason}**\n\n"
        "Tu nodo no está protegido. Si pierdes acceso, pierdes tu progreso.\n\n"
        "🔐 **VINCULAR NODO AHORA**\n"
        f"Copia este código de seguridad:\n`{code}`"
    )
    kb = []
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

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
        poder = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango = "LARVA" 
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder >= data["meta_hive"]:
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
# FLUJO DE INICIO
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    try: await db.db.create_node(user.id, user.first_name, user.username, ref)
    except: pass
    
    txt = (
        "Bienvenido a The One Hive.\n\n"
        "No es un juego.\n"
        "No es un airdrop.\n"
        "No es inversión.\n\n"
        "Es una colmena activa donde cada acción deja rastro.\n"
        "Tu progreso depende de lo que hacés, no de lo que prometen.\n\n"
        "Explorá. El sistema se adapta."
    )
    kb = [[InlineKeyboardButton("👉 Entrar a la Colmena", callback_data="intro_step_2")]]
    
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def intro_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Conectando...")
    try: await context.bot.send_chat_action(chat_id=q.message.chat_id, action=ChatAction.TYPING)
    except: pass
    await asyncio.sleep(2)
    try: await q.message.delete()
    except: pass

    txt = (
        "La colmena no crece de golpe.\n"
        "Crece por constancia.\n\n"
        "Algunos entran temprano.\n"
        "Otros llegan cuando ya está llena."
    )
    kb = [[InlineKeyboardButton("👉 Ver mi estado", callback_data="go_dash")]]
    await q.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ CONFIRMAR Y PROTEGER", callback_data="accept_terms")]]
            await update.message.reply_text(
                "🛡️ **PROTOCOLO DE PROTECCIÓN**\n\n"
                "Al vincular tu nodo, aceptas recibir:\n"
                "• Alertas críticas de seguridad\n"
                "• Eventos del Enjambre\n"
                "• Oportunidades exclusivas\n\n"
                "¿Confirmas?",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
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
            node['honey'] += 10.0
            await db.db.save_node(uid, node)
            
            action = context.user_data.get('pending_action', 'General')
            
            kb = [[InlineKeyboardButton("🟢 VOLVER AL SISTEMA", callback_data="go_dash")]]
            await update.message.reply_text(
                f"✅ **NODO BLINDADO**\n\n"
                f"Acceso '{action}' desbloqueado.\n"
                "Tu progreso está seguro.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text("⚠️ Email inválido.")
        return

    try:
        node = await db.db.get_node(uid)
        if node: await show_dashboard(update, context)
    except: pass

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
        
        status_msg = "⚠️ NODO NO PROTEGIDO" if not node.get("email") else "✅ NODO SEGURO"
        
        txt = (
            f"🏰 **THE ONE HIVE** | {info['icono']} **{rango}**\n"
            f"────────────────\n"
            f"Estado: {status_msg}\n\n"
            f"⚡ **Energía:** `{bar}` ({polen}/{max_p})\n"
            f"🍯 **Néctar:** `{node['honey']:.4f}`\n\n"
            f"📊 **Log del Sistema:**\n"
            f"{live_activity}\n\n"
            f"📝 _Lo que hagas hoy importa más que lo que hagas mañana._\n"
            f"────────────────"
        )
        
        kb = [
            [InlineKeyboardButton("⚡ MINAR (TAP)", callback_data="forage")],
            [InlineKeyboardButton("🟢 TAREAS", callback_data="tasks"), InlineKeyboardButton("🧬 EVOLUCIÓN", callback_data="rank_info")],
            [InlineKeyboardButton("🐝 COLMENA", callback_data="squad"), InlineKeyboardButton("👥 INVITAR", callback_data="team")],
            [InlineKeyboardButton("🚀 ESTABILIZAR NODO ($)", callback_data="shop")]
        ]
        await smart_edit(update, txt, InlineKeyboardMarkup(kb))
            
    except Exception as e:
        logger.error(f"Dash Error: {e}")

# ==============================================================================
# SUB-MENÚS
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 ACCIÓN RÁPIDA (Abierto)", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 EXPLORACIÓN (Bloqueado 🔒)", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 PATROCINADA (Prioridad 🔒)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "📡 **MINERÍA DE DATOS**\n\n"
        "Selecciona zona de trabajo:\n"
        "• **Verde:** Baja recompensa, abierto a todos.\n"
        "• **Amarillo:** High Yield (Requiere Explorador).\n"
        "• **Rojo:** VIP Access (Requiere Guardián).\n\n"
        "⚠️ *La dificultad aumenta con el tiempo.*"
    )
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if (key == "v_t2" or key == "v_t3") and not node.get("email"):
        await request_email_protection(update, context, "Acceso a Tareas Avanzadas")
        return

    rol = node.get("caste", "LARVA")
    lvl = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["acceso"]
    
    db_key = "TIER_1"; req_lvl = 1; req_pts = 0
    if key == "v_t2": db_key = "TIER_2"; req_lvl = 2; req_pts = 5000
    if key == "v_t3": db_key = "TIER_3"; req_lvl = 3; req_pts = 20000
    
    if lvl < req_lvl:
        balance_actual = node.get("honey", 0) + (len(node.get("referrals", [])) * CONST["BONO_REFERIDO"])
        falta = req_pts - balance_actual
        invites = math.ceil(falta / CONST["BONO_REFERIDO"])
        
        await q.answer(
            f"🔒 ACCESO DENEGADO\n\nReq: {req_pts} Pts\nTienes: {balance_actual:.0f}\n\n👉 Invita a {invites} personas.", 
            show_alert=True
        )
        return
        
    links = FORRAJEO_DB.get(db_key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    # CORRECCIÓN DE BUG: Reemplazamos _ por espacio en el título visual para evitar error de Markdown
    display_title = db_key.replace("_", " ") 
    await smart_edit(update, f"📍 **ZONA ACTIVA: {display_title}**\n\nCompleta para validar.", InlineKeyboardMarkup(kb))

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    refs = len(node.get("referrals", []))
    honey = node.get("honey", 0)
    poder = honey + (refs * CONST["BONO_REFERIDO"])
    
    txt = (
        f"🧬 **ESTADO EVOLUTIVO**\n\n"
        f"🍯 Saldo Real: **{honey:.4f}**\n"
        f"👥 Influencia: **{refs} x 500 = {refs*500}**\n"
        f"⚡ **PODER TOTAL: {poder:.2f}**\n\n"
        "**REQUISITOS:**\n"
        "🐛 LARVA: 0\n"
        "🐝 OBRERO: 1,000\n"
        "🔭 EXPLORADOR: 5,000\n"
        "🛡️ GUARDIÁN: 20,000\n"
        "👑 REINA: 100,000"
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🐝 **COLMENA: {cell['name']}**\n👥 Miembros: {len(cell['members'])}\n\nLa colmena optimiza la extracción."
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = "⚠️ **NODO SIN COLMENA**\n\nUn nodo aislado mina lento.\nForma una estructura para sobrevivir."
        kb = [[InlineKeyboardButton(f"➕ FORMAR (Costo: {CONST['COSTO_ENJAMBRE']} HIVE)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if not node.get("email"):
        await request_email_protection(update, context, "Creación de Colmena")
        return

    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Estructura Iniciada"); await squad_menu(update, context)
    else: await q.answer(f"❌ Necesitas {CONST['COSTO_ENJAMBRE']} HIVE", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if not node.get("email"):
        await request_email_protection(update, context, "Acceso a Tienda Segura")
        return

    kb = [
        [InlineKeyboardButton(f"🚀 ESTABILIZADOR PREMIUM (${CONST['PRECIO_ACELERADOR']})", callback_data="buy_premium")],
        [InlineKeyboardButton("🔋 RECARGA ENERGÍA (50 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "💎 **ESTABILIZACIÓN DE NODO**\n\n"
        "Los nodos inestables pierden eficiencia con el tiempo.\n"
        "La Estabilización Premium asegura:\n\n"
        "✅ **Prioridad de Red:** Regeneración x2.\n"
        "✅ **Blindaje VIP:** Soporte preferencial.\n"
        "✅ **Eficiencia:** Sin tiempos muertos.\n\n"
        "Asegura tu posición antes del próximo evento."
    )
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Restaurado"); await show_dashboard(update, context)
    else: await q.answer(f"❌ Necesitas {CONST['COSTO_RECARGA']} Tokens", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = f"🚀 **ACTIVAR ESTABILIZADOR**\n\nEnvía $9.99 USDT (TRC20) a:\n`{CRYPTO_WALLET_USDT}`\n\n(Envía comprobante al admin)"
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if not node.get("email"):
        await request_email_protection(update, context, "Generación de Enlaces Únicos")
        return

    share_text = get_viral_share_text(uid, context.bot.username)
    share_url = f"https://t.me/share/url?url={share_text}"
    
    txt = f"👥 **EXPANSIÓN DE RED**\n\n1 Referido = 500 Puntos de Poder.\nUsa este enlace único:"
    kb = [[InlineKeyboardButton("📤 EXPANDIR NODO", url=share_url)], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        
        # SUGERENCIA SUAVE DE EMAIL (NO BLOQUEANTE)
        if node['honey'] > 20 and not node.get("email") and random.random() < 0.1:
            pass # Solo lógica interna, no interrumpimos el flow

        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Energía baja.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        yield_amt = CONST['RECOMPENSA_BASE'] * RANGOS_CONFIG[node['caste']]['bonus_tap']
        node['honey'] += yield_amt
        
        await db.db.save_node(uid, node)
        await q.answer(f"✅ +{yield_amt:.4f}")
        if random.random() < 0.2: await show_dashboard(update, context)
    except Exception: pass

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "intro_step_2": await intro_step_2(update, context); return
    
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
async def help_cmd(u, c): await u.message.reply_text("V8.2 Stable")
async def broadcast_cmd(u, c): pass
