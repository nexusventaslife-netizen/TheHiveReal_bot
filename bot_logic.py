import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler
from email_validator import validate_email, EmailNotValidError

from database import (
    db_pool, # Importamos pool para el reset
    get_user_fast, register_user_smart, update_gamification,
    burn_hive_for_withdrawal, unlock_api_gate, save_user_email
)

# LINKS / CONFIG
LINK_GATE_CPA = os.environ.get("LINK_GATE", "https://tucpalink.com/security-check")
LINK_OFFERWALL = "https://www.offertoro.com/ifr/show/TU_PUB_ID/{uid}/TU_SECRET"
PARTNERS = {
    "SWAGBUCKS": "https://www.swagbucks.com/p/register?rb=TU_REF",
    "FREECASH": "https://freecash.com/r/TU_REF",
    "BINANCE": "https://accounts.binance.com/register?ref=TU_REF"
}
NFT_SHOP = {
    "GPU_V1": {"name": "Rig Casero", "cost_usd": 5.0, "power": 1.5},
    "ASIC_PRO": {"name": "Titan Miner", "cost_usd": 20.0, "power": 3.0}
}

# Estados de Conversación
WAIT_EMAIL, WAIT_API_CHECK = range(2)

# --- COMANDO PARA TESTEO (BORRARME DE LA DB) ---
async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra tu usuario para probar el inicio de cero."""
    user_id = update.effective_user.id
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE telegram_id=$1", user_id)
        await conn.execute("DELETE FROM leads_harvest WHERE telegram_id=$1", user_id)
        # Limpiar caché de Redis si existe (opcional, se maneja solo usualmente)
    
    await update.message.reply_text("🔄 **USUARIO RESETEADO.**\nAhora escribe /start para probar el flujo de Email + API desde cero.")
    return ConversationHandler.END

# --- FLUJO PRINCIPAL ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await register_user_smart(user)
    data = await get_user_fast(user.id)
    
    # 1. PEDIR EMAIL SI NO LO TIENE
    if not data.get('email'):
        await update.message.reply_text(
            "📧 **TITAN SECURITY PROTOCOL**\n\n"
            "Para activar el Nodo, ingresa tu correo electrónico oficial:\n"
            "_(Nos sirve para enviarte alertas de pago y recuperar cuenta)_"
        )
        return WAIT_EMAIL

    # 2. PEDIR API (MURO) SI NO LA TIENE
    if not data.get('api_gate_passed'):
        await update.message.reply_text(
            "🛡️ **VERIFICACIÓN REQUERIDA**\n\n"
            "Falta un paso: Instala la Llave de Seguridad (API) para proteger la economía del nodo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📲 DESCARGAR API SEGURA", url=LINK_GATE_CPA)],
                [InlineKeyboardButton("🔄 YA LA DESCARGUÉ", callback_data="check_gate")]
            ])
        )
        return WAIT_API_CHECK

    # 3. SI TIENE TODO, MOSTRAR DASHBOARD
    await show_dashboard(update)

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    try:
        v = validate_email(text)
        email_norm = v.email
        # Guardamos el mail
        await save_user_email(user.id, email_norm, market_value=0.2)
        
        # Inmediatamente pedimos el Muro (Paso 2)
        await update.message.reply_text(
            "✅ **Email Registrado.**\n\n"
            "🛡️ **Último paso:** Descarga la App Llave para desbloquear el bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📲 DESCARGAR API SEGURA", url=LINK_GATE_CPA)],
                [InlineKeyboardButton("🔄 VERIFICAR INSTALACIÓN", callback_data="check_gate")]
            ])
        )
        return WAIT_API_CHECK
    except EmailNotValidError:
        await update.message.reply_text("❌ Email inválido. Por favor usa un correo real (Gmail, Hotmail, etc).")
        return WAIT_EMAIL

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("📡 Buscando señal de la API...")
    await asyncio.sleep(1.5) # Simular carga
    
    # Validar que tenga email antes de dejar pasar
    data = await get_user_fast(user_id)
    if not data.get('email'):
        await query.message.reply_text("⚠️ Error: Falta registrar el email. Escribe /start de nuevo.")
        return ConversationHandler.END

    await unlock_api_gate(user_id)
    await query.message.reply_text("✅ **ACCESO CONCEDIDO.** Bienvenido al Titan Node.")
    await show_dashboard(query)
    return ConversationHandler.END

async def show_dashboard(update_obj):
    if isinstance(update_obj, Update):
        user = update_obj.effective_user
        send = update_obj.message.reply_text
    else:
        user = update_obj.from_user
        send = update_obj.message.reply_text

    await update_gamification(user.id)
    data = await get_user_fast(user.id)
    
    streak = data.get('streak_days', 0)
    rank = data.get('rank', 'LARVA')
    rank_icon = "🐛" if rank == "LARVA" else "🐝" if rank == "ABEJA" else "🦁"
    
    msg = (
        f"{rank_icon} **TITAN OS V9** | `{user.first_name}`\n"
        f"🌍 Zona: **{data.get('tier')}**\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💵 Retirable: **${data.get('balance_available', 0):.2f}**\n"
        f"⏳ Pendiente: **${data.get('balance_pending', 0):.2f}**\n"
        f"🍯 HIVE: **{data.get('balance_hive', 0):.0f}**\n"
        f"🔥 Racha: **{streak} días**\n"
        f"➖➖➖➖➖➖➖➖\n"
        "👇 **PANEL DE CONTROL:**"
    )
    kb = [
        ["💸 TAREAS (Gana USD)", "🤝 PARTNERS VIP"],
        ["⛏️ MINAR HIVE", "🛍️ TIENDA NFTs"],
        ["🏦 BILLETERA", "🆘 SOPORTE"]
    ]
    await send(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user = update.effective_user
    
    if "TAREAS" in text:
        personal_link = LINK_OFFERWALL.replace("{uid}", str(user.id))
        kb = [[InlineKeyboardButton("🚀 INICIAR TAREAS (WebApp)", web_app=WebAppInfo(url=personal_link))]]
        await update.message.reply_text("💼 **CENTRO DE TRABAJO**\nCompleta ofertas para ganar Saldo Real.", reply_markup=InlineKeyboardMarkup(kb))
    elif "PARTNERS" in text:
        kb = [[InlineKeyboardButton("🔵 SWAGBUCKS (Bono $5)", url=PARTNERS['SWAGBUCKS'])],
              [InlineKeyboardButton("🟢 FREECASH (Crypto)", url=PARTNERS['FREECASH'])]]
        await update.message.reply_text("🤝 **ALIANZAS**\nRegístrate aquí para ingresos pasivos vitalicios.", reply_markup=InlineKeyboardMarkup(kb))
    elif "MINAR" in text:
        kb = [[InlineKeyboardButton("⛏️ PICAR BLOQUE", callback_data="mine_tap")]]
        await update.message.reply_text("⛏️ **MINERÍA ACTIVA**\nConsigue HIVE para desbloquear retiros.", reply_markup=InlineKeyboardMarkup(kb))
    elif "TIENDA" in text:
        kb = []
        for key, v in NFT_SHOP.items():
            kb.append([InlineKeyboardButton(f"{v['name']} - ${v['cost_usd']}", callback_data=f"buy_{key}")])
        await update.message.reply_text("🛍️ **BLACK MARKET**\nCompra potencia con tu saldo.", reply_markup=InlineKeyboardMarkup(kb))
    elif "BILLETERA" in text:
        kb = [[InlineKeyboardButton("📤 RETIRAR FONDOS", callback_data="try_withdraw")]]
        await update.message.reply_text("🏦 **BÓVEDA SEGURA**", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await show_dashboard(update)

# Callbacks simples
async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("💥 +1 HIVE", cache_time=0)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    res = await burn_hive_for_withdrawal(user_id, 5.0) # Simula retiro de $5
    if res == "OK": await update.callback_query.message.edit_text("✅ Solicitud de retiro enviada.")
    elif res == "NO_HIVE": await update.callback_query.answer("❌ Falta HIVE. Necesitas 500 HIVE para retirar $5.", show_alert=True)
    elif res == "NO_USD": await update.callback_query.answer("❌ Saldo insuficiente.", show_alert=True)
