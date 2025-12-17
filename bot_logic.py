import os
import logging
import asyncio
import json
import time
import random
import datetime
from typing import List, Optional

# Frameworks externos
from fastapi import FastAPI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    filters
)
from telegram.error import BadRequest, Forbidden
import redis.asyncio as redis

# ==========================================
# 1. CONFIGURACIÓN DEL SERVIDOR (RENDER)
# ==========================================
app = FastAPI()

@app.get("/")
async def health_check():
    """Endpoint para que Render sepa que estamos vivos."""
    return {
        "system": "The One Hive",
        "status": "Operational",
        "timestamp": time.time()
    }

# ==========================================
# 2. LOGGING Y CONSTANTES
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("HiveMaster")

# Identificación
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Economía del Juego
MAX_ENERGY_BASE = 500
ENERGY_REGEN_PER_SEC = 1.0  
AFK_CAP_HOURS = 6
MINING_COOLDOWN = 1.0  
MINING_COST = 20
BASE_REWARD = 5
VARIABILITY = 0.4
DAILY_BONUS_BASE = 100

# Seguridad
MAX_CLICKS_PER_MINUTE = 60  
FRAUD_PENALTY_HOURS = 24

# Textos de Lore / Psicología
STATES = {
    1: "Explorador (Nivel 1)",
    2: "Operador (Nivel 2)",
    3: "Insider (Nivel 3)",
    4: "Nodo Maestro (Nivel 4)",
    5: "Génesis (Nivel 5)"
}

# Base de Enlaces Completa
LINKS = {
    # TIER 1 - TAREAS RÁPIDAS
    'TIMEBUCKS': os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472"),
    'ADBTC': "https://r.adbtc.top/3284589",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'COINPAYU': "https://www.coinpayu.com/?r=Josesitoto",
    
    # TIER 2 - PASIVOS
    'HONEYGAIN': "https://join.honeygain.com/ALEJOE9F32",
    'PACKETSTREAM': "https://packetstream.io/?psr=7hQT",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    
    # TIER 3 - HIGH TICKET
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'NEXO': "https://nexo.com/ref/rbkekqnarx?src=android-link",
    'REVOLUT': "https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'WISE': "https://wise.com/invite/ahpc/josealejandrop73",
    'AIRTM': "https://app.airtm.com/ivt/jos3vkujiyj",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'POLLOAI': "https://pollo.ai/invitation-landing?invite_code=wI5YZK"
}

IMG_WELCOME = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# ==========================================
# 3. GESTIÓN DE BASE DE DATOS (REDIS)
# ==========================================
r = None

async def init_db():
    global r
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        logger.info("✅ Conexión a Redis exitosa.")
    except Exception as e:
        logger.error(f"❌ Error fatal conectando a Redis: {e}")

async def get_user_data(user_id: int) -> dict:
    """Recupera los datos del usuario o devuelve None."""
    raw = await r.get(f"user:{user_id}")
    if raw:
        return json.loads(raw)
    return None

async def save_user_data(user_id: int, data: dict):
    """Guarda los datos del usuario en Redis."""
    await r.set(f"user:{user_id}", json.dumps(data))

async def get_all_users() -> List[int]:
    """Obtiene todos los IDs de usuarios registrados (para broadcast)."""
    keys = await r.keys("user:*")
    return [int(k.split(":")[1]) for k in keys]

# ==========================================
# 4. LÓGICA DE NEGOCIO Y ESTADOS
# ==========================================

def calculate_swarm_multiplier(referrals_count: int) -> float:
    """Calcula el multiplicador basado en el tamaño del equipo."""
    # Curva logarítmica suave: empieza rápido, luego se estabiliza
    bonus = min(referrals_count, 100) * 0.05
    return round(1.0 + bonus, 2)

async def update_user_state(user_data: dict) -> dict:
    """
    Función crítica: Actualiza energía, tokens AFK y estados.
    Se ejecuta cada vez que el usuario interactúa.
    """
    now = time.time()
    last_ts = user_data.get('last_update_ts', now)
    elapsed = now - last_ts
    
    # 1. Regeneración de Energía
    max_energy = user_data.get('max_energy', MAX_ENERGY_BASE)
    current_energy = user_data.get('energy', 0)
    
    if current_energy < max_energy:
        recovered = elapsed * ENERGY_REGEN_PER_SEC
        user_data['energy'] = min(max_energy, current_energy + recovered)
    
    # 2. Cálculo AFK (Token Farming)
    # Solo produce si no está baneado
    if not user_data.get('is_banned', False):
        state_level = user_data.get('state', 1)
        ref_bonus = calculate_swarm_multiplier(len(user_data.get('referrals', [])))
        
        # Fórmula: Nivel * Base * Multiplicador
        hourly_rate = state_level * 10 * ref_bonus
        
        # Cap de tiempo
        effective_time_hours = min(elapsed, AFK_CAP_HOURS * 3600) / 3600
        
        if effective_time_hours > 0.01: # Mínimo significativo
            produced = effective_time_hours * hourly_rate
            user_data['tokens_locked'] = user_data.get('tokens_locked', 0) + produced
            
    # Actualizar timestamp
    user_data['last_update_ts'] = now
    return user_data

def render_progress_bar(value, total, length=12):
    percent = max(0, min(value / total, 1.0))
    filled = int(length * percent)
    empty = length - filled
    return "█" * filled + "▒" * empty

# ==========================================
# 5. HANDLERS DE COMANDOS (USUARIO)
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Verificar Referido
    args = context.args
    referrer_id = None
    if args and args[0].isdigit():
        possible_referrer = int(args[0])
        if possible_referrer != user_id:
            referrer_id = possible_referrer

    # Cargar o Crear Usuario
    data = await get_user_data(user_id)
    
    if not data:
        # CREACIÓN DE NUEVO PERFIL
        logger.info(f"Nuevo usuario detectado: {user_id} - {user.first_name}")
        data = {
            "id": user_id,
            "username": user.username,
            "first_name": user.first_name,
            "joined_at": time.time(),
            "referrer_id": referrer_id,
            "referrals": [],
            
            # Economía
            "nectar": 50.0,
            "usd_balance": 0.0,
            "energy": MAX_ENERGY_BASE,
            "tokens_locked": 0.0,
            
            # Estado
            "state": 1,
            "progress_xp": 0,
            "max_energy": MAX_ENERGY_BASE,
            
            # Gamification
            "daily_streak": 0,
            "last_daily_claim": 0,
            "last_update_ts": time.time(),
            
            # Seguridad
            "is_banned": False,
            "warnings": 0,
            "click_timestamps": [] 
        }
        
        # Procesar Referido
        if referrer_id:
            ref_data = await get_user_data(referrer_id)
            if ref_data:
                ref_data['referrals'].append(user_id)
                # Bono inmediato al referido
                ref_data['nectar'] += 100 
                await save_user_data(referrer_id, ref_data)
                try:
                    await context.bot.send_message(referrer_id, f"👥 **¡Nuevo Nodo Reclutado!**\n{user.first_name} se unió a tu enjambre. +100 HIVE", parse_mode="Markdown")
                except:
                    pass

        await save_user_data(user_id, data)
        
        # SECUENCIA DE BIENVENIDA (CAPTCHA)
        captcha_code = f"HIVE-{random.randint(1000,9999)}"
        context.user_data['captcha_correct'] = captcha_code
        
        welcome_msg = (
            f"🟢 **CONEXIÓN ESTABLECIDA**\n\n"
            f"Identidad: {user.first_name}\n"
            f"Estado: No Verificado\n\n"
            f"El Sistema Hive prioriza la inteligencia humana sobre la artificial.\n"
            f"Para activar tu nodo de minería, introduce el siguiente código de seguridad:\n\n"
            f"`{captcha_code}`"
        )
        
        try:
            await update.message.reply_photo(photo=IMG_WELCOME, caption=welcome_msg, parse_mode="Markdown")
        except:
            await update.message.reply_text(welcome_msg, parse_mode="Markdown")
            
        return

    # Si ya existe, mostrar dashboard
    await show_dashboard(update, context)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = await get_user_data(user_id)
    
    if data.get('is_banned'):
        await update.effective_message.reply_text("⛔ **ACCESO DENEGADO**\nTu cuenta ha sido suspendida por actividad sospechosa.")
        return

    # Actualizar cálculos
    data = await update_user_state(data)
    await save_user_data(user_id, data)
    
    # Preparar visualización
    lvl = data['state']
    role = STATES.get(lvl, "Desconocido")
    energy_bar = render_progress_bar(data['energy'], data['max_energy'])
    xp_bar = render_progress_bar(data['progress_xp'], 100)
    
    multiplier = calculate_swarm_multiplier(len(data['referrals']))
    
    txt = (
        f"🐝 **PANEL DE CONTROL PRINCIPAL**\n"
        f"👤 **Operador:** {data['first_name']}\n"
        f"🎖 **Rango:** {role}\n"
        f"⚡ **Energía:** `{int(data['energy'])}` / {data['max_energy']}\n"
        f"{energy_bar}\n\n"
        
        f"💰 **RECURSOS**\n"
        f"• Saldo USD: `${data['usd_balance']:.2f}`\n"
        f"• HIVE Tokens: `{int(data['nectar'])}`\n"
        f"• Bloqueados (AFK): `{int(data['tokens_locked'])}`\n\n"
        
        f"📊 **ESTADÍSTICAS**\n"
        f"• Equipo: {len(data['referrals'])} nodos\n"
        f"• Multiplicador: x{multiplier}\n"
        f"• Progreso Nv {lvl+1}: {xp_bar} {data['progress_xp']}%\n"
    )
    
    kb = [
        [InlineKeyboardButton("⛏️ INICIAR MINERÍA (TIERS)", callback_data="open_tiers")],
        [InlineKeyboardButton("🔓 RECLAMAR AFK", callback_data="claim_afk"), InlineKeyboardButton("🎁 BONUS DIARIO", callback_data="daily_bonus")],
        [InlineKeyboardButton("👥 EQUIPO", callback_data="team_view"), InlineKeyboardButton("🛒 TIENDA", callback_data="shop_view")],
        [InlineKeyboardButton("🏦 RETIRAR FONDOS", callback_data="withdraw_menu")]
    ]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==========================================
# 6. ACCIONES Y MECÁNICAS (MINERÍA, AFK, SHOP)
# ==========================================

async def claim_afk_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = await get_user_data(user_id)
    
    # Actualizar antes de reclamar para asegurar el último segundo
    data = await update_user_state(data)
    
    locked = data.get('tokens_locked', 0)
    if locked < 1:
        await query.answer("⚠️ No hay suficientes recursos acumulados.", show_alert=True)
        return
        
    data['nectar'] += locked
    data['tokens_locked'] = 0
    await save_user_data(user_id, data)
    
    await query.answer(f"✅ Has recolectado {int(locked)} HIVE pasivos.", show_alert=True)
    await show_dashboard(update, context)

async def daily_bonus_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = await get_user_data(user_id)
    
    now = time.time()
    last_claim = data.get('last_daily_claim', 0)
    
    # Verificar si pasaron 24 horas (86400 segundos)
    if now - last_claim < 86400:
        next_claim = 86400 - (now - last_claim)
        hours = int(next_claim // 3600)
        minutes = int((next_claim % 3600) // 60)
        await query.answer(f"⏳ Vuelve en {hours}h {minutes}m", show_alert=True)
        return
        
    # Calcular Racha
    if now - last_claim < 172800: # Menos de 48 horas (seguido)
        data['daily_streak'] += 1
    else:
        data['daily_streak'] = 1
        
    bonus = DAILY_BONUS_BASE + (data['daily_streak'] * 10)
    data['nectar'] += bonus
    data['last_daily_claim'] = now
    
    await save_user_data(user_id, data)
    await query.answer(f"📅 ¡Día {data['daily_streak']}! Recibiste +{bonus} HIVE", show_alert=True)
    await show_dashboard(update, context)

async def mine_click_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Acción de minería manual con Anti-Fraude."""
    query = update.callback_query
    user_id = query.from_user.id
    data = await get_user_data(user_id)
    
    # --- ANTI FRAUDE LAYER ---
    now = time.time()
    timestamps = data.get('click_timestamps', [])
    # Limpiar timestamps viejos (> 60 segundos)
    timestamps = [t for t in timestamps if now - t < 60]
    timestamps.append(now)
    data['click_timestamps'] = timestamps
    
    if len(timestamps) > MAX_CLICKS_PER_MINUTE:
        await query.answer("🚨 ALERTA: Velocidad inhumana detectada. Enfriando...", show_alert=True)
        return
    # -------------------------

    data = await update_user_state(data)
    
    if data['energy'] < MINING_COST:
        await query.answer("⚡ Energía agotada. Necesitas recargar.", show_alert=True)
        return

    # Ejecutar Gasto
    data['energy'] -= MINING_COST
    
    # Calcular Ganancia
    ref_bonus = calculate_swarm_multiplier(len(data['referrals']))
    base_gain = BASE_REWARD * data['state']
    variability = random.uniform(-VARIABILITY, VARIABILITY)
    final_gain = int(base_gain * (1 + variability) * ref_bonus)
    
    data['nectar'] += final_gain
    
    # Progreso de Nivel (XP)
    data['progress_xp'] += 2
    if data['progress_xp'] >= 100:
        if data['state'] < 5:
            data['state'] += 1
            data['progress_xp'] = 0
            # Premio por subir nivel
            data['max_energy'] += 100
            data['energy'] = data['max_energy']
            await query.message.reply_text(f"🆙 **¡NIVEL ASCENDIDO!**\nAhora eres rango: {STATES[data['state']]}")

    await save_user_data(user_id, data)
    await query.answer(f"⛏️ +{final_gain} HIVE")
    await show_dashboard(update, context)

# ==========================================
# 7. MENÚS DE NAVEGACIÓN (TIERS Y TIENDA)
# ==========================================

async def open_tiers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 TIER 1 (Fácil)", callback_data="tier_1")],
        [InlineKeyboardButton("🟡 TIER 2 (Medio)", callback_data="tier_2")],
        [InlineKeyboardButton("🔴 TIER 3 (Pro)", callback_data="tier_3")],
        [InlineKeyboardButton("🔙 Volver al Panel", callback_data="back_home")]
    ]
    await update.callback_query.message.edit_text(
        "📂 **SELECTOR DE TAREAS**\n\nSelecciona tu nivel de acceso para visualizar las oportunidades de minería disponibles.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def tier_1_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⛏️ MINAR AHORA (TAP)", callback_data="mine_tap")],
        [InlineKeyboardButton("📺 Timebucks", url=LINKS['TIMEBUCKS']), InlineKeyboardButton("💰 AdBTC", url=LINKS['ADBTC'])],
        [InlineKeyboardButton("🎲 FreeBitcoin", url=LINKS['FREEBITCOIN']), InlineKeyboardButton("👁️ CoinPayU", url=LINKS['COINPAYU'])],
        [InlineKeyboardButton("🔙 Atrás", callback_data="open_tiers")]
    ]
    await update.callback_query.message.edit_text("🟢 **TIER 1: INICIACIÓN**", reply_markup=InlineKeyboardMarkup(kb))

async def tier_2_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🐝 Honeygain", url=LINKS['HONEYGAIN']), InlineKeyboardButton("📦 PacketStream", url=LINKS['PACKETSTREAM'])],
        [InlineKeyboardButton("♟️ Pawns.app", url=LINKS['PAWNS']), InlineKeyboardButton("🚦 TraffMonetizer", url=LINKS['TRAFFMONETIZER'])],
        [InlineKeyboardButton("💼 Paidwork", url=LINKS['PAIDWORK'])],
        [InlineKeyboardButton("🔙 Atrás", callback_data="open_tiers")]
    ]
    await update.callback_query.message.edit_text("🟡 **TIER 2: OPERACIONES PASIVAS**", reply_markup=InlineKeyboardMarkup(kb))

async def tier_3_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📈 Bybit", url=LINKS['BYBIT']), InlineKeyboardButton("🏦 Nexo", url=LINKS['NEXO'])],
        [InlineKeyboardButton("💳 Revolut", url=LINKS['REVOLUT']), InlineKeyboardButton("🦉 Wise", url=LINKS['WISE'])],
        [InlineKeyboardButton("☁️ Airtm", url=LINKS['AIRTM']), InlineKeyboardButton("🐔 Pollo AI", url=LINKS['POLLOAI'])],
        [InlineKeyboardButton("🔙 Atrás", callback_data="open_tiers")]
    ]
    await update.callback_query.message.edit_text("🔴 **TIER 3: HIGH YIELD**", reply_markup=InlineKeyboardMarkup(kb))

async def shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú de Tienda (Expandible)"""
    kb = [
        [InlineKeyboardButton("⚡ Recarga Energía (1000 HIVE)", callback_data="buy_energy")],
        [InlineKeyboardButton("🛡️ Escudo Anti-Ban (5000 HIVE)", callback_data="buy_shield")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_home")]
    ]
    await update.callback_query.message.edit_text("🛒 **TIENDA DE RECURSOS**\n\nIntercambia tus tokens minados por mejoras para tu nodo.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def team_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = await get_user_data(user_id)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    txt = (
        f"👥 **GESTIÓN DE EQUIPO**\n\n"
        f"Tus referidos directos: **{len(data['referrals'])}**\n"
        f"Bono de Potencia actual: **x{calculate_swarm_multiplier(len(data['referrals']))}**\n\n"
        f"🔗 **Tu Enlace de Reclutamiento:**\n`{link}`\n\n"
        f"Recibes +100 HIVE por invitado y un % permanente de su producción."
    )
    kb = [[InlineKeyboardButton("🔙 Volver", callback_data="back_home")]]
    await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ==========================================
# 8. PANEL DE ADMINISTRACIÓN (SECURE)
# ==========================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    users = await get_all_users()
    total_users = len(users)
    total_hive = 0
    
    await update.message.reply_text(f"📊 **ESTADÍSTICAS GLOBALES**\n\nUsuarios Totales: {total_users}\nCalculando economía...", parse_mode="Markdown")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /broadcast <mensaje>"""
    if update.effective_user.id != ADMIN_ID: return
    
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("❌ Uso: /broadcast <mensaje>")
        return
        
    users = await get_all_users()
    success = 0
    await update.message.reply_text(f"📢 Iniciando difusión a {len(users)} usuarios...")
    
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 **ANUNCIO OFICIAL**\n\n{msg}", parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05) # Evitar flood limits
        except Exception:
            pass
            
    await update.message.reply_text(f"✅ Difusión completada. Recibidos: {success}/{len(users)}")

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /addbalance <id> <monto>"""
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        data = await get_user_data(target_id)
        if data:
            data['usd_balance'] += amount
            await save_user_data(target_id, data)
            await update.message.reply_text(f"✅ Se añadieron ${amount} al usuario {target_id}")
            await context.bot.send_message(target_id, f"💰 **AJUSTE DE SALDO**\nHas recibido ${amount} USD de la administración.")
        else:
            await update.message.reply_text("❌ Usuario no encontrado.")
    except:
        await update.message.reply_text("❌ Uso: /addbalance <id> <monto>")

# ==========================================
# 9. MANEJADORES DE TEXTO Y ROUTER
# ==========================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el Captcha y mensajes generales."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Verificación de Captcha
    if 'captcha_correct' in context.user_data:
        correct = context.user_data['captcha_correct']
        if text == correct:
            del context.user_data['captcha_correct']
            await update.message.reply_text("✅ **IDENTIDAD CONFIRMADA**\nAccediendo al sistema central...")
            await asyncio.sleep(1)
            await show_dashboard(update, context)
        else:
            await update.message.reply_text("❌ **ERROR DE VERIFICACIÓN**\nCódigo incorrecto. Inténtalo de nuevo.")
        return
    
    # Chatbot simple si no es comando
    await update.message.reply_text("Comando no reconocido. Usa /start para reiniciar el panel.")

async def router_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enrutador central de botones."""
    data = update.callback_query.data
    
    if data == "back_home": await show_dashboard(update, context)
    elif data == "open_tiers": await open_tiers_menu(update, context)
    elif data == "tier_1": await tier_1_view(update, context)
    elif data == "tier_2": await tier_2_view(update, context)
    elif data == "tier_3": await tier_3_view(update, context)
    elif data == "mine_tap": await mine_click_action(update, context)
    elif data == "claim_afk": await claim_afk_action(update, context)
    elif data == "daily_bonus": await daily_bonus_action(update, context)
    elif data == "shop_view": await shop_view(update, context)
    elif data == "team_view": await team_view(update, context)
    elif data == "withdraw_menu": await update.callback_query.answer("Mínimo: $10.00 USD", show_alert=True)
    elif data == "buy_energy": await update.callback_query.answer("Fondos insuficientes", show_alert=True)
    elif data == "buy_shield": await update.callback_query.answer("Fondos insuficientes", show_alert=True)

# ==========================================
# 10. EJECUCIÓN PRINCIPAL
# ==========================================

async def main_bot_logic():
    """Función de arranque del bot."""
    if not BOT_TOKEN:
        logger.error("❌ FALTA EL BOT_TOKEN EN VARIABLES DE ENTORNO")
        return

    await init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers Comandos
    application.add_handler(CommandHandler("start", start))
    
    # Handlers Admin
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(CommandHandler("addbalance", admin_add_balance))
    
    # Handlers Lógica
    application.add_handler(CallbackQueryHandler(router_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    # Iniciar
    await application.initialize()
    await application.start()
    logger.info("🚀 HIVE MASTER SYSTEM ONLINE - POLLING STARTED")
    await application.updater.start_polling()

@app.on_event("startup")
async def startup_event():
    """Gancho de inicio para Render."""
    asyncio.create_task(main_bot_logic())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
