import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler
from email_validator import validate_email, EmailNotValidError

from database import (
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

# Conversation states
WAIT_EMAIL, WAIT_API_CHECK = range(2)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Register or ensure user exists
    await register_user_smart(user)
    data = await get_user_fast(user.id)
    
    # If email not present, ask for it first (new requirement)
    if not data.get('email'):
        await update.message.reply_text(
            "📧 Para activar tu cuenta debes ingresar tu correo electrónico oficial.\n\n"
            "Esto nos permite verificar identidad, recuperar cuenta y enviarte oportunidades.\n"
            "Al ingresar tu correo aceptas recibir ofertas (puedes desactivar en perfil)."
        )
        return WAIT_EMAIL

    # If email present but api_gate not passed, ask to download API
    if not data.get('api_gate_passed'):
        await update.message.reply_text(
            "🛡️ Ahora debes instalar la Llave de Seguridad para proteger la economía del nodo.\n\n"
            "👇 Pulsa el botón para descargar e instala la 'API de Seguridad'.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📲 DESCARGAR API SEGURA", url=LINK_GATE_CPA)],
                [InlineKeyboardButton("🔄 YA LA DESCARGUÉ (Verificar)", callback_data="check_gate")]
            ])
        )
        return WAIT_API_CHECK

    # Otherwise show dashboard
    await show_dashboard(update)

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Estado: WAIT_EMAIL
    Validamos y guardamos el email, luego pedimos descargar la API obligatoria.
    """
    text = update.message.text.strip()
    user = update.effective_user
    try:
        v = validate_email(text)  # throws if invalid
        email_norm = v.email
        # Save email in DB and leads table
        await save_user_email(user.id, email_norm, market_value=0.2)
        
        # Prompt to download API (muro)
        await update.message.reply_text(
            "✅ Email registrado.\n\n"
            "Siguiente paso obligatorio: Instala la Llave de Seguridad (API) para desbloquear tu cuenta.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📲 DESCARGAR API SEGURA", url=LINK_GATE_CPA)],
                [InlineKeyboardButton("🔄 YA LA DESCARGUÉ (Verificar)", callback_data="check_gate")]
            ])
        )
        return WAIT_API_CHECK
    except EmailNotValidError:
        await update.message.reply_text("❌ Email inválido. Ingresa un correo real (Gmail/Outlook).")
        return WAIT_EMAIL

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para 'YA LA DESCARGUÉ' -> desbloquea (siempre que email exista)."""
    query = update.callback_query
    user_id = query.from_user.id
    # In production, validate Postback from the CPA network. Here we simulate small delay.
    await query.answer("🔄 Verificando instalación...")
    await asyncio.sleep(2.0)
    # Ensure email exists before unlocking
    data = await get_user_fast(user_id)
    if not data.get('email'):
        await query.message.reply_text("❌ Necesitamos tu correo antes de verificar. Usa /start y agrega tu email.")
        return

    await unlock_api_gate(user_id)
    await query.message.reply_text("✅ Acceso concedido. Bienvenido al Enjambre.")
    await show_dashboard(query)

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
        f"{rank_icon} **TITAN OS** | `{user.first_name}`\n"
        f"🌍 Zona: **{data.get('tier')}**\n"
        f"💵 Disponible: **${data.get('balance_available', 0):.2f}**\n"
        f"⏳ En revisión: **${data.get('balance_pending', 0):.2f}**\n"
        f"🍯 HIVE: **{data.get('balance_hive', 0):.0f}**\n"
        f"🔥 Racha: **{streak} días**\n\n"
        "👇 Elige cómo quieres ganar hoy:"
    )
    kb = [
        ["💸 TAREAS (Split)", "🤝 PARTNERS"],
        ["⛏️ MINAR HIVE", "🛍️ TIENDA NFTs"],
        ["🏦 BILLETERA", "🆘 AYUDA"]
    ]
    await send(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user = update.effective_user
    data = await get_user_fast(user.id)
    
    if "TAREAS" in text:
        personal_link = LINK_OFFERWALL.replace("{uid}", str(user.id))
        kb = [[InlineKeyboardButton("🚀 INICIAR TAREAS (WebApp)", web_app=WebAppInfo(url=personal_link))]]
        await update.message.reply_text("💼 Centro de trabajo seguro", reply_markup=InlineKeyboardMarkup(kb))
    elif "PARTNERS" in text:
        kb = [[InlineKeyboardButton("🔵 SWAGBUCKS", url=PARTNERS['SWAGBUCKS'])],
              [InlineKeyboardButton("🟢 FREECASH", url=PARTNERS['FREECASH'])]]
        await update.message.reply_text("🤝 Alianzas", reply_markup=InlineKeyboardMarkup(kb))
    elif "MINAR" in text:
        kb = [[InlineKeyboardButton("⛏️ GOLPEAR BLOQUE", callback_data="mine_tap")]]
        await update.message.reply_text("⛏️ Minería", reply_markup=InlineKeyboardMarkup(kb))
    elif "TIENDA" in text:
        kb = []
        for key, v in NFT_SHOP.items():
            kb.append([InlineKeyboardButton(f"{v['name']} - ${v['cost_usd']}", callback_data=f"buy_{key}")])
        await update.message.reply_text("🛍️ Tienda NFTs", reply_markup=InlineKeyboardMarkup(kb))
    elif "BILLETERA" in text:
        await show_dashboard(update)
    else:
        await show_dashboard(update)

async def mine_tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("💥 +1 HIVE", cache_time=0)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    res = await burn_hive_for_withdrawal(user_id, 5.0)
    if res == "OK":
        await update.callback_query.message.edit_text("✅ Retiro procesado.")
    elif res == "NO_HIVE":
        await update.callback_query.answer("❌ No tienes HIVE suficiente (500 HIVE para $5).", show_alert=True)
    elif res == "NO_USD":
        await update.callback_query.answer("❌ Saldo insuficiente.", show_alert=True)
from database import db_pool # Asegúrate de importar esto arriba

async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando secreto para borrar mi cuenta y probar desde cero"""
    user_id = update.effective_user.id
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE telegram_id=$1", user_id)
    
    await update.message.reply_text("🔄 **CUENTA BORRADA.**\nEscribe /start para probar el registro de nuevo.")
