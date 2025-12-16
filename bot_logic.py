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
# CONFIGURACIÓN DE LOGS Y ENTORNO
# -----------------------------------------------------------------------------
logger = logging.getLogger("HiveLogic")
logger.setLevel(logging.INFO)

# 1. SEGURIDAD: ID de Administrador (Desde Render o Default 0)
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except ValueError:
    logger.warning("⚠️ ADMIN_ID no configurado o inválido. Usando 0.")
    ADMIN_ID = 0

# 2. BILLETERA CRIPTO (USDT TRC20)
# Se lee de la variable de entorno para seguridad máxima.
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "⚠️ ERROR: CONFIGURAR WALLET_USDT EN RENDER")

# 3. ENLACE DE PAGO PAYPAL (NCP)
# Enlace profesional para el botón nativo.
LINK_PAGO_GLOBAL = os.getenv("LINK_PAYPAL", "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC")

# -----------------------------------------------------------------------------
# ECONOMÍA Y MECÁNICAS DE JUEGO (TOKENOMICS)
# -----------------------------------------------------------------------------
INITIAL_USD = 0.00          # Saldo inicial real
INITIAL_HIVE = 500          # Saldo inicial de juego
BONUS_REWARD = 0.05         # Recompensa por primera validación

# Configuración del Motor de Minería
MINING_RATE_BASE = 1.5      # HIVE por segundo (Hashrate base)
MAX_ENERGY_BASE = 500       # Capacidad máxima de energía
ENERGY_REGEN = 1            # Puntos de energía regenerados por segundo
AFK_CAP_HOURS = 6           # Tiempo máximo de minería pasiva (horas)
MINING_COOLDOWN = 1.5       # Segundos entre clicks para evitar bots

# Costos en la Tienda
COST_PREMIUM_MONTH = 10     # Costo en USD
COST_ENERGY_REFILL = 500    # Costo en HIVE
COST_LEVEL_UP = 5000        # Costo en HIVE (Futuro)

# Assets Visuales
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# -----------------------------------------------------------------------------
# ARSENAL MAESTRO DE ENLACES (MONETIZACIÓN)
# -----------------------------------------------------------------------------
LINKS = {
    # --- VALIDACIÓN PRINCIPAL ---
    'VALIDATOR_MAIN': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    
    # --- ZONA 1: MICRO-TAREAS (CLICKS) ---
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744", 
    'COINTIPLY': "https://cointiply.com/r/jR1L6y", 
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://betfury.io/?r=6664969919f42d20e7297e29",
    
    # --- ZONA 2: MINERÍA PASIVA (NODOS) ---
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",
    'GOTRANSCRIPT': "https://gotranscript.com/r/7667434",
    'KOLOTIBABLO': "http://getcaptchajob.com/30nrmt1xpj",
    'EVERVE': "https://everve.net/ref/1950045/",
    
    # --- ZONA 3: HIGH TICKET & FINTECH ---
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
    
    # --- OFERTAS VIP ---
    'VIP_OFFER_1': os.getenv("LINK_BYBIT", "https://www.bybit.com/invite?ref=BBJWAX4"),
}

# -----------------------------------------------------------------------------
# TEXTOS NEUROLINGÜÍSTICOS Y COPYWRITING
# -----------------------------------------------------------------------------
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE: ACTIVADO**\n"
            "──────────────────────────\n\n"
            "Saludos, **{name}**. Has salido de la Matrix.\n"
            "La mayoría pierde el tiempo gratis en internet. Aquí, tu tiempo genera **VALOR REAL**.\n\n"
            "💎 **TU ESTRATEGIA DUAL DE INGRESOS:**\n\n"
            "1️⃣ **Mina Néctar (HIVE):** Es el combustible de la red. Lo usas para comprar mejoras y licencias.\n"
            "2️⃣ **Zonas de Misión ($USD):** Tareas verificadas de nuestros partners que te pagan Dólares reales.\n"
            "3️⃣ **Escala:** Usa tu HIVE para comprar la 'Licencia de Reina' y multiplicar tus ganancias x2.\n\n"
            "🛡️ **FASE 1: SINCRONIZACIÓN DE NODO**\n"
            "Estamos estableciendo un canal seguro con tu billetera...\n\n"
            "👇 **PARA CONTINUAR, ENVÍA TU CÓDIGO DE ACCESO AL CHAT:**"
        ),
        'ask_terms': (
            "✅ **ENLACE ESTABLECIDO CON ÉXITO**\n"
            "───────────────────────\n"
            "Antes de asignarte tu primera tarea pagada, debes aceptar el **Protocolo de la Colmena**:\n\n"
            "• Usarás datos reales en los registros.\n"
            "• No usarás VPNs, Proxies ni multicuentas.\n"
            "• Entiendes que el esfuerzo genera la recompensa.\n\n"
            "¿Aceptas el desafío?"
        ),
        'ask_email': (
            "🤝 **PROTOCOLO ACEPTADO**\n"
            "───────────────────────\n"
            "📧 **ÚLTIMO PASO DE CONFIGURACIÓN:**\n\n"
            "Escribe tu **CORREO ELECTRÓNICO** principal.\n"
            "*(Lo usaremos estrictamente para notificarte cuando recibas un pago o un Airdrop importante)*."
        ),
        'ask_bonus': (
            "🎉 **¡CUENTA 100% ACTIVA!**\n"
            "───────────────────────\n"
            "Tu saldo actual es: **$0.00 USD**\n\n"
            "🎁 **TU PRIMERA TAREA PAGADA (BONO DE BIENVENIDA):**\n"
            "Hemos reservado un bono de **${bonus} USD** exclusivamente para ti. Para desbloquearlo, debes validar tu identidad en nuestro partner principal.\n\n"
            "1. Entra al enlace oficial.\n"
            "2. Regístrate o completa la validación.\n"
            "3. Vuelve aquí y pulsa 'YA LA COMPLETÉ' para recibir tus primeros $0.05."
        ),
        'btn_claim_bonus': "🚀 IR A LA MISIÓN (GANAR ${bonus})",
        
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
        'mining_success': "✅ **BLOQUE VALIDADO**\n\n💰 **Recompensa:** +{gain} HIVE\n🔋 **Consumo:** -{cost} Energía\n📈 **XP:** +10 Puntos",
        
        'payment_card_info': """
💳 **PASARELA DE PAGO SEGURA (PAYPAL PRO)**
──────────────────────────
**Estás comprando:** Licencia de Reina (Vitalicia)
**Beneficio:** Minería x2 + Retiros Express

🛡️ **Protección al Comprador:**
El pago se procesa en una ventana segura de PayPal. TheOneHive no almacena tus datos financieros.

👇 **INSTRUCCIONES:**
1. Pulsa el botón **"PAGAR AHORA"** de abajo.
2. Completa el pago de **$10.00 USD**.
3. Regresa aquí y pulsa el botón **"YA PAGUÉ"** para activar.
""",
        'payment_crypto_info': """
💎 **DEPOSITO TETHER (USDT)**
──────────────────────────
Red: **TRON (TRC20)**
Billetera Destino:
`{wallet}`

⚠️ **Instrucciones de Pago:**
1. Envía exactamente **10 USDT**.
2. Copia el **Hash de Transacción (TXID)** después de enviar.
3. Pégalo aquí abajo para la validación automática en Blockchain.
""",
        'shop_body': """
🏪 **MERCADO DE RECURSOS**
──────────────────────────
*Saldo Disponible:* {hive} HIVE

⚡ **RECARGAR ENERGÍA (500 HIVE)**
Recupera 100 puntos de batería instantáneamente para seguir minando.

👑 **LICENCIA DE REINA ($10 USD)**
Multiplicador x2 permanente en todas las ganancias y acceso a retiros rápidos.

👷 **CERTIFICADO DE MAESTRO (50k HIVE)**
Desbloquea tareas de alto valor (Tier 2).

💎 **NFT DE LA COLMENA (100k HIVE)**
Te otorga el 30% de comisión de referidos de por vida.
""",
        'justificante_header': "📜 **HISTORIAL DE INGRESOS (TRANSPARENCIA)**\n──────────────────────────\nAuditoría en tiempo real de la Colmena:\n\n",
        
        # Botones del Menú Principal
        'btn_t1': "🟢 ZONA 1 (Clicks)", 
        'btn_t2': "🟡 ZONA 2 (Pasivo)", 
        'btn_t3': "🔴 ZONA 3 (Pro)",
        'btn_shop': "🛒 TIENDA / MEJORAS",
        'btn_justificante': "📜 JUSTIFICANTE",
        'btn_back': "🔙 VOLVER AL MENU", 
        'btn_withdraw': "💸 RETIRAR SALDO", 
        'btn_team': "👥 MI EQUIPO", 
        'btn_profile': "👤 MI PERFIL"
    }
}

# -----------------------------------------------------------------------------
# FUNCIONES UTILITARIAS Y MATEMÁTICAS
# -----------------------------------------------------------------------------

def get_text(lang, key, **kwargs):
    t = TEXTS.get('es', {}).get(key, key)
    try: return t.format(**kwargs)
    except: return t

def generate_hash():
    """Genera un hash visualmente realista para la minería"""
    return "0x" + ''.join(random.choices("ABCDEF0123456789", k=18))

def generate_captcha():
    """Genera código de seguridad simple"""
    return f"HIVE-{random.randint(100, 999)}"

async def calculate_user_state(user_data):
    """
    Motor matemático: Calcula cuánta energía se regeneró y cuánto minaron los
    NFTs mientras el usuario estaba desconectado (AFK).
    """
    now = time.time()
    last_update = user_data.get('last_update_ts', now)
    elapsed = now - last_update
    
    # 1. Regenerar Energía (Clamp entre 0 y Max)
    current_energy = user_data.get('energy', MAX_ENERGY_BASE)
    max_e = user_data.get('max_energy', MAX_ENERGY_BASE)
    
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
    """Guarda los datos en la base de datos (Redis)"""
    if hasattr(db, 'r') and db.r:
        await db.r.set(f"user:{user_id}", json.dumps(data))

async def check_daily_streak(user_id):
    """Calcula la racha diaria de conexiones"""
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
        user_data['nectar'] = int(user_data.get('nectar', 0)) + (new_streak * 10) # Bono HIVE por racha
        await save_user_data(user_id, user_data)
        return new_streak
    else:
        user_data['streak_days'] = 1
        user_data['last_streak_date'] = today_str
        await save_user_data(user_id, user_data)
        return 1

# -----------------------------------------------------------------------------
# HANDLERS DE COMANDOS Y MENSAJES DE TEXTO
# -----------------------------------------------------------------------------

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
    
    # 1. Verificación Captcha
    expected = context.user_data.get('captcha')
    if expected and text == expected:
        context.user_data['captcha'] = None
        await show_dashboard(update, context)
        return

    # 2. Comando Start manual
    if text.upper() == "/START":
        await start(update, context)
        return
        
    # 3. Manejo de Hash de Crypto (Pago Manual)
    if context.user_data.get('waiting_for_hash'):
        context.user_data['waiting_for_hash'] = False
        # Validación simple de longitud de hash para filtrar spam
        if len(text) > 10:
            context.user_data['is_premium'] = True
            await update.message.reply_text(
                "✅ **HASH RECIBIDO CORRECTAMENTE**\n\nEl sistema está validando la transacción en la Blockchain (3-6 confirmaciones). Tu licencia de Reina se activará automáticamente en breve.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("VOLVER AL NODO", callback_data="go_dashboard")]])
            )
        else:
            await update.message.reply_text("❌ **HASH INVÁLIDO.** Por favor, verifica el código TXID y envíalo de nuevo.")
        return

    # 4. Fallback al Dashboard si el usuario está perdido
    user_data = await db.get_user(user.id)
    if user_data:
        await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# DASHBOARD PRINCIPAL Y LÓGICA DE VISUALIZACIÓN
# -----------------------------------------------------------------------------

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)
    
    # Recalcular estado actual (Energía/AFK) antes de mostrar
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
    # Botón Principal Dinámico: Recolectar AFK o Minar
    if afk_amount > 10:
        kb.append([InlineKeyboardButton(f"💰 RECOLECTAR (+{int(afk_amount)})", callback_data="claim_afk")])
    else:
        kb.append([InlineKeyboardButton("⛏️ MINAR BLOQUE (TAP)", callback_data="mine_click")])
    
    # Zonas de Tareas (Restauradas)
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t1'), callback_data="tier_1"), InlineKeyboardButton(get_text('es', 'btn_t2'), callback_data="tier_2")])
    kb.append([InlineKeyboardButton(get_text('es', 'btn_t3'), callback_data="tier_3")])
    
    # Herramientas
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
# MOTOR DE MINERÍA ACTIVA (TAP) CON ANIMACIÓN
# -----------------------------------------------------------------------------

async def mining_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # 1. Protección Anti-Flood (Cooldown)
    last_mine = context.user_data.get('last_mine_time', 0)
    if time.time() - last_mine < MINING_COOLDOWN:
        await query.answer("❄️ Enfriando sistemas... Espera.", show_alert=False)
        return
    context.user_data['last_mine_time'] = time.time()

    user_data = await db.get_user(user_id)
    user_data = await calculate_user_state(user_data) # Actualizar energía
    
    cost = 20 # Costo de energía por operación
    if user_data['energy'] < cost:
        await query.answer("🔋 Batería Agotada. Compra energía o espera.", show_alert=True)
        return

    # 2. Lógica de Ganancia
    user_data['energy'] -= cost
    is_premium = context.user_data.get('is_premium', False)
    multiplier = 2.0 if is_premium else 1.0
    
    base_gain = MINING_RATE_BASE * 15 * multiplier
    # Probabilidad de golpe crítico (Gamificación)
    is_crit = random.random() < 0.15
    gain = base_gain * 2.5 if is_crit else base_gain
    
    user_data['nectar'] = int(user_data.get('nectar', 0) + gain)
    await save_user_data(user_id, user_data)

    # 3. Animación Visual (Barra de progreso)
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

    # 4. Resultado Final
    final_txt = get_text('es', 'mining_success', gain=int(gain), cost=cost)
    if is_crit: final_txt += "\n🔥 **¡CRITICAL HIT! (x2.5)**"
    if is_premium: final_txt += "\n👑 **Bono Reina Aplicado**"
    
    kb = [[InlineKeyboardButton("⛏️ SEGUIR MINANDO", callback_data="mine_click")],
          [InlineKeyboardButton("🔙 PANEL DE CONTROL", callback_data="go_dashboard")]]
          
    await query.message.edit_text(final_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def claim_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recolecta lo minado pasivamente"""
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

# -----------------------------------------------------------------------------
# MENÚS DE TAREAS Y ZONAS (CPA)
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
    await query.message.edit_text("🟢 **ZONA 1: MICRO-TAREAS**\nGanancia rápida por click.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def tier2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kb = [
        [InlineKeyboardButton("🐝 HONEYGAIN", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PACKETSTREAM", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ PAWNS", url=LINKS['PAWNS']), InlineKeyboardButton("📶 TRAFFMONETIZER", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("📱 PAIDWORK", url=LINKS['PAIDWORK']), InlineKeyboardButton("✅ VALIDAR TAREA ($)", callback_data="verify_task_manual")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="go_dashboard")]
    ]
    await query.message.edit_text("🟡 **ZONA 2: MINERÍA PASIVA**\nInstala y gana sin hacer nada (AFK).", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

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
    await query.message.edit_text("🔴 **ZONA 3: HIGH TICKET**\nPagos altos por registro.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def verify_task_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simulación de verificación de tarea con retraso para realismo"""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await db.get_user(user_id)
    
    await query.message.edit_text("🛰️ **CONECTANDO CON SERVIDOR CPA...**\nVerificando click ID...")
    await asyncio.sleep(2.0) 
    
    # Primera vez: Bono de bienvenida
    if not context.user_data.get('bonus_claimed'):
        context.user_data['bonus_claimed'] = True
        user_data['usd_balance'] = float(user_data.get('usd_balance', 0)) + BONUS_REWARD
        await save_user_data(user_id, user_data)
        await query.answer(f"✅ ¡Verificado! ${BONUS_REWARD} acreditados.", show_alert=True)
    else:
        # Siguientes veces: Mensaje de espera
        await query.answer("⚠️ Tarea en revisión. El saldo se liberará en 24h.", show_alert=True)
        
    await show_dashboard(update, context)

# -----------------------------------------------------------------------------
# TIENDA, PAGOS Y PERFIL
# -----------------------------------------------------------------------------

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
        # Botón Nativo PayPal
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

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
    await query.message.edit_text(f"📡 **RED DE RECOLECCIÓN**\n\n🔗 Tu enlace:\n`{link}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")

# -----------------------------------------------------------------------------
# ENRUTADOR CENTRAL DE EVENTOS
# -----------------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # Mapeo eficiente de funciones
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
            await query.answer("❌ Saldo HIVE insuficiente.", show_alert=True)
            
    elif data == "profile":
        await query.message.edit_text(f"👤 **NODO:** `{query.from_user.id}`\nEstado: Activo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="go_dashboard")]]), parse_mode="Markdown")
        
    elif data == "withdraw":
        await query.answer("🔒 Mínimo de retiro: $10.00 USD", show_alert=True)
    
    # Prevenir errores si el botón no hace nada
    try: await query.answer()
    except: pass

# --- COMANDOS FINALES ---
async def help_command(u, c): await u.message.reply_text("Sistema TheOneHive v80.0\nUsa /start para reiniciar.")
async def invite_command(u, c): await team_menu(u, c)
async def reset_command(u, c): c.user_data.clear(); await u.message.reply_text("Reset OK.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    msg = update.message.text.replace("/broadcast", "").strip()
    if not msg:
        await update.message.reply_text("❌ Uso: /broadcast <mensaje>")
        return
    # Aquí iría el bucle real de envío a la DB
    await update.message.reply_text(f"📢 Mensaje programado:\n\n{msg}")
