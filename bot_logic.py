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
# 1. NÚCLEO DE CONFIGURACIÓN Y SEGURIDAD (NEXUS KERNEL)
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# SEGURIDAD: ID de Administrador (Desde Variables de Entorno)
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado o inválido. Usando 0.")
    ADMIN_ID = 0

# DIRECCIONES DE COBRO (Las venas del negocio)
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# ECONOMÍA Y BALANCE INICIAL (Tokenomics)
INITIAL_USD = 0.00          # El dinero real empieza en 0 para evitar pérdidas.
INITIAL_HIVE = 500          # Capital semilla (Néctar) para enganchar.
BONUS_REWARD = 0.05         # Costo de adquisición de Lead (Validación).

# MOTOR DE JUEGO (Gamificación)
MINING_RATE_BASE = 1.5      # HIVE/segundo base.
MAX_ENERGY_BASE = 500       # Capacidad de tanque.
ENERGY_REGEN = 1            # Regeneración por segundo.
AFK_CAP_HOURS = 6           # Límite de minería pasiva (Retention Hook).
MINING_COOLDOWN = 1.5       # Protección Anti-Spam/Autoclicker.

# PRECIOS DE MERCADO
COST_PREMIUM_MONTH = 10     # Precio en USD de la Licencia.
COST_ENERGY_REFILL = 500    # Precio en HIVE de la recarga.

# ASSETS GRÁFICOS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# 2. ARSENAL DE ENLACES DE MONETIZACIÓN (REVENUE STREAMS)
# -----------------------------------------------------------------------------
# Aquí residen tus 4 vías de ingreso. El bot dirigirá el tráfico aquí.
LINKS = {
    # > FUENTE DE TRÁFICO 1: VALIDACIÓN DE LEADS (CPA)
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    
    # > FUENTE DE TRÁFICO 2: MICRO-TAREAS (Volumen)
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    
    # > FUENTE DE TRÁFICO 3: INGRESOS PASIVOS (Data Sharing)
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    
    # > FUENTE DE TRÁFICO 4: HIGH TICKET & FINTECH (Comisiones Altas)
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
    'TESTBIRDS': "https://nest.testbirds.com/home/tester?t=9ef7ff82-ca89-4e4a-a288-02b4938ff381",
    
    # OFERTA VIP (El gancho principal)
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"),
}

# -----------------------------------------------------------------------------
# 3. COPYWRITING PERSUASIVO Y MENSAJES DEL SISTEMA
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE: CONEXIÓN ESTABLECIDA**\n"
            "──────────────────────────\n\n"
            "Bienvenido, **{name}**. Has sido seleccionado.\n"
            "Mientras otros pierden tiempo, tú estás a punto de construir un **ACTIVO DIGITAL REAL**.\n\n"
            "💎 **TU ECOSISTEMA DUAL DE INGRESOS:**\n\n"
            "1️⃣ **HIVE (Néctar):** Token de utilidad. Úsalo para comprar Licencias y NFTs.\n"
            "2️⃣ **USD (Fiat):** Dinero real generado por tareas de High-Ticket.\n"
            "3️⃣ **Data Lead:** Tu actividad genera valor. Nosotros compartimos ese valor contigo.\n\n"
            "🛡️ **PASO 1: VERIFICACIÓN DE NODO**\n"
            "Para activar tu billetera receptora, necesitamos confirmar tu humanidad.\n\n"
            "👇 **COPIA EL CÓDIGO DE SEGURIDAD Y ENVÍALO AL CHAT:**"
        ),
        'ask_terms': (
            "✅ **NODO VERIFICADO CORRECTAMENTE**\n"
            "───────────────────────\n"
            "**PROTOCOLO DE LA COLMENA & CONSENTIMIENTO:**\n\n"
            "Al operar en TheOneHive, aceptas:\n"
            "1. **Monetización:** Recibir ofertas comerciales y publicidad segmentada.\n"
            "2. **Calidad:** Usar datos reales (Prohibido VPN/Bots).\n"
            "3. **Gamificación:** Entiendes que HIVE es un activo interno para mejorar tu rendimiento.\n\n"
            "¿Aceptas el protocolo para iniciar la facturación?"
        ),
        'ask_email': (
            "🤝 **CONTRATO INTELIGENTE ACEPTADO**\n"
            "───────────────────────\n"
            "📧 **VINCULACIÓN DE CUENTA (KYC LITE):**\n\n"
            "Ingresa tu **CORREO ELECTRÓNICO** principal.\n"
            "*(Es vital para enviarte los comprobantes de retiro y alertas de Airdrop)*."
        ),
        'ask_bonus': (
            "🎉 **¡SISTEMA OPERATIVO AL 100%!**\n"
            "───────────────────────\n"
            "Estado de Billetera: **ACTIVA**\n"
            "Saldo Actual: **$0.00 USD**\n\n"
            "🎁 **MISIÓN INICIAL (BONO DE ACTIVACIÓN):**\n"
            "Tienes un pago pendiente de **${bonus} USD** esperando liberación. Para desbloquearlo, valida tu identidad en nuestro Partner Principal.\n\n"
            "1. Accede al enlace seguro.\n"
            "2. Completa el registro gratuito.\n"
            "3. Regresa y pulsa 'VALIDAR MISIÓN' para acreditar."
        ),
        'btn_claim_bonus': "🚀 ACCEDER A LA MISIÓN (GANAR ${bonus})",
        
        'dashboard_body': """
🎛 **DASHBOARD CENTRAL: {name}**
──────────────────
🔰 **Rango:** {rank}
⚡ **Energía:** {energy}/{max_energy}
⛏️ **Potencia:** {rate} HIVE/s

💵 **SALDO FIAT:** `${usd:.2f} USD`
🐝 **SALDO HIVE:** `{hive:.2f}`

💤 **MINERÍA AFK (PASIVA):**
_{afk_msg}_
──────────────────
""",
        'mining_active': "⛏️ **EXTRAYENDO BLOQUE...**\n`{bar}` {percent}%\n\n🔗 Hash: `{hash}`",
        'mining_success': "✅ **BLOQUE MINADO**\n\n💰 **Resultado:** +{gain} HIVE\n🔋 **Energía:** -{cost}\n📈 **Experiencia:** +10 XP",
        
        'payment_card_info': """
💳 **LICENCIA DE REINA (LIFETIME ACCESS)**
──────────────────────────
Al adquirir esta licencia, desbloqueas el máximo potencial de tu nodo:

🚀 **Multiplicador x2** en minería manual y AFK.
🔓 **Retiros Prioritarios** en 24h.
💎 **Acceso a Mercado P2P** (Próximamente).

👇 **PAGO SEGURO VÍA PAYPAL:**
""",
        'payment_crypto_info': """
💎 **RECARGA VÍA TETHER (USDT)**
──────────────────────────
Red Requerida: **TRON (TRC20)**
Dirección de Bóveda:
`{wallet}`

⚠️ **Procedimiento de Verificación:**
1. Realiza la transferencia de **10 USDT**.
2. Copia el **TXID (Hash)** de la transacción.
3. Pégalo en este chat para validación automática.
""",
        'shop_body': """
🏪 **MERCADO DE ACTIVOS**
──────────────────────────
*Capital Disponible:* {hive} HIVE

⚡ **RECARGA DE EMERGENCIA (500 HIVE)**
Restaura 100% de energía para seguir operando.

👑 **LICENCIA DE REINA ($10 USD)**
Estatus VIP y velocidad de minado x2.

👷 **PAQUETE DE OBREROS (50k HIVE)**
Desbloquea las Zonas de Alto Valor (Tier 2).

💎 **NFT "HIVE GENESIS" (100k HIVE)**
Otorga 30% de comisión vitalicia sobre referidos.
""",
        'justificante_header': "📜 **LEDGER DE TRANSPARENCIA**\n──────────────────────────\nRegistro inmutable de ingresos del sistema:\n\n",
        
        # Botones del Menú Principal
        'btn_t1': "🟢 ZONA 1: MICRO-TAREAS", 
        'btn_t2': "🟡 ZONA 2: PASIVO (AFK)", 
        'btn_t3': "🔴 ZONA 3: HIGH TICKET",
        'btn_shop': "🛒 MERCADO / UPGRADES",
        'btn_justificante': "📜 AUDITORÍA",
        'btn_back': "🔙 VOLVER AL DASHBOARD", 
        'btn_withdraw': "💸 RETIRAR FONDOS", 
        'btn_team': "👥 GESTIÓN DE EQUIPO", 
        'btn_profile': "👤 MI PERFIL"
    }
}

# -----------------------------------------------------------------------------
# 4. LÓGICA MATEMÁTICA Y EVOLUTIVA (GAME ENGINE)
# -----------------------------------------------------------------------------

def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_hash():
    """Genera un hash visualmente realista para la simulación de minería"""
    return "0x" + ''.join(random.choices("ABCDEF0123456789", k=18))

def generate_captcha():
    return f"HIVE-{random.randint(100, 999)}"

def calculate_rank(hive_balance):
    """Sistema de Evolución de Personaje basado en tenencia"""
    if hive_balance < 2000: return "🥚 LARVA (Nvl 1)"
    if hive_balance < 10000: return "🐛 OBRERO (Nvl 2)"
    if hive_balance < 50000: return "⚔️ SOLDADO (Nvl 3)"
    if hive_balance < 100000: return "🛡️ GUARDIÁN (Nvl 4)"
    return "👑 REINA (Nvl MAX)"

async def calculate_user_state(user_data):
    """
    Motor de cálculo en tiempo real.
    Calcula: Regeneración de energía y Minería Pasiva (AFK)
    """
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    # 1. Regenerar Energía
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
    if elapsed > 0:
        new_energy = min(max_e, current_energy + (elapsed * ENERGY_REGEN))
        user_data['energy'] = int(new_energy)
    
    # 2. Calcular Minería AFK (Ingreso Pasivo)
    mining_level = user_data.get('mining_level', 1)
    afk_rate = mining_level * 0.2  # 20% eficiencia pasiva
    
    # Cap de tiempo para obligar al usuario a volver (Retention Loop)
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

async def check_daily_streak(user_id):
    """Sistema de Rachas Diarias para aumentar retención"""
    user_data = await db.get_user(user_id)
    if not user_data: return 0

    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    last_date_str = user_data.get('last_streak_date', "")
    current_streak = user_data.get('streak_days', 0)

    if last_date_str == today_str:
        return current_streak 

    yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    if last_date_str == yesterday:
        new_streak = current_streak + 1
        user_data['streak_days'] = new_streak
        user_data['last_streak_date'] = today_str
        user_data['nectar'] = int(user_data.get('nectar', 0)) + (new_streak * 10)
        await save_user_data(user_id, user_data)
        return new_streak
    else:
        user_data['streak_days'] = 1
        user_data['last_streak_date'] = today_str
        await save_user_data(user_id, user_data)
        return 1

# -----------------------------------------------------------------------------
# 5. HANDLERS DE INTERACCIÓN (INPUT/OUTPUT)
# -----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = args[0] if args and args[0].isdigit() else None
    
    if hasattr(db, 'add_user'): 
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Setup inicial
    user_data = await db.get_user(user.id)
    if 'last_update_ts' not in user_data:
        user_data['last_update_ts'] = time.time()
        user_data['mining_level'] = 1
        await save_user_data(user.id, user_data)

    txt = get_text('es', 'welcome_caption', name=user.first_name)
    captcha = f"HIVE-{random.randint(100,999)}"
    context.user_data['captcha'] = captcha
    
    try:
        await update.message.reply_photo(
            photo=IMG_BEEBY, 
            caption=f"{txt}\n\n🔐 **CÓDIGO DE ACCESO:** `{captcha}`", 
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error media: {e}")
        await update.message.reply_text(f"{txt}\n\n🔐 **CÓDIGO DE ACCESO:** `{captcha}`", parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    
    # 1. Validación Captcha
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        # Lanzar paso 2: Términos Legales
        kb = [
            [InlineKeyboardButton("✅ ACEPTO EL PROTOCOLO", callback_data="accept_legal")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="reject_legal")]
        ]
        await update.message.reply_text(get_text('es', 'ask_terms'), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    # 2. Comandos Manuales
    if text.upper() == "/START":
        await start(update, context)
        return
        
    # 3. Validación de Pagos (Hash Crypto)
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        if len(text) > 10:
            context.user_data['is_premium'] = True
            await update.message.reply_text(
                "✅ **HASH RECIBIDO.**\nEl sistema está validando la transacción en Blockchain. Tu licencia se activará en breve.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("IR AL DASHBOARD", callback_data="go_dashboard")]])
            )
        else:
            await update.message.reply_text("❌ **ERROR:** Formato de Hash inválido.")
        return
        
    # 4. Captura de Email (Lead Generation)
    if context.user_data.get('waiting_for_email'):
        if "@" in text and "." in text:
            if hasattr(db, 'update_email'): await db.update_email(user.id, text)
            context.user_data['waiting_for_email'] = False
            await offer_bonus_step(update, context)
        else:
            await update.message.reply_text("⚠️ Email inválido. Por favor verifica.")
        return

    # Fallback
    user_data = await db.get_user(user.id)
    if user_data:
        await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 6. DASHBOARD PERFECTO (THE CONTROL CENTER)
# -----------------------------------------------------------------------------

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    
    # Update State
    user_data = await calculate_user_state(user_data)
    await save_user_data(user.id, user_data)
    
    afk_amount = user_data.get('pending_afk', 0)
    afk_msg = "Sistemas en espera..." if afk_amount < 1 else f"💰 **{afk_amount:.0f} HIVE** generados mientras dormías."
    
    is_premium = context.user_data.get('is_premium', False)
    rank = calculate_rank(user_data.get('nectar', 0))
    if is_premium: rank += " (VIP)"
    
    txt = get_text('es', 'dashboard_body',
        name=user.first_name,
        rank=rank,
        level=user_data.get('mining_level', 1),
        energy=int(user_data['energy']),
        max_energy=MAX_ENERGY_BASE,
        rate=MINING_RATE_BASE * user_data.get('mining_level', 1) * (2 if is_premium else 1),
        usd=user_data.get('usd_balance', 0.0),
        hive=user_data.get('nectar', 0),
        afk_msg=afk_msg
    )
    
    kb = []
    # Botón Principal Dinámico (Call to Action)
    if afk_amount > 10:
        kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else:
        kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE (TAP)", callback_data="mine_click")])
    
    # Zonas de Ingresos (Desplegadas)
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text('es', 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t3'), callback_data="tier_3")])
    
    # Utilidades
    kb.append([
        InlineKeyboardButton(get_text('es', 'btn_shop'), callback_data="shop_menu"),
        InlineKeyboardButton(get_text('es', 'btn_withdraw'), callback_data="withdraw")
    ])
    kb.append([
        InlineKeyboardButton(get_text('es', 'btn_profile'), callback_data="profile"), 
        InlineKeyboardButton(get_text('es', 'btn_team'), callback_data="team_menu")
    ])
    
    if update.callback_query:
        try: await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except: pass
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 7. MOTOR DE MINERÍA (ACTIVA & PASIVA)
# -----------------------------------------------------------------------------

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Cooldown Anti-Flood
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN:
        await query.answer("❄️ Enfriando...", show_alert=False)
        return
    context.user_data['last_mine_time'] = time.time()

    user_data = await db.get_user(user_id)
    user_data = await calculate_user_state(user_data) 
    
    cost = 20 
    if user_data['energy'] < cost:
        await query.answer("🔋 Batería Agotada. Recarga en la Tienda.", show_alert=True)
        return

    # Cálculo de Recompensa
    user_data['energy'] -= cost
    is_premium = context.user_data.get('is_premium', False)
    multiplier = 2.0 if is_premium else 1.0
    
    base_gain = MINING_RATE_BASE * 15 * multiplier
    is_crit = random.random() < 0.15 # 15% Chance de Crítico
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
        await asyncio.sleep(0.3)
        await query.message.edit_text(
            get_text('es', 'mining_active', bar="▓▓▓▓▓▓▓▓░░", percent=88, hash=block_hash),
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.2)
    except: pass 

    # Resultado
    final_txt = get_text('es', 'mining_success', gain=int(gain), cost=cost)
    if is_crit: final_txt += "\n🔥 **¡CRITICAL HIT! (x2.5)**"
    if is_premium: final_txt += "\n👑 **Bono Reina Aplicado**"
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")], [InlineKeyboardButton("🔙 DASHBOARD", callback_data="go_dashboard")]]
    await query.message.edit_text(final_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

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
    
    await query.answer(f"💰 +{amount} HIVE transferidos.", show_alert=True)
    await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 8. MENÚS DE ZONAS DE INGRESO (CPA/LEADS)
# -----------------------------------------------------------------------------

async def tier1_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("📺 TIMEBUCKS", url=LINKS['VALIDATOR_MAIN']), InlineKeyboardButton("💰 ADBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FREEBITCOIN", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("🌧 COINTIPLY", url=LINKS['COINTIPLY'])],
        [InlineKeyboardButton("🎮 GAMEHAG", url=LINKS['GAMEHAG']), InlineKeyboardButton("🎰 BETFURY", url=LINKS['BETFURY'])],
        [InlineKeyboardButton("💰 BC.GAME", url=LINKS['BCGAME']), InlineKeyboardButton("⚡ SPROUTGIGS", url=LINKS['SPROUTGIGS'])],
        [InlineKeyboardButton("📝 GOTRANSCRIPT", url=LINKS['GOTRANSCRIPT']), InlineKeyboardButton("⌨️ KOLOTIBABLO", url=LINKS['KOLOTIBABLO'])],
        [InlineKeyboardButton("⭐ SWAGBUCKS", url=LINKS['SWAGBUCKS']), InlineKeyboardButton("💵 FREECASH", url=LINKS['FREECASH'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS (VOLUMEN)**\nRealiza clicks rápidos y gana satoshis/centavos.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA (DATOS)**\nInstala estos nodos y gana dinero mientras duermes vendiendo ancho de banda.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier3_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🔥 BYBIT ($5.00)", url=LINKS['BYBIT'])],
        [InlineKeyboardButton("🏦 NEXO", url=LINKS['NEXO']), InlineKeyboardButton("💳 REVOLUT", url=LINKS['REVOLUT'])],
        [InlineKeyboardButton("💰 YOUHODLER", url=LINKS['YOUHODLER']), InlineKeyboardButton("🌍 WISE", url=LINKS['WISE'])],
        [InlineKeyboardButton("💲 AIRTM", url=LINKS['AIRTM']), InlineKeyboardButton("📧 GETRESPONSE", url=LINKS['GETRESPONSE'])],
        [InlineKeyboardButton("💹 PLUS500", url=LINKS['PLUS500']), InlineKeyboardButton("🤖 POLLO AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🔴 **ZONA 3: HIGH TICKET (COMISIONES)**\nRegistros financieros que pagan altas comisiones.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    await query.message.edit_text("🛰️ **CONECTANDO CON SERVIDOR CPA...**\nVerificando click ID en red de anunciantes...")
    await asyncio.sleep(2.0) 
    
    # Lógica de conversión del bono
    if not context.user_data.get('bonus_claimed'):
        context.user_data['bonus_claimed'] = True
        user_data['usd_balance'] = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ ¡Conversión Exitosa! ${BONUS_REWARD} acreditados.", show_alert=True)
    else:
        await query.answer("⚠️ Tarea enviada a revisión manual. Estado: PENDIENTE (24h).", show_alert=True)
        
    await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# 9. TIENDA, PAGOS Y GESTIÓN DE EQUIPO
# -----------------------------------------------------------------------------

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    hive = user_data.get('nectar', 0)
    
    txt = get_text('es', 'shop_body', hive=hive) 
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
        [InlineKeyboardButton("💳 PAGAR AHORA (SECURE CHECKOUT)", web_app=WebAppInfo(url=LINK_PAGO_GLOBAL))],
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
    await query.message.edit_text("📝 **MODO DE VERIFICACIÓN MANUAL**\n\nPor favor, pega el TXID de tu transacción aquí para que el sistema la rastree.")

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
    await query.message.edit_text(f"📡 **RED DE RECOLECCIÓN**\n\nInvita nodos a tu colmena y gana comisiones perpetuas.\n\n🔗 Tu enlace único:\n`{link}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")

async def offer_bonus_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.effective_user.language_code
    txt = get_text(lang, 'ask_bonus', bonus=BONUS_REWARD)
    kb = [
        [InlineKeyboardButton(get_text(lang, 'btn_claim_bonus', bonus=BONUS_REWARD), url=LINKS['VALIDATOR_MAIN'])],
        [InlineKeyboardButton("✅ VALIDAR MISIÓN", callback_data="bonus_done")]
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 10. ENRUTADOR CENTRAL DE EVENTOS (CORE LOGIC)
# -----------------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    # 1. Flujo Legal / Onboarding
    if data == "accept_legal":
        context.user_data['waiting_for_terms'] = False
        context.user_data['waiting_for_email'] = True
        await query.message.edit_text(get_text('es', 'ask_email'), parse_mode="Markdown")
        return
        
    if data == "reject_legal":
        await query.message.edit_text("❌ Acceso Denegado. Protocolo cancelado.")
        return

    # 2. Validación de Bono Inicial
    if data == "bonus_done":
        user_data = await db.get_user(user_id)
        if not context.user_data.get('bonus_claimed'):
            context.user_data['bonus_claimed'] = True
            new_balance = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
            user_data['usd_balance'] = new_balance
            await save_user_data(user_id, user_data)
            await query.answer(f"✅ ¡Bono de ${BONUS_REWARD} acreditado!", show_alert=True)
        else:
            await query.answer("⚠️ Ya reclamaste este bono.", show_alert=True)
        await show_dashboard(update, context)
        return

    # 3. Mapeo de Funciones del Dashboard
    handlers = {
        "go_dashboard": show_dashboard,
        "mine_click": mining_animation,
        "claim_afk": claim_afk,
        "verify_task_manual": verify_task_manual,
        "shop_menu": shop_menu,
        "buy_premium_info": buy_premium_info,
        "pay_crypto_info": pay_crypto_info,
        "confirm_crypto_wait": confirm_crypto_wait,
        "tier_1": tier1_menu,
        "tier_2": tier2_menu,
        "tier_3": tier3_menu,
        "team_menu": team_menu,
        "go_justificante": show_justificante
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
            await query.answer("❌ Saldo HIVE insuficiente. Mina más.", show_alert=True)
            
    elif data == "profile":
        await query.message.edit_text(f"👤 **PERFIL DE NODO**\nID: `{query.from_user.id}`\nEstado: Online\nReputación: 100%", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
        
    elif data == "withdraw":
        await query.answer("🔒 Retiro bloqueado. Mínimo $10.00 USD requeridos.", show_alert=True)
    
    try: await query.answer()
    except: pass

async def show_justificante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_text = get_text('es', 'justificante_header')
    log_text += f"🟢 `[{now} 10:15]` **+$0.01 USD** (Partner Network)\n✅ **ESTADO:** Validado en Blockchain."
    kb = [[InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]]
    await update.callback_query.message.edit_text(log_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 11. COMANDOS DE MANTENIMIENTO
# -----------------------------------------------------------------------------

async def help_command(u, c): await u.message.reply_text("Sistema TheOneHive v91.0\nUsa /start para reiniciar el núcleo.")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset de sesión completado.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Herramienta de Marketing Masivo (Solo Admin)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    msg = update.message.text.replace("/broadcast", "").strip()
    if not msg:
        await update.message.reply_text("❌ Uso: /broadcast <mensaje de marketing>")
        return
    await update.message.reply_text(f"📢 **MENSAJE ENVIADO A LA RED:**\n\n{msg}")
