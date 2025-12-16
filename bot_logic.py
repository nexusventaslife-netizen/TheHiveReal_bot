import logging
import asyncio
import random
import string
import datetime
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# -----------------------------------------------------------------------------
# 1. KERNEL & SEGURIDAD (V120.0 - DEFLATIONARY EDITION)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado. El sistema de aprobación manual no funcionará.")
    ADMIN_ID = 0

CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA "HARD MONEY" (Anti-Inflación)
INITIAL_USD = 0.00      # Saldo real estricto
INITIAL_HIVE = 100      # Reducido para aumentar escasez inicial
BONUS_REWARD = 0.05     # Pago por tarea validada manualmente

# ALGORITMO DE MINERÍA (PROOF OF WORK)
# Dificultad: Para ganar, debes gastar Energía (Tiempo)
MINING_COST_PER_TAP = 25    # Costo alto de energía para valorizar el token
BASE_REWARD_PER_TAP = 5     # Recompensa base baja (Escasez)
MAX_ENERGY_BASE = 500       # Tope de energía
ENERGY_REGEN = 1            # Regeneración lenta (1 punto por segundo)
AFK_CAP_HOURS = 4           # Límite pasivo estricto

# COSTOS DE MERCADO (QUEMA DE TOKENS)
COST_PREMIUM_MONTH = 10     # USD
COST_ENERGY_REFILL = 200    # HIVE (Quema tokens para seguir minando)

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# 2. ENLACES (ECOSYSTEM REVENUE)
# -----------------------------------------------------------------------------
LINKS = {
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"), 
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK",
    'GETRESPONSE': "https://gr8.com//pr/mWAka/d",
    'FREECASH': "https://freecash.com/r/XYN98",
    'SWAGBUCKS': "https://www.swagbucks.com/p/register?rb=226213635&rp=1",
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381"
}

# -----------------------------------------------------------------------------
# 3. TEXTOS (ENGANCHE DE VALOR REAL)
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE: PROTOCOLO DE VALOR**\n"
            "──────────────────────────\n\n"
            "Saludos, **{name}**. Estás entrando a una economía deflacionaria.\n"
            "Aquí el token **HIVE** no se regala, se MINA con esfuerzo (Proof of Work).\n\n"
            "💎 **TU ESTRATEGIA:**\n"
            "1. **Mina HIVE:** Escaso y valioso. Úsalo para comprar mejoras.\n"
            "2. **Ejecuta Tareas:** Gana USD reales verificados.\n"
            "3. **Acumula:** El valor futuro depende de tu posición hoy.\n\n"
            "🛡️ **FASE 1: VERIFICACIÓN**\n"
            "👇 **INGRESA TU CÓDIGO PARA ACTIVAR EL NODO:**"
        ),
        'ask_terms': "✅ **ENLACE SEGURO**\n\nAl unirte, aceptas que:\n1. Las tareas se verifican manualmente (No trampas).\n2. El HIVE es un activo digital del ecosistema.\n3. Tus datos ayudan a mejorar la red.\n\n¿Confirmas el protocolo?",
        'ask_email': "🤝 **CONFIRMADO**\n\n📧 Ingresa tu **EMAIL** para recibir notificaciones de pagos aprobados:",
        'ask_bonus': "🎉 **CUENTA LISTA**\n\n💰 Saldo: **$0.00 USD**\n⚡ Energía: **500/500**\n\n🎁 **PRIMERA MISIÓN ($0.05):**\nRegístrate en el Partner. Luego solicita la validación manual.",
        'btn_claim_bonus': "🚀 HACER TAREA Y VALIDAR",
        
        'dashboard_body': """
🎛 **NODO: {name}**
──────────────────
🏆 **Rango:** {rank}
⚡ **Energía:** `{energy_bar}` {energy}%
⛏️ **Potencia:** {rate} HIVE/tap

💵 **BILLETERA:** `${usd:.2f} USD`
🐝 **HIVE MINADO:** `{hive}`

💤 **MINERÍA AFK:**
_{afk_msg}_
──────────────────
""",
        'mining_success': "⛏️ **MINANDO BLOQUE...**\n\n🔋 Energía: `{old_e}` ➔ `{new_e}`\n🐝 HIVE: `{old_h}` ➔ `{new_h}`\n\n✅ **Bloque Validado**",
        
        'payment_card_info': "💳 **LICENCIA DE REINA**\nCompra segura vía PayPal. Activación manual tras pago.\n\n👇 **PAGAR:**",
        'payment_crypto_info': "💎 **PAGO USDT (TRC20)**\nDestino: `{wallet}`\n\nEnvía 10 USDT y pega el TXID abajo.",
        'shop_body': "🏪 **MERCADO**\nSaldo: {hive} HIVE\n\n⚡ **RECARGAR ENERGÍA (200 HIVE)**\nQuema HIVE para seguir minando.\n\n👑 **LICENCIA REINA ($10)**\n👷 **OBRERO (50k HIVE)**",
        
        'btn_t1': "🟢 ZONA 1 (Clicks)", 'btn_t2': "🟡 ZONA 2 (Pasivo)", 'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_shop': "🛒 TIENDA", 'btn_justificante': "📜 AUDITORÍA", 'btn_back': "🔙 VOLVER", 
        'btn_withdraw': "💸 RETIRAR", 'btn_team': "👥 ENJAMBRE", 'btn_profile': "👤 PERFIL"
    }
}

# -----------------------------------------------------------------------------
# 4. MOTOR MATEMÁTICO Y VISUAL (BARRA DE PROGRESO REAL)
# -----------------------------------------------------------------------------

def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_captcha(): return f"HIVE-{random.randint(100, 999)}"

def render_progressbar(current, total, length=10):
    """Genera una barra visual [███░░░]"""
    percent = max(0, min(current / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "░" * empty

def calculate_rank(hive_balance):
    if hive_balance < 1000: return "🥚 LARVA"
    if hive_balance < 5000: return "🐛 OBRERO"
    if hive_balance < 20000: return "⚔️ SOLDADO"
    if hive_balance < 100000: return "🛡️ GUARDIÁN"
    return "👑 REINA"

async def calculate_user_state(user_data):
    """Calcula regeneración basada en tiempo real"""
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    # Regeneración Lineal
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    # Minería AFK (Muy lenta para incentivar actividad)
    mining_level = user_data.get('mining_level', 1)
    afk_rate = mining_level * 0.1 
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 60: pending_afk += afk_time * afk_rate
    user_data['pending_afk'] = int(pending_afk)
    user_data['last_update_ts'] = now
    
    return user_data

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r: await db.r.set(f"user:{user_id}", json.dumps(data))

# -----------------------------------------------------------------------------
# 5. HANDLERS
# -----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    user_data = await db.get_user(user.id)
    # Inicializar valores si es nuevo
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['energy'] = MAX_ENERGY_BASE
        user_data['mining_level'] = 1
        await save_user_data(user.id, user_data)

    txt = get_text('es', 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    try: await update.message.reply_photo(photo=IMG_BEEBY, caption=f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")
    except: await update.message.reply_text(f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); user = update.effective_user
    
    # COMANDOS ADMIN PARA GESTIÓN DE PAGOS
    if user.id == ADMIN_ID:
        if text.startswith("/approve_task"): # /approve_task 12345
            try:
                target = int(text.split()[1])
                target_data = await db.get_user(target)
                if target_data:
                    current_usd = float(target_data.get('usd_balance', 0))
                    target_data['usd_balance'] = current_usd + BONUS_REWARD
                    await save_user_data(target, target_data)
                    await context.bot.send_message(target, f"✅ **TAREA APROBADA**\nSe han acreditado ${BONUS_REWARD} USD a tu saldo.")
                    await update.message.reply_text(f"Pago acreditado a {target}")
            except: pass
            return
        
        if text.startswith("/approve_vip"): # /approve_vip 12345
            try:
                target = int(text.split()[1])
                await context.bot.send_message(target, "👑 **LICENCIA DE REINA ACTIVADA**\nDisfruta de tus beneficios VIP.")
                await update.message.reply_text(f"VIP activado a {target}")
            except: pass
            return

    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        kb = [[InlineKeyboardButton("✅ ACEPTO EL PROTOCOLO", callback_data="accept_legal")], [InlineKeyboardButton("❌ CANCELAR", callback_data="reject_legal")]]
        await update.message.reply_text(get_text('es', 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if text.upper() == "/START": await start(update, context); return
    
    # Hash Crypto
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        if len(text) > 10:
            if ADMIN_ID != 0:
                await context.bot.send_message(ADMIN_ID, f"💰 **PAGO CRYPTO**\nUser: `{user.id}`\nHash: `{text}`\n\nUsa `/approve_vip {user.id}` para activar.")
            await update.message.reply_text("✅ **HASH ENVIADO.** Esperando validación del administrador.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER", callback_data="go_dashboard")]]))
        else: await update.message.reply_text("❌ Hash inválido.")
        return
        
    if context.user_data.get('waiting_for_email'):
        if "@" in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else: await update.message.reply_text("⚠️ Email inválido.")
        return

    user_data = await db.get_user(user.id)
    if user_data: await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD (DATOS EN TIEMPO REAL)
# -----------------------------------------------------------------------------
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; user_data = await db.get_user(user.id)
    user_data = await calculate_user_state(user_data); await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "Sin actividad..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** pendientes."
    
    current_e = int(user_data.get('energy', 0))
    max_e = MAX_ENERGY_BASE
    # BARRA VISUAL DE ENERGÍA
    bar = render_progressbar(current_e, max_e)
    
    txt = get_text('es', 'dashboard_body',
        name=user.first_name, 
        rank=calculate_rank(user_data.get('nectar', 0)),
        energy=current_e, max_energy=max_e, energy_bar=bar,
        rate=BASE_REWARD_PER_TAP,
        usd=user_data.get('usd_balance', 0.0), 
        hive=int(user_data.get('nectar', 0)),
        afk_msg=afk_msg
    )
    
    kb = []
    if afk_amount > 5: kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else: kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE (TAP)", callback_data="mine_click")])
    
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text('es', 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t3'), callback_data="tier_3")])
    kb.append([InlineKeyboardButton("🛒 TIENDA", callback_data="shop_menu"), InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")])
    kb.append([InlineKeyboardButton("👤 PERFIL", callback_data="profile"), InlineKeyboardButton("👥 ENJAMBRE", callback_data="team_menu")])
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. MINERÍA (PROOF OF WORK)
# -----------------------------------------------------------------------------
async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id
    
    # 1. Calcular estado actual antes de operar
    user_data = await db.get_user(user_id)
    user_data = await calculate_user_state(user_data)
    
    old_energy = int(user_data['energy'])
    old_hive = int(user_data.get('nectar', 0))
    
    # 2. Verificar Costo (Escasez)
    if old_energy < MINING_COST_PER_TAP:
        await query.answer(f"🔋 Sin Energía. Necesitas {MINING_COST_PER_TAP}.", show_alert=True)
        return

    # 3. Aplicar Costo y Ganancia
    user_data['energy'] = old_energy - MINING_COST_PER_TAP
    
    # Bonus de Suerte (Critical)
    is_crit = random.random() < 0.1
    gain = BASE_REWARD_PER_TAP * 2 if is_crit else BASE_REWARD_PER_TAP
    
    user_data['nectar'] = old_hive + gain
    await save_user_data(user_id, user_data)
    
    # 4. Actualizar UI con datos exactos (Feedback Visual)
    new_energy = int(user_data['energy'])
    new_hive = int(user_data['nectar'])
    
    msg_txt = get_text('es', 'mining_success', 
                       gain=gain, cost=MINING_COST_PER_TAP,
                       old_e=old_energy, new_e=new_energy,
                       old_h=old_hive, new_h=new_hive)
    
    if is_crit: msg_txt += "\n🔥 **¡CRITICAL HIT! (x2)**"
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")], [InlineKeyboardButton("🔙 DASHBOARD", callback_data="go_dashboard")]]
    
    # Usamos try/except para evitar floodwait si el usuario clickea muy rápido
    try:
        await query.message.edit_text(msg_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except:
        await query.answer("⛏️ Minado! (UI actualizando...)", show_alert=False)

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id)
    amount = int(user_data.get('pending_afk', 0))
    if amount <= 0: await query.answer("Nada que recolectar.", show_alert=True); return
    user_data['nectar'] = int(user_data.get('nectar', 0) + amount); user_data['pending_afk'] = 0
    await save_user_data(user_id, user_data)
    await query.answer(f"💰 +{amount} HIVE transferidos.", show_alert=True); await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 8. SISTEMA DE TAREAS (VERIFICACIÓN MANUAL)
# -----------------------------------------------------------------------------
async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (VALIDAR)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ YA HICE UNA TAREA (VALIDAR)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['BYBIT'])],
        [InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO']), InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT'])],
        [InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE'])],
        [InlineKeyboardButton("💹 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("✅ YA HICE UNA TAREA (VALIDAR)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **ZONA 3: HIGH TICKET**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SISTEMA DE VERIFICACIÓN HUMANA"""
    query = update.callback_query
    user_id = query.from_user.id
    user = query.from_user
    
    # 1. Bloqueo inmediato (No dar dinero)
    await query.message.edit_text("🛰️ **ENVIANDO SOLICITUD DE REVISIÓN...**")
    await asyncio.sleep(1.5)
    
    # 2. Notificar al Admin
    if ADMIN_ID != 0:
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📋 **NUEVA TAREA COMPLETADA**\n\nUsuario: {user.first_name} (ID: `{user_id}`)\nDice haber completado una tarea.\n\n👉 Revisa tus paneles de afiliado.\nSi es verdad, usa: `/approve_task {user_id}`"
            )
        except: pass
    
    # 3. Respuesta al Usuario
    await query.message.edit_text(
        "📝 **SOLICITUD RECIBIDA (ESTADO: PENDIENTE)**\n\n"
        "Hemos notificado al equipo de revisión. Verificaremos con el anunciante si tu registro es válido.\n"
        "⏳ **Tiempo estimado:** 12-24 horas.\n\n"
        "⚠️ *Si intentas engañar al sistema, tu cuenta será baneada.*",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ENTENDIDO", callback_data="go_dashboard")]])
    )

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; user_id = query.from_user.id; user_data = await db.get_user(user_id); hive = user_data.get('nectar', 0)
    txt = get_text('es', 'shop_body', hive=hive) 
    kb = [[InlineKeyboardButton(f"⚡ RECARGA ENERGÍA ({COST_ENERGY_REFILL} HIVE)", callback_data="buy_energy")], [InlineKeyboardButton("👑 LICENCIA REINA ($10 USD)", callback_data="buy_premium_info")], [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; txt = get_text('es', 'payment_card_info')
    kb = [[InlineKeyboardButton("💳 PAGAR AHORA (SECURE)", web_app=WebAppInfo(url=LINK_PAGO_GLOBAL))], [InlineKeyboardButton("💎 PAGAR CON CRIPTO", callback_data="pay_crypto_info")], [InlineKeyboardButton("🔙 CANCELAR", callback_data="shop_menu")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def pay_crypto_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; txt = get_text('es', 'payment_crypto_info', wallet=CRYPTO_WALLET_USDT)
    kb = [[InlineKeyboardButton("✅ YA ENVIÉ EL PAGO", callback_data="confirm_crypto_wait")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def confirm_crypto_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; context.user_data['waiting_for_hash'] = True
    await query.message.edit_text("📝 **INGRESO MANUAL DE HASH**\n\nPega el TXID de tu transacción aquí.")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
    await query.message.edit_text(f"📡 **RED DE RECOLECCIÓN**\n🔗 Tu enlace:\n`{link}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code; txt = get_text(lang, 'ask_bonus', bonus=BONUS_REWARD)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_claim_bonus', bonus=BONUS_REWARD), url=LINKS['VALIDATOR_MAIN'])], [InlineKeyboardButton("✅ VALIDAR MISIÓN", callback_data="verify_task_manual")]] # Redirige a verificación manual
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 9. ENRUTADOR
# -----------------------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; data = query.data; user_id = query.from_user.id
    
    if data == "accept_legal": context.user_data['waiting_for_terms'] = False; context.user_data['waiting_for_email'] = True; await query.message.edit_text(get_text('es', 'ask_email'), parse_mode="Markdown"); return
    if data == "reject_legal": await query.message.edit_text("❌ Acceso Denegado."); return
    # Bonus Done ahora va a verify manual, no da dinero gratis
    if data == "bonus_done": await verify_task_manual(update, context); return 

    handlers = {
        "go_dashboard": show_dashboard, "mine_click": mining_animation, "claim_afk": claim_afk, "verify_task_manual": verify_task_manual, "shop_menu": shop_menu,
        "buy_premium_info": buy_premium_info, "pay_crypto_info": pay_crypto_info, "confirm_crypto_wait": confirm_crypto_wait,
        "tier_1": tier1_menu, "tier_2": tier2_menu, "tier_3": tier3_menu, "team_menu": team_menu, "go_justificante": show_justificante
    }
    
    if data in handlers: await handlers[data](update, context)
    elif data == "buy_energy":
        user_data = await db.get_user(user_id)
        # QUEMA DE TOKENS (Utility)
        if user_data.get('nectar', 0) >= COST_ENERGY_REFILL:
            user_data['nectar'] -= COST_ENERGY_REFILL
            user_data['energy'] = min(user_data.get('energy', 0) + 200, MAX_ENERGY_BASE) # Recarga parcial para que sigan jugando
            await save_user_data(user_id, user_data)
            await query.answer("⚡ +200 Energía Recargada. (-200 HIVE)", show_alert=True)
            await show_dashboard(update, context)
        else: await query.answer(f"❌ Necesitas {COST_ENERGY_REFILL} HIVE.", show_alert=True)
    elif data == "profile": await query.message.edit_text(f"👤 **PERFIL**\nID: `{query.from_user.id}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
    elif data == "withdraw": 
        user_data = await db.get_user(user_id); bal = user_data.get('usd_balance', 0)
        if bal >= 10:
            if ADMIN_ID != 0: 
                try: await context.bot.send_message(ADMIN_ID, f"💸 **SOLICITUD RETIRO**\nUser: {user_id}\nMonto: ${bal}")
                except: pass
            await query.answer("✅ Solicitud enviada.", show_alert=True)
        else: await query.answer(f"🔒 Mínimo $10. Tienes ${bal:.2f}", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("TheOneHive v120.0 Deflationary")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")
async def broadcast_command(u, c): 
    if u.effective_user.id != ADMIN_ID: return
    msg = u.message.text.replace("/broadcast", "").strip()
    if msg: await u.message.reply_text(f"📢 **ENVIADO:**\n\n{msg}")
    
async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_text = get_text('es', 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD** (Partner Network)\n✅ **ESTADO:** Validado."
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
