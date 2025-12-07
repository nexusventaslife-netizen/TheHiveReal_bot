import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from email_validator import validate_email
from database import get_user, upsert_user, modify_balance, check_duplicate_image, get_p2p_orders, REGION_DATA

# Configuración traída del entorno
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
ADMIN_WALLET = os.environ.get("ADMIN_WALLET_TRC20", "WALLET_PENDIENTE")
OFFERTORO_PUB_ID = os.environ.get("OFFERTORO_PUB_ID", "0")
OFFERTORO_SECRET = os.environ.get("OFFERTORO_SECRET", "0")

# Estados de Conversación
(WAIT_EMAIL, WAIT_PROOF) = range(2)

# Links de Monetización (Nexus Market)
LINKS = {
    "TRADING": "https://hotmart.com/es/marketplace/productos/curso-trading",
    "FREELANCE": "https://fiverr.com",
    "BINANCE": "https://accounts.binance.com/register"
}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bienvenida y Geo-Escaneo."""
    user = update.effective_user
    args = context.args
    referrer = int(args[0]) if args and args[0].isdigit() else None
    
    await upsert_user(user, referrer)
    data = await get_user(user.id)
    
    # Si no tiene email, hacemos el show del escaneo
    if not data.get("email"):
        tier = data.get('region_tier', 'TIER_3')
        tier_info = REGION_DATA.get(tier, {})
        cap = tier_info.get('cap', 100)
        flag = tier_info.get('flag', '🏳️')
        
        await update.message.reply_text("🛰️ **INICIANDO ESCANEO SATELITAL...**")
        # Simula carga rápida (psicología)
        # await asyncio.sleep(1) 
        
        await update.message.reply_text(
            f"✅ **UBICACIÓN CONFIRMADA:** {data.get('country_code')} {flag}\n"
            f"📊 **POTENCIAL DE MERCADO:** ${cap}/día\n\n"
            "🧬 **ACTIVACIÓN REQUERIDA:**\n"
            "Para crear tu Billetera HIVE, ingresa tu **Email Oficial** abajo:"
        )
        return WAIT_EMAIL
    
    await show_dashboard(update)
    return ConversationHandler.END

async def save_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    try:
        validate_email(email)
        # Aquí se guardaría en DB (database.py tiene la función upsert, se podría añadir update email)
        # Para el MVP asumimos éxito visual
        await update.message.reply_text("✅ **IDENTIDAD VERIFICADA.** Accediendo al sistema...")
        await show_dashboard(update)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Email inválido. Intenta de nuevo.")
        return WAIT_EMAIL

async def show_dashboard(update: Update):
    """El Panel de Control Principal."""
    user = update.effective_user
    data = await get_user(user.id)
    
    bal_usd = data.get('balance_usd', 0.0)
    bal_hive = data.get('balance_hive', 0.0)
    
    # Proyecciones Psicológicas
    proj_week = bal_usd + (15 * 7)
    
    msg = (
        f"💠 **HIVE TITAN OS** | ID: `{user.id}`\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💵 Liquidez USD: **${bal_usd:.2f}**\n"
        f"🍯 Reservas HIVE: **{bal_hive:.2f}**\n"
        f"🧬 Rango: **{data.get('rank', 'LARVA')}**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📈 **Proyección (7d):** ${proj_week:.2f}\n\n"
        "👇 **SELECCIONA MÓDULO:**"
    )
    kb = [
        ["🎓 ACADEMIA / MARKET", "📱 VIRAL STUDIO"],
        ["🍯 RECOLECTAR (CPA)", "⛏️ MINAR / ADS"],
        ["🧬 EVOLUCIONAR (VIP)", "💹 P2P DEX"],
        ["🏦 RETIRAR", "👤 PERFIL"]
    ]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador inteligente de botones."""
    text = update.message.text.upper()
    
    if "ACADEMIA" in text:
        kb = [
            [InlineKeyboardButton("📈 CURSO TRADING", url=LINKS["TRADING"])],
            [InlineKeyboardButton("💰 CUENTA BINANCE", url=LINKS["BINANCE"])],
            [InlineKeyboardButton("📤 RECLAMAR CASHBACK", callback_data="req_proof")]
        ]
        await update.message.reply_text("🎓 **NEXUS MARKET**\nInvierte en herramientas y recibe HIVE.", reply_markup=InlineKeyboardMarkup(kb))
        
    elif "MINAR" in text or "ADS" in text:
        kb = [
            [InlineKeyboardButton("⛏️ MINAR (+1 HIVE)", callback_data="mine_manual")],
            [InlineKeyboardButton("📺 VER AD (+10 HIVE)", callback_data="watch_ad")]
        ]
        await update.message.reply_text("⛏️ **CENTRO DE MINERÍA**", reply_markup=InlineKeyboardMarkup(kb))
        
    elif "VIP" in text or "EVOLUCIONAR" in text:
        kb = [[InlineKeyboardButton("🅰️ PAGAR VIP ($14.99)", callback_data="req_proof")]]
        await update.message.reply_text(
            f"🧬 **EVOLUCIÓN VIP**\nBeneficios x5.\nWallet TRC20: `{ADMIN_WALLET}`", 
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
        
    elif "CPA" in text or "RECOLECTAR" in text:
        uid = update.effective_user.id
        link = f"https://www.offertoro.com/ifr/show/{OFFERTORO_PUB_ID}/{uid}/{OFFERTORO_SECRET}"
        kb = [[InlineKeyboardButton("🚀 IR A OFERTAS", url=link)]]
        await update.message.reply_text("🍯 **ZONA CPA**\nGana USD instalando apps.", reply_markup=InlineKeyboardMarkup(kb))
        
    elif "P2P" in text:
        orders = await get_p2p_orders()
        msg = "💹 **MERCADO P2P**\n"
        if orders:
            for o in orders: msg += f"\n📦 {o['amount_hive']} HIVE -> ${o['price_usd']}"
        else:
            msg += "\nNo hay órdenes activas. Sé el primero."
        await update.message.reply_text(msg)
        
    else:
        await show_dashboard(update)

async def mine_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await modify_balance(update.effective_user.id, hive=1.0)
    await update.callback_query.message.reply_text("✅ +1 HIVE Minado")

async def request_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📸 **SUBE TU COMPROBANTE (FOTO AHORA):**")
    return WAIT_PROOF

async def process_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo: return
    user = update.effective_user
    photo = await update.message.photo[-1].get_file()
    img_bytes = await photo.download_as_bytearray()
    
    # Check Seguridad
    if await check_duplicate_image(img_bytes, user.id):
        await update.message.reply_text("🚨 **ALERTA:** Imagen duplicada detectada.")
        return ConversationHandler.END
        
    if ADMIN_ID != 0:
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=f"Proof User: {user.id}")
        
    await update.message.reply_text("✅ **ENVIADO A REVISIÓN.**")
    return ConversationHandler.END
