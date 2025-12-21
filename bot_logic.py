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
from loguru import logger
import database as db 
from email_validator import validate_email, EmailNotValidError

# ==============================================================================
# 🐝 THE ONE HIVE: GLOBAL LAUNCH MASTER (V7.2 STABLE)
# ==============================================================================

logger = logging.getLogger("HiveMind")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# --- IDENTIDAD VISUAL ---
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA (DÍA 0) ---
CONST = {
    "COSTO_POLEN": 10,        # Costo Energía
    "RECOMPENSA_BASE": 0.50,  # Emisión inicial
    "DECAY_OXIGENO": 4.0,     # Presión de inactividad
    "COSTO_ENJAMBRE": 100,    # Barrera social
    "COSTO_RECARGA": 200,     # Prioridad
    "BONO_REFERIDO": 500,     # Incentivo Viral
    "PRECIO_ACELERADOR": 9.99 # Monetización
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 300,  "bonus_tap": 0.8, "icono": "🐛", "acceso": 0},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 500,  "bonus_tap": 1.0, "icono": "🐝", "acceso": 1},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 1000, "bonus_tap": 1.2, "icono": "🔭", "acceso": 2},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 2000, "bonus_tap": 1.5, "icono": "🛡️", "acceso": 3},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑", "acceso": 3}
}

# --- PANALES ACTIVOS (MONETIZACIÓN) ---
FORRAJEO_DB = {
    "TIER_1": [ 
        {"name": "⚡ ACCIÓN PATROCINADA (Prioridad)", "url": "https://t.me/AnuncianteDeTurno"}, 
        {"name": "📺 Timebucks (Video)", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC (Click)", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "💸 FreeCash (Rápido)", "url": "https://freecash.com/r/XYN98"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"}
    ],
    "TIER_2": [ 
        {"name": "🐝 Honeygain (Pasivo)", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810"},
        {"name": "🌱 SproutGigs", "url": "https://sproutgigs.com/?a=83fb1bf9"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"}
    ],
    "TIER_3": [ 
        {"name": "🔥 ByBit (+20 USDT)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🏦 Nexo (Yield)", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"},
        {"name": "🆗 OKX", "url": "https://www.okx.com/join/PANDORA"}
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
        return f"Evolución: Faltan {falta:,.0f}"
    return "ORGANISMO PERFECCIONADO"

def generate_live_feed() -> str:
    acciones = ["completó una acción", "desbloqueó acceso", "sintetizó néctar", "aseguró su posición", "entró a la colmena", "subió de rango"]
    minutos = random.randint(1, 9)
    return f"• Un miembro {random.choice(acciones)} hace {minutos} min"

# ==============================================================================
# MOTOR LÓGICO (BIO ENGINE)
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0)
        refs = len(node.get("referrals", []))
        poder = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango = "OBRERO"
        stats = RANGOS_CONFIG["OBRERO"]
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
    def analyze_entropy(timestamps: List[float]) -> Tuple[float, str]:
        if len(timestamps) < 5: return 1.0, ""
        deltas = [timestamps[i]-timestamps[i-1] for i in range(1,len(timestamps))]
        try:
            cv = statistics.stdev(deltas) / statistics.mean(deltas)
        except: return 1.0, ""
        if cv < 0.05: return 0.1, "🚫 ANOMALÍA"
        return 1.0, "✅"

    @staticmethod
    def generate_access_code() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

# ==============================================================================
# SECUENCIA DE INICIO (CORREGIDA PARA EVITAR CRASH)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref = int(args[0]) if args and args[0].isdigit() else None
    
    try: await db.db.create_node(user.id, user.first_name, user.username, ref)
    except: pass
    
    node = await db.db.get_node(user.id)
    if node and node.get("email"):
        await show_dashboard(update, context)
        return

    # 1. MISTERIO (FOTO)
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
    # SOLUCIÓN DEL ERROR: Usamos reply_text en vez de edit_text sobre la foto
    q = update.callback_query
    await q.answer("Conectando...")
    
    # Pausa dramática
    try: await context.bot.send_chat_action(chat_id=q.message.chat_id, action=ChatAction.TYPING)
    except: pass
    await asyncio.sleep(3) 
    
    # 2. VALIDACIÓN (NUEVO MENSAJE DE TEXTO)
    txt = (
        "La colmena no crece de golpe.\n"
        "Crece por constancia.\n\n"
        "Algunos entran temprano.\n"
        "Otros llegan cuando ya está llena."
    )
    kb = [[InlineKeyboardButton("👉 Ver mi estado", callback_data="start_validation")]]
    # AQUÍ ESTÁ EL ARREGLO:
    await q.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def start_validation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 3. CAPTCHA
    q = update.callback_query
    code = SecurityEngine.generate_access_code()
    context.user_data['captcha'] = code
    context.user_data['step'] = 'captcha_wait'
    
    # Editar el mensaje de texto anterior es seguro
    await q.message.edit_text(
        f"🔐 **VALIDACIÓN DE HUMANIDAD**\n\n"
        f"Copia este código para sincronizar:\n`{code}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    # PASO A: VERIFICAR CAPTCHA -> OPT-IN
    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ ACEPTO Y ENTRO", callback_data="accept_terms")]]
            await update.message.reply_text(
                "📡 **PROTOCOLO FINAL**\n\n"
                "Para ingresar, debes aceptar recibir actualizaciones críticas, ofertas del Enjambre y propaganda oficial.\n\n"
                "¿Confirmas?",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Código incorrecto.")
        return

    # PASO B: EMAIL -> DASHBOARD
    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            node = await db.db.get_node(uid)
            node['honey'] += 100.0
            node['caste'] = "OBRERO"
            await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🟢 IR A MI ESTADO", callback_data="go_dash")]]
            await update.message.reply_text(
                "✅ **SISTEMA SINCRONIZADO**\n\n"
                "Tu rastro comienza ahora.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text("⚠️ Email inválido.")
        return

    try:
        node = await db.db.get_node(uid)
        if node and node.get("email"): await show_dashboard(update, context)
    except: pass

# ==============================================================================
# DASHBOARD CENTRAL (VIVO)
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
        if not node or not node.get("email"): 
            context.user_data['step'] = 'email_wait'
            await msg("⚠️ Escribe tu email para asegurar tu lugar:"); return

        node = BioEngine.calculate_state(node)
        await db.db.save_node(uid, node)
        
        rango = node['caste']
        info = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["OBRERO"])
        progreso = calculate_evolution_progress(node['honey'], len(node.get("referrals", [])))
        live_activity = generate_live_feed()
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        txt = (
            f"🏰 **THE ONE HIVE** | {info['icono']} **{rango}**\n"
            f"────────────────\n"
            f"Estado de la Colmena: **ACTIVA**\n\n"
            f"⚡ **Energía del Enjambre:**\n"
            f"`{bar}` ({polen}/{max_p})\n\n"
            f"📊 **Actividad Reciente:**\n"
            f"{live_activity}\n\n"
            f"📝 _Lo que hagas hoy importa más que lo que hagas mañana._\n"
            f"────────────────"
        )
        
        kb = [
            [InlineKeyboardButton("⚡ REALIZAR ACCIÓN", callback_data="forage")],
            # ACCIONES
            [InlineKeyboardButton("🟢 ACCIONES DISPONIBLES", callback_data="tasks")],
            # SOCIAL
            [InlineKeyboardButton("🐝 COLMENA", callback_data="squad"), InlineKeyboardButton("👥 INVITAR", callback_data="team")],
            # PREMIUM
            [InlineKeyboardButton("🚀 ACCESO PREMIUM", callback_data="shop")]
        ]
        
        try: await msg(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except: await msg(txt.replace("*", "").replace("_", ""), reply_markup=InlineKeyboardMarkup(kb))
            
    except Exception as e:
        logger.error(f"Dash Error: {e}")

# ==============================================================================
# SUB-MENÚS (ACCIONES, COLMENA, TIENDA)
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 ACCIÓN RÁPIDA", callback_data="v_t1")],
        [InlineKeyboardButton("🟡 EXPLORACIÓN (Bloqueado)", callback_data="v_t2")],
        [InlineKeyboardButton("🔴 PATROCINADA (Prioridad)", callback_data="v_t3")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = (
        "📡 **REGISTRO DE ACCIONES**\n\n"
        "Selecciona tu aporte:\n"
        "• **Acción Rápida:** Flujo constante.\n"
        "• **Exploración:** Requiere rango Explorador.\n"
        "• **Patrocinada:** Alto impacto.\n\n"
        "⚠️ *Estamos priorizando calidad de actividad.*"
    )
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    rol = node.get("caste", "OBRERO")
    lvl = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["OBRERO"])["acceso"]
    
    db_key = "TIER_1"
    req_lvl = 1
    if key == "v_t2": db_key = "TIER_2"; req_lvl = 2
    if key == "v_t3": db_key = "TIER_3"; req_lvl = 3
    
    if lvl < req_lvl:
        needed = "EXPLORADOR" if req_lvl == 2 else "GUARDIÁN"
        await q.answer(f"🔒 Acceso {needed} Requerido", show_alert=True); return
        
    links = FORRAJEO_DB.get(db_key, [])
    kb = [[InlineKeyboardButton(f"{item['name']}", url=item["url"])] for item in links]
    kb.append([InlineKeyboardButton("🔙 ATRÁS", callback_data="tasks")])
    
    await q.message.edit_text(f"📍 **LISTA DE ACCIONES**\n\nReglas en ajuste. Completa para validar.", reply_markup=InlineKeyboardMarkup(kb))

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"):
        cell = await db.db.get_cell(node["enjambre_id"])
        txt = f"🐝 **COLMENA: {cell['name']}**\n👥 Miembros: {len(cell['members'])}\n\nLa colmena crece."
        kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    else:
        txt = "⚠️ **NODO SIN COLMENA**\n\nUn nodo aislado es débil.\nForma una estructura para sobrevivir."
        kb = [[InlineKeyboardButton("➕ INICIAR ESTRUCTURA (100 pts)", callback_data="mk_cell")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cid = await db.db.create_cell(uid, f"Colmena-{random.randint(100,999)}")
        node['enjambre_id'] = cid
        await db.db.save_node(uid, node)
        await q.answer("✅ Estructura Iniciada"); await squad_menu(update, context)
    else: await q.answer("❌ Puntos insuficientes", show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🚀 OBTENER ACCESO PREMIUM ($9.99)", callback_data="buy_premium")],
        [InlineKeyboardButton("🔋 RECARGA ENERGÍA (200 pts)", callback_data="buy_energy")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]
    ]
    txt = "💎 **ACCESO PREMIUM**\n\n• Menos espera entre acciones.\n• Más acciones visibles.\n• Prioridad en futuras funciones.\n\nComodidad y eficiencia."
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ Energía Restaurada"); await show_dashboard(update, context)
    else: await q.answer("❌ Puntos Insuficientes", show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(
        f"🚀 **ACCESO PREMIUM**\n\nEnvía $9.99 USDT (TRC20) a:\n`{CRYPTO_WALLET_USDT}`\n\n(Envía comprobante al admin)", 
        parse_mode=ParseMode.MARKDOWN
    )

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    node = await db.db.get_node(uid)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    
    share_text = f"Entré a una fase temprana de The One Hive.\nTodavía están ajustando las reglas.\n\n{link}"
    share_url = f"https://t.me/share/url?url={link}&text={share_text}"
    
    txt = f"👥 **INVITACIÓN**\n\nComparte el acceso temprano.\n\n🔗 Enlace: `{link}`"
    kb = [[InlineKeyboardButton("📤 COMPARTIR ACCESO", url=share_url)], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Energía baja. Espera o recarga.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        
        yield_amt = CONST['RECOMPENSA_BASE'] * RANGOS_CONFIG[node['caste']]['bonus_tap']
        node['honey'] += yield_amt
        
        await db.db.save_node(uid, node)
        await q.answer(f"✅ Acción registrada: +{yield_amt:.2f}")
        
        if random.random() < 0.2: await show_dashboard(update, context)
        
    except Exception: pass

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🧬 **CICLO EVOLUTIVO**\n\n"
        "Tu rol en la colmena cambió. Ahora tus acciones pesan más.\n\n"
        "🐝 **OBRERO:** Inicio.\n"
        "🔭 **EXPLORADOR:** 5k pts.\n"
        "🛡️ **GUARDIÁN:** 20k pts.\n"
        "👑 **REINA:** 100k pts."
    )
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dash")]]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def global_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await db.db.get_global_stats()
    await update.callback_query.answer(
        f"🌍 ESTADO GLOBAL\n\n"
        f"📡 Nodos: {stats['nodes']:,}\n"
        f"💰 Tesoro: {stats['honey']:,.0f}\n"
        f"⚠️ Fase Temprana", 
        show_alert=True
    )

# ==============================================================================
# ROUTER FINAL
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    
    if d == "intro_step_2": await intro_step_2(update, context); return
    if d == "start_validation": await start_validation(update, context); return
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await q.message.edit_text("✅ Confirma con tu **EMAIL**:", parse_mode=ParseMode.MARKDOWN)
        return

    actions = {
        "go_dash": show_dashboard, 
        "forage": forage_action, 
        "tasks": tasks_menu, 
        "rank_info": rank_info_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "v_t1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "v_t2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "v_t3", c),
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
async def help_cmd(u, c): await u.message.reply_text("System v7.2")
async def broadcast_cmd(u, c): pass
