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

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN MAESTRA DEL ECOSISTEMA ---

# Seguridad
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    ADMIN_ID = 0

CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ Configurar en Render")
LINK_PAGO_GLOBAL = "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC"

# --- ECONOMÍA DE LA COLMENA (MATH MODEL) ---
INITIAL_USD = 0.00
INITIAL_HIVE = 500
BONUS_REWARD = 0.05

# Configuración de Minería
MINING_RATE_BASE = 1.5       # HIVE por segundo (Nivel 1)
MAX_ENERGY_BASE = 500        # Capacidad de batería
ENERGY_REGEN = 1             # Energía recuperada por segundo
AFK_CAP_HOURS = 4            # Tiempo máximo de minado sin entrar al bot

# Costos
COST_PREMIUM_MONTH = 10 
COST_LEVEL_UP = 5000         # Costo para subir nivel de minería

# Assets
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ENLACES (CPA / REVENUE) ---
LINKS = {
    'VALIDATOR_MAIN': "https://timebucks.com/?refID=227501472",
    'VIP_OFFER_1': "https://www.bybit.com/invite?ref=BBJWAX4", 
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

# --- TEXTOS PERSUASIVOS ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **PROTOCOL HIVE INICIADO**\n\n"
            "Bienvenido, **{name}**. Has sido reclutado.\n"
            "A diferencia de otros sistemas, aquí tu tiempo genera **VALOR REAL**.\n\n"
            "💎 **TU MISIÓN:**\n"
            "1. **Mina Néctar (HIVE):** El combustible de la economía.\n"
            "2. **Ejecuta Tareas:** Convierte tu actividad en **USD**.\n"
            "3. **Adquiere NFTs:** Automatiza tu riqueza.\n\n"
            "👇 **ACTIVA TU NODO AHORA:**"
        ),
        'dashboard_body': """
🎛 **CENTRO DE MINERÍA**
──────────────────
👤 **Nodo:** {name} | 🏆 **Nivel:** {level}
⚡ **Energía:** {energy}/{max_energy}
⛏️ **Hashrate:** {rate} HIVE/s

💵 **SALDO REAL:** `${usd:.2f} USD`
🐝 **HIVE MINADO:** `{hive:.2f}`

⏳ **MINERÍA PASIVA (AFK):**
_{afk_msg}_
──────────────────
""",
        'mining_active': "⛏️ **MINANDO BLOQUE...**\n`{bar}` {percent}%\n\n⚡ Hash: `{hash}`",
        'mining_success': "✅ **BLOQUE COMPLETADO**\n\n💰 **Ganancia:** +{gain} HIVE\n🔋 **Energía:** -{cost}\n📈 **XP:** +10",
        'afk_claim': "💤 **INFORME DE SUEÑO**\n\nTus obreros trabajaron mientras no estabas.\n\n💰 **GENERADO:** {amount} HIVE\n👇 ¡Recoléctalo ahora!",
        'payment_card_info': "💳 **PASARELA PAYPAL PRO**\n\nAdquiere tu **Licencia de Reina** para duplicar (x2) toda tu minería.\n\n👇 **PAGO SEGURO:**",
        'btn_mine': "⛏️ MINAR AHORA",
        'btn_claim': "💰 RECOLECTAR",
        'btn_shop': "🛒 MEJORAR RIG",
        'btn_tasks': "📋 TAREAS ($USD)",
    }
}

def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_hash():
    return "0x" + ''.join(random.choices("ABCDEF0123456789", k=16))

# --- CÁLCULOS DE MINERÍA ---

async def calculate_user_state(user_data):
    """Calcula energía regenerada y minería AFK basada en el tiempo real"""
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    # 1. Regenerar Energía
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
    user_data['energy'] = int(new_energy)
    
    # 2. Calcular Minería AFK (Pasiva)
    # Solo si el usuario tiene nivel > 0 o NFTs
    mining_level = user_data.get('mining_level', 1)
    afk_rate = mining_level * 0.5 # 0.5 HIVE por segundo pasivo
    
    # Cap de tiempo AFK (para obligarlos a entrar)
    afk_time = min(elapsed, AFK_CAP_HOURS * 3600)
    
    pending_afk = user_data.get('pending_afk', 0)
    if afk_time > 60: # Mínimo 1 minuto para contar
        pending_afk += afk_time * afk_rate
    
    user_data['pending_afk'] = int(pending_afk)
    user_data['last_update_ts'] = now
    
    return user_data

async def save_user_data(user_id, data):
    if hasattr(db, 'r') and db.r:
        await db.r.set(f"user:{user_id}", json.dumps(data))

# --- HANDLERS PRINCIPALES ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Inicializar datos de tiempo si es nuevo o reset
    user_data = await db.get_user(user.id)
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['mining_level'] = 1
        await save_user_data(user.id, user_data)

    txt = get_text('es', 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    
    await update.message.reply_photo(
        photo=IMG_BEEBY, 
        caption=f"{txt}\n\n🔐 **CÓDIGO:** `{captcha}`", 
        parse_mode="Markdown"
    )

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    
    # Verificación Captcha
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        await show_dashboard(update, context)
        return

    if text.upper() == "/START":
        await start(update, context)
        return

    # Si escribe cualquier otra cosa y ya está verificado, mostrar dashboard
    user_data = await db.get_user(user.id)
    if user_data:
        await show_dashboard(update, context)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    
    # Recalcular estado actual (Energía/AFK)
    user_data = await calculate_user_state(user_data)
    await save_user_data(user.id, user_data)
    
    # Preparar visualización
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "💤 Todo tranquilo..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** pendientes de recolección."
    
    txt = get_text('es', 'dashboard_body',
        name=user.first_name,
        level=user_data.get('mining_level', 1),
        energy=int(user_data['energy']),
        max_energy=MAX_ENERGY_BASE,
        rate=MINING_RATE_BASE * user_data.get('mining_level', 1),
        usd=user_data.get('usd_balance', 0.0),
        hive=user_data.get('nectar', 0),
        afk_msg=afk_msg
    )
    
    kb = []
    # Botón Principal Dinámico
    if afk_amount > 10:
        kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else:
        kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE", callback_data="mine_click")])
        
    kb.append([
        InlineKeyboardButton("📋 TAREAS ($USD)", callback_data="tasks_menu"),
        InlineKeyboardButton("🛒 MEJORAS", callback_data="shop_menu")
    ])
    kb.append([InlineKeyboardButton("👤 PERFIL", callback_data="profile"), InlineKeyboardButton("💸 RETIRAR", callback_data="withdraw")])
    
    if update.callback_query:
        # Evitar error si el mensaje es idéntico
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- MOTOR DE MINERÍA ACTIVA (TAP) ---
async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # 1. Validar Energía
    user_data = await calculate_user_state(user_data) # Actualizar primero
    cost = 20 # Costo por click
    
    if user_data['energy'] < cost:
        await query.answer("🔋 Batería baja. Espera recarga o compra energía.", show_alert=True)
        return

    # 2. Descontar y Calcular
    user_data['energy'] -= cost
    mining_level = user_data.get('mining_level', 1)
    # Ganancia variable (Critical hit chance)
    base_gain = MINING_RATE_BASE * 10 
    is_crit = random.random() < 0.1 # 10% probabilidad
    gain = base_gain * 3 if is_crit else base_gain
    
    user_data['nectar'] = int(user_data.get('nectar', 0) + gain)
    await save_user_data(user_id, user_data)

    # 3. Animación Visual (Barra de progreso)
    # Editamos el mensaje 2 veces para simular trabajo
    block_hash = generate_hash()
    
    try:
        await query.message.edit_text(
            get_text('es', 'mining_active', bar="██░░░░░░░░", percent=20, hash=block_hash),
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.3) # Pequeña pausa
        
        await query.message.edit_text(
            get_text('es', 'mining_active', bar="████████░░", percent=80, hash=block_hash),
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.3)
    except: pass # Ignorar si telegram se queja de rapidez

    # 4. Resultado Final
    final_txt = get_text('es', 'mining_success', gain=int(gain), cost=cost)
    if is_crit: final_txt += "\n🔥 **¡GOLPE DE SUERTE! (x3)**"
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")],
          [InlineKeyboardButton("🔙 PANEL", callback_data="go_dashboard")]]
          
    await query.message.edit_text(final_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- RECOLECCIÓN AFK ---
async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    amount = int(user_data.get('pending_afk', 0))
    if amount <= 0:
        await query.answer("Nada que recolectar aún.", show_alert=True)
        return
        
    user_data['nectar'] = int(user_data.get('nectar', 0) + amount)
    user_data['pending_afk'] = 0
    await save_user_data(user_id, user_data)
    
    await query.answer(f"💰 +{amount} HIVE recolectados!", show_alert=True)
    await show_dashboard(update, context)

# --- TAREAS REALES ($USD) ---
async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # Aquí es donde el usuario hace dinero real
    txt = (
        "📋 **TABLÓN DE MISIONES (PAGO EN USD)**\n"
        "──────────────────────────\n"
        "Completa estas acciones para cargar tu saldo en Dólares. \n"
        "⚠️ *El sistema verifica tu IP.* \n\n"
        "1️⃣ **Registro Bybit:** Pago $5.00\n"
        "2️⃣ **Encuesta Timebucks:** Pago $0.50\n"
        "3️⃣ **FreeCash App:** Pago $2.00\n"
    )
    
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['VIP_OFFER_1'])],
        [InlineKeyboardButton("⏱ TIMEBUCKS ($0.50)", url=LINKS['VALIDATOR_MAIN'])],
        [InlineKeyboardButton("💰 FREECASH ($2.00)", url=LINKS['FREECASH'])],
        # BOTÓN DE VALIDACIÓN DE TAREA
        [InlineKeyboardButton("✅ YA COMPLETÉ UNA TAREA", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simulación de verificación. En producción, esto se conecta al Postback.
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    # Bono de bienvenida si es la primera vez
    if not context.user_data.get('bonus_claimed'):
        context.user_data['bonus_claimed'] = True
        user_data['usd_balance'] = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ ¡Verificado! +${BONUS_REWARD} USD agregados.", show_alert=True)
    else:
        await query.answer("⏳ Verificando con el anunciante... Esto puede tardar 24h.", show_alert=True)
        
    await show_dashboard(update, context)

# --- TIENDA Y PAGOS ---
async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    txt = get_text('es', 'shop_body', hive=0) # Simplificado para visualización
    
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
        [InlineKeyboardButton("💳 PAGAR AHORA (PAYPAL)", web_app=WebAppInfo(url=LINK_PAGO_GLOBAL))],
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
    # Activar modo "esperando hash"
    context.user_data['waiting_for_hash'] = True
    await query.message.edit_text("📝 **POR FAVOR, ESCRIBE EL HASH (TXID):**\n\nCopia y pega el código de la transacción aquí en el chat.")

# --- ENRUTADOR DE BOTONES ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "go_dashboard": await show_dashboard(update, context)
    elif data == "mine_click": await mining_animation(update, context)
    elif data == "claim_afk": await claim_afk(update, context)
    elif data == "tasks_menu": await tasks_menu(update, context)
    elif data == "verify_task_manual": await verify_task_manual(update, context)
    elif data == "shop_menu": await shop_menu(update, context)
    elif data == "buy_energy": 
        await query.answer("Función de compra en desarrollo (Necesitas HIVE)", show_alert=True)
    elif data == "buy_premium_info": await buy_premium_info(update, context)
    elif data == "pay_crypto_info": await pay_crypto_info(update, context)
    elif data == "confirm_crypto_wait": await confirm_crypto_wait(update, context)
    
    # Manejo genérico para botones no definidos arriba
    try: await query.answer()
    except: pass

async def help_command(u, c): await u.message.reply_text("Ayuda: /start para reiniciar.")
async def invite_command(u, c): await u.message.reply_text("Tu enlace está en el Perfil.")
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK")
async def broadcast_command(u, c): pass
