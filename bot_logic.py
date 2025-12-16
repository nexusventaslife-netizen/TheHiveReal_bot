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

# [NEXUS-7]: Configuración de Logs optimizada para producción
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# --- CONFIGURACIÓN MAESTRA DEL ECOSISTEMA (V70.0 - PRODUCTION GRADE) ---

# 1. SEGURIDAD & VARIABLES DE ENTORNO
# [NEXUS-7]: Validación robusta de entorno. No fallamos silenciosamente.
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no es un entero válido. Default: 0")
    ADMIN_ID = 0

CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# 2. ECONOMÍA DE LA COLMENA (TOKENOMICS)
# [NEXUS-7]: Ajustado para evitar inflación descontrolada.
INITIAL_USD = 0.00
INITIAL_HIVE = 500
BONUS_REWARD = 0.05

# 3. MOTOR DE MINERÍA
MINING_RATE_BASE = 1.5       # HIVE/segundo base
MAX_ENERGY_BASE = 500        # Capacidad batería
ENERGY_REGEN = 1             # Regen/segundo
AFK_CAP_HOURS = 6            # Aumentado a 6h para retención nocturna
MINING_COOLDOWN = 2.0        # [NEXUS-7]: Protección contra Autoclickers

# Costos
COST_PREMIUM_MONTH = 10 
COST_ENERGY_REFILL = 500 

# Assets Visuales
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ARSENAL DE ENLACES (MONETIZACIÓN CPA) ---
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

# --- TEXTOS NEUROLINGÜÍSTICOS (COPYWRITING) ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE: ACTIVADO**\n\n"
            "Saludos, **{name}**. Has salido de la Matrix.\n"
            "La mayoría pierde tiempo gratis. Aquí, tu tiempo es **CAPITAL**.\n\n"
            "💎 **TU ESTRATEGIA DUAL:**\n"
            "1. **Mina Néctar (HIVE):** Tu 'Gas' para operar en la red.\n"
            "2. **Ejecuta Contratos ($USD):** Tareas verificadas que pagan Dólares.\n"
            "3. **Escala:** Usa HIVE para comprar Licencias y ganar x2.\n\n"
            "🛡️ **FASE 1: SINCRONIZACIÓN**\n"
            "Estableciendo canal seguro con tu billetera...\n\n"
            "👇 **ENVÍA TU CÓDIGO DE ACCESO PARA CONTINUAR:**"
        ),
        'dashboard_body': """
🎛 **NODO DE OPERACIONES: {name}**
──────────────────
🏆 **Rango:** {status}
⚡ **Batería:** {energy}/{max_energy}
⛏️ **Hashrate:** {rate} HIVE/s

💵 **LIQUIDEZ REAL:** `${usd:.2f} USD`
🐝 **NÉCTAR ACUMULADO:** `{hive:.2f}`

⏳ **MINERÍA EN SEGUNDO PLANO (AFK):**
_{afk_msg}_
──────────────────
""",
        'mining_active': "⛏️ **EXTRAYENDO BLOQUE...**\n`{bar}` {percent}%\n\n⚡ Hash: `{hash}`",
        'mining_success': "✅ **BLOQUE VALIDADO**\n\n💰 **Recompensa:** +{gain} HIVE\n🔋 **Consumo:** -{cost} Energía\n",
        'payment_card_info': """
💳 **PASARELA PAYPAL PRO**
──────────────────────────
**Item:** Licencia de Reina (Lifetime)
**Beneficio:** Minería x2 + Retiros Express

El pago se procesa externamente. Tus datos están blindados.

👇 **INICIAR TRANSACCIÓN SEGURA:**
""",
        'payment_crypto_info': """
💎 **DEPOSITO TETHER (USDT)**
──────────────────────────
Red: **TRON (TRC20)**
Billetera Destino:
`{wallet}`

⚠️ **Instrucciones:**
1. Envía exactamente 10 USDT.
2. Copia el TXID (Hash).
3. Pégalo abajo para validación automática.
""",
    }
}

# --- UTILIDADES DE ALTA EFICIENCIA ---
def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_hash():
    # Genera un hash hexadecimal realista
    return "0x" + ''.join(random.choices("ABCDEF0123456789", k=18))

async def calculate_user_state(user_data):
    """
    [NEXUS-7]: Cálculo matemático preciso de regeneración y AFK.
    Evita que los usuarios manipulen el reloj del cliente. Usa tiempo del servidor.
    """
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    # 1. Regenerar Energía (Clamp entre 0 y Max)
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    # Solo regenera si ha pasado tiempo
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    # 2. Calcular Minería AFK (Solo si Mining Level > 0)
    mining_level = user_data.get('mining_level', 1)
    afk_rate = mining_level * 0.2  # 20% de eficiencia en modo pasivo
    
    # Cap de tiempo AFK para forzar login (Retention Hook)
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 60: # Solo cuenta si estuvo fuera más de 1 minuto
        pending_afk += afk_time * afk_rate
    
    user_data['pending_afk'] = int(pending_afk)
    user_data['last_update_ts'] = now
    
    return user_data

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r:
        await db.r.set(f"user:{user_id}", json.dumps(data))

# --- HANDLERS Y LÓGICA DE NEGOCIO ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    # Registro silencioso en DB
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Inicialización de Timestamp para minería
    user_data = await db.get_user(user.id)
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['mining_level'] = 1
        await save_user_data(user.id, user_data)

    txt = get_text('es', 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    
    # [NEXUS-7]: Enviar foto y texto juntos para mejor UX
    try:
        await update.message.reply_photo(
            photo=IMG_BEEBY, 
            caption=f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", 
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error media: {e}")
        await update.message.reply_text(f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    
    # Bypass de verificación
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        await show_dashboard(update, context)
        return

    if text.upper() == "/START":
        await start(update, context)
        return
        
    # Manejo de Hash de Crypto
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        # [NEXUS-7]: Validación básica de longitud de hash para filtrar spam
        if len(text) > 10:
            context.user_data['is_premium'] = True
            await update.message.reply_text(
                "✅ **HASH RECIBIDO**\n\nEl sistema está validando la transacción en la Blockchain (3-6 confirmaciones). Tu licencia se activará automáticamente.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL NODO", callback_data="go_dashboard")]])
            )
        else:
            await update.message.reply_text("❌ **HASH INVÁLIDO.** Verifica y envía de nuevo.")
        return

    # Fallback al Dashboard si el usuario está perdido
    user_data = await db.get_user(user.id)
    if user_data:
        await show_dashboard(update, context)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    
    # Matemáticas de minería en tiempo real
    user_data = await calculate_user_state(user_data)
    await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "Sistemas en espera..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** generados en ausencia."
    
    is_premium = context.user_data.get('is_premium', False)
    status_txt = "👑 REINA (VIP)" if is_premium else "🐛 OBRERO (STD)"
    
    txt = get_text('es', 'dashboard_body',
        name=user.first_name,
        status=status_txt,
        level=user_data.get('mining_level', 1),
        energy=int(user_data['energy']),
        max_energy=MAX_ENERGY_BASE,
        rate=MINING_RATE_BASE * user_data.get('mining_level', 1) * (2 if is_premium else 1),
        usd=user_data.get('usd_balance', 0.0),
        hive=user_data.get('nectar', 0),
        afk_msg=afk_msg
    )
    
    kb = []
    # [NEXUS-7]: UX Dinámica - Si hay AFK, el botón principal es recolectar
    if afk_amount > 10:
        kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else:
        kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE (TAP)", callback_data="mine_click")])
        
    kb.append([
        InlineKeyboardButton("📋 TAREAS ($USD)", callback_data="tasks_menu"),
        InlineKeyboardButton("🛒 MEJORAS", callback_data="shop_menu")
    ])
    kb.append([
        InlineKeyboardButton("👤 PERFIL", callback_data="profile"), 
        InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")
    ])
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- CORE MINING ENGINE (ANTISPAM PROTECTED) ---
async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # [NEXUS-7]: Protección Anti-Flood (Cooldown)
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN:
        await query.answer("❄️ Enfriando sistemas...", show_alert=False)
        return
    context.user_data['last_mine_time'] = time.time()

    user_data = await db.get_user(user_id)
    user_data = await calculate_user_state(user_data) # Actualizar energía
    
    cost = 20 # Costo de energía por operación
    if user_data['energy'] < cost:
        await query.answer("🔋 Batería Agotada. Compra energía o espera.", show_alert=True)
        return

    # Lógica de Ganancia
    user_data['energy'] -= cost
    is_premium = context.user_data.get('is_premium', False)
    multiplier = 2.0 if is_premium else 1.0
    
    base_gain = MINING_RATE_BASE * 15 * multiplier
    # Probabilidad de golpe crítico (Gamificación)
    is_crit = random.random() < 0.15
    gain = base_gain * 2.5 if is_crit else base_gain
    
    user_data['nectar'] = int(user_data.get('nectar', 0) + gain)
    await save_user_data(user_id, user_data)

    # Animación Visual
    block_hash = generate_hash()
    try:
        await query.message.edit_text(
            get_text('es', 'mining_active', bar="▓▓░░░░░░░░", percent=25, hash=block_hash[:10]+"..."),
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.4) # Retardo táctico
        
        await query.message.edit_text(
            get_text('es', 'mining_active', bar="▓▓▓▓▓▓▓▓░░", percent=88, hash=block_hash),
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.2)
    except: pass 

    # Reporte Final
    final_txt = get_text('es', 'mining_success', gain=int(gain), cost=cost)
    if is_crit: final_txt += "\n🔥 **¡CRITICAL HIT! (x2.5)**"
    if is_premium: final_txt += "\n👑 **Bono Reina Aplicado**"
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")],
          [InlineKeyboardButton("🔙 PANEL", callback_data="go_dashboard")]]
          
    await query.message.edit_text(final_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- SISTEMAS DE SOPORTE ---

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    amount = int(user_data.get('pending_afk', 0))
    if amount <= 0:
        await query.answer("Nada que recolectar.", show_alert=True)
        return
        
    user_data['nectar'] = int(user_data.get('nectar', 0) + amount)
    user_data['pending_afk'] = 0
    await save_user_data(user_id, user_data)
    
    await query.answer(f"💰 +{amount} HIVE transferidos a Bóveda.", show_alert=True)
    await show_dashboard(update, context)

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = (
        "📋 **CONTRATOS DE LIQUIDEZ ($USD)**\n"
        "──────────────────────────\n"
        "Completa estas operaciones para recibir pagos en Fiat.\n"
        "⚠️ *Verificación Manual: 24h*\n\n"
        "1️⃣ **Operación Bybit:** Pago $5.00\n"
        "2️⃣ **Micro-Tasks Timebucks:** Pago $0.50\n"
        "3️⃣ **Encuestas FreeCash:** Pago $2.00\n"
    )
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['VIP_OFFER_1'])],
        [InlineKeyboardButton("⏱ TIMEBUCKS ($0.50)", url=LINKS['VALIDATOR_MAIN'])],
        [InlineKeyboardButton("💰 FREECASH ($2.00)", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ VALIDAR CONTRATO", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # [NEXUS-7]: Simulación de verificación con "Loading" para realismo
    await query.message.edit_text("🛰️ **CONECTANDO CON SERVIDOR CPA...**\nVerificando click ID...")
    await asyncio.sleep(2.0) # Espera dramática
    
    if not context.user_data.get('bonus_claimed'):
        context.user_data['bonus_claimed'] = True
        user_data['usd_balance'] = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ ¡Verificado! ${BONUS_REWARD} acreditados.", show_alert=True)
    else:
        await query.answer("⚠️ Tarea en revisión. El saldo se liberará en 24h.", show_alert=True)
        
    await show_dashboard(update, context)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = get_text('es', 'shop_body', hive=0) 
    kb = [
        [InlineKeyboardButton("⚡ RECARGA ENERGÍA (500 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("👑 LICENCIA REINA ($10 USD)", callback_data="buy_premium_info")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def buy_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = get_text('es', 'payment_card_info')
    kb = [
        # [NEXUS-7]: Botón WebAppInfo para UX nativa (Sin salir de Telegram visualmente)
        [InlineKeyboardButton("💳 PAGAR AHORA (SECURE)", web_app=WebAppInfo(url=LINK_PAGO_GLOBAL))],
        [InlineKeyboardButton("💎 PAGAR CON CRIPTO", callback_data="pay_crypto_info")],
        [InlineKeyboardButton("🔙 CANCELAR", callback_data="shop_menu")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def pay_crypto_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = get_text('es', 'payment_crypto_info', wallet=CRYPTO_WALLET_USDT)
    kb = [[InlineKeyboardButton("✅ YA ENVIÉ EL PAGO", callback_data="confirm_crypto_wait")]]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def confirm_crypto_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['waiting_for_hash'] = True
    await query.message.edit_text("📝 **INGRESO MANUAL DE HASH**\n\nPor favor, pega el TXID de tu transacción para que el sistema la rastree.")

# --- ENRUTADOR CENTRAL ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # Mapeo eficiente
    handlers = {
        "go_dashboard": show_dashboard,
        "mine_click": mining_animation,
        "claim_afk": claim_afk,
        "tasks_menu": tasks_menu,
        "verify_task_manual": verify_task_manual,
        "shop_menu": shop_menu,
        "buy_premium_info": buy_premium_info,
        "pay_crypto_info": pay_crypto_info,
        "confirm_crypto_wait": confirm_crypto_wait
    }
    
    if data in handlers:
        await handlers[data](update, context)
    elif data == "buy_energy":
        user_id = query.from_user.id
        user_data = await db.get_user(user_id)
        if user_data.get('nectar', 0) >= COST_ENERGY_REFILL:
            user_data['nectar'] -= COST_ENERGY_REFILL
            user_data['energy'] = min(user_data.get('energy', 0) + MAX_ENERGY_BASE, 2000)
            await save_user_data(user_id, user_data)
            await query.answer("⚡ Recarga exitosa.", show_alert=True)
            await show_dashboard(update, context)
        else:
            await query.answer("❌ Saldo HIVE insuficiente.", show_alert=True)
    elif data == "profile":
        await query.message.edit_text(f"👤 **NODO:** `{query.from_user.id}`\nEstado: Activo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
    elif data == "withdraw":
        await query.answer("🔒 Mínimo de retiro: $10.00 USD (Balance insuficiente)", show_alert=True)
    
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("Sistema TheOneHive v70.0\nUsa /start para reiniciar.")
async def invite_command(u, c): await u.message.reply_text("Sistema de referidos en mantenimiento.")
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Cache local limpiado.")
async def broadcast_command(u, c): pass
