import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user_fast, register_user_smart, update_gamification, burn_hive_for_withdrawal, unlock_api_gate

# --- TUS LINKS DE MONETIZACIÓN REALES ---
# 1. PEAJE DE ENTRADA (Link de Adsterra/CPAGrip Direct Link)
LINK_GATE_CPA = os.environ.get("LINK_GATE", "https://tucpalink.com/security-check")

# 2. OFFERWALL INTERNO (Donde ganas el Split 30/70)
# Usa OfferToro/AdGem. El {uid} es vital para el postback.
LINK_OFFERWALL = "https://www.offertoro.com/ifr/show/TU_PUB_ID/{uid}/TU_SECRET"

# 3. ALIANZAS EXTERNAS (Referidos Vitalicios)
PARTNERS = {
    "SWAGBUCKS": "https://www.swagbucks.com/p/register?rb=TU_REF",
    "FREECASH": "https://freecash.com/r/TU_REF",
    "BINANCE": "https://accounts.binance.com/register?ref=TU_REF"
}

# 4. TIENDA DE ITEMS (Economía Circular)
NFT_SHOP = {
    "GPU_V1": {"name": "Rig Casero", "cost_usd": 5.0, "power": 1.5},
    "ASIC_PRO": {"name": "Titan Miner", "cost_usd": 20.0, "power": 3.0}
}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tier = await register_user_smart(user) # Auto-detecta país
    data = await get_user_fast(user.id)
    
    # 1. MURO DE SEGURIDAD (MONETIZACIÓN DÍA 1)
    if not data.get('api_gate_passed'):
        await update.message.reply_text(
            "🛡️ **PROTOCOLO DE SEGURIDAD TITAN**\n\n"
            "⚠️ Detectamos una nueva conexión.\n"
            "Para evitar bots y activar tu billetera, debes instalar la **Llave de Acceso (API)**.\n\n"
            "👇 **PASO OBLIGATORIO:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📲 DESCARGAR API SEGURA", url=LINK_GATE_CPA)],
                [InlineKeyboardButton("🔄 VERIFICAR ACCESO", callback_data="check_gate")]
            ])
        )
        return

    # Si ya pasó el muro, mostramos Dashboard
    await show_dashboard(update)

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simulación de verificación del muro"""
    # En producción real, esto debería activarse por Postback, pero para UX lo hacemos manual con delay
    await update.callback_query.answer("📡 Verificando señal...", show_alert=True)
    await unlock_api_gate(update.effective_user.id)
    await update.callback_query.message.reply_text("✅ **ACCESO CONCEDIDO.** Bienvenido al Enjambre.")
    await show_dashboard(update)

async def show_dashboard(update_obj):
    if isinstance(update_obj, Update):
        user = update_obj.effective_user
        msg_func = update_obj.message.reply_text
    else: # Callback
        user = update_obj.from_user
        msg_func = update_obj.message.reply_text

    # Actualizamos Racha y Gamificación al entrar
    game_stats = await update_gamification(user.id)
    data = await get_user_fast(user.id)
    
    streak = game_stats['streak']
    rank = game_stats['rank']
    
    # Emojis de Rango
    rank_icon = "🐛" if rank == "LARVA" else "🦁" if rank == "TITAN" else "🐝"
    
    msg = (
        f"{rank_icon} **TITAN OS V9** | `{user.first_name}`\n"
        f"🌍 Zona: **{data.get('tier')}**\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💵 Saldo Retirable: **${data.get('balance_available', 0):.2f}**\n"
        f"⏳ En Revisión: **${data.get('balance_pending', 0):.2f}**\n"
        f"🍯 HIVE Token: **{data.get('balance_hive', 0):,.0f}**\n"
        f"🔥 Racha: **{streak} Días**\n"
        f"➖➖➖➖➖➖➖➖\n"
        "👇 **ELIGE TU CAMINO:**"
    )
    
    kb = [
        ["💸 TAREAS (Split 70%)", "🤝 PARTNERS (Gana Crypto)"],
        ["⛏️ MINAR HIVE", "🛍️ TIENDA NFTs"],
        ["🏦 BILLETERA", "🆘 AYUDA"]
    ]
    await msg_func(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    data = await get_user_fast(user.id)
    
    if "TAREAS" in text:
        # SMART ROUTING
        personal_link = LINK_OFFERWALL.replace("{uid}", str(user.id))
        kb = [[InlineKeyboardButton("🚀 INICIAR TAREAS (WebApp)", web_app=WebAppInfo(url=personal_link))]]
        await update.message.reply_text(
            "💼 **CENTRO DE TRABAJO SEGURO**\n"
            "Realiza tareas dentro de Telegram para asegurar tu pago.\n"
            "💰 *Pagos instantáneos (Tareas < $5)*", 
            reply_markup=InlineKeyboardMarkup(kb)
        )
        
    elif "PARTNERS" in text:
        # REFERIDOS VITALICIOS
        kb = [
            [InlineKeyboardButton("🟢 FREECASH (Pagos Altos)", url=PARTNERS['FREECASH'])],
            [InlineKeyboardButton("🔵 SWAGBUCKS (Bono $5)", url=PARTNERS['SWAGBUCKS'])],
            [InlineKeyboardButton("🟡 BINANCE (Exchange)", url=PARTNERS['BINANCE'])]
        ]
        await update.message.reply_text(
            "🤝 **ALIANZAS GLOBALES**\n"
            "Regístrate en estas plataformas certificadas.\n"
            "Gana dinero extra y retíralo directo a tu cuenta.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        
    elif "MINAR" in text:
        # TAP TO EARN
        kb = [[InlineKeyboardButton("⛏️ GOLPEAR BLOQUE", callback_data="mine_tap")]]
        await update.message.reply_text("⛏️ **ZONA DE MINERÍA**\nAcumula HIVE para poder retirar tus Dólares.", reply_markup=InlineKeyboardMarkup(kb))
        
    elif "TIENDA NFTs" in text:
        # ECONOMÍA CIRCULAR (Gastar USD para ganar Power)
        kb = []
        for key, item in NFT_SHOP.items():
            kb.append([InlineKeyboardButton(f"🛒 {item['name']} (${item['cost_usd']})", callback_data=f"buy_{key}")])
            
        await update.message.reply_text(
            "🛍️ **MERCADO NEGRO DE HARDWARE**\n"
            "Invierte tus ganancias (USD) para minar HIVE más rápido.\n"
            "Recuerda: Sin HIVE, no puedes retirar dólares.",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif "BILLETERA" in text:
        kb = [[InlineKeyboardButton("📤 RETIRAR FONDOS", callback_data="try_withdraw")]]
        await update.message.reply_text(
            f"🏦 **BILLETERA**\n💵 Disponible: ${data.get('balance_available', 0):.2f}",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# CALLBACKS RÁPIDOS
async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # En producción: conectar a database.mine_hive
    await update.callback_query.answer("💥 +1 HIVE", cache_time=0)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lógica de retiro con quema de HIVE
    user_id = update.effective_user.id
    # Simulamos intento de retiro de $5
    result = await burn_hive_for_withdrawal(user_id, 5.0)
    
    if result == "OK":
        await update.callback_query.message.edit_text("✅ **RETIRO PROCESADO.**\nEnviando LTC a tu wallet...")
    elif result == "NO_HIVE":
        await update.callback_query.answer("❌ FALTA HIVE. Necesitas 500 HIVE para retirar $5.", show_alert=True)
    elif result == "NO_USD":
        await update.callback_query.answer("❌ SALDO INSUFICIENTE.", show_alert=True)
