import logging
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# URL DE TU WEB DE VERIFICACIÓN
LANDING_PAGE_URL = "https://index-html-3uz5.onrender.com"

# --- 🌍 CONFIGURACIÓN DE OFERTAS (CPA / AFILIADOS) ---
OFFERS = {
    'US': {'link': 'https://freecash.com/r/TU_LINK_USA', 'name': '🇺🇸 Misión VIP USA (Boost x10)'},
    'ES': {'link': 'https://www.bybit.com/invite?ref=LINK_ESPANA', 'name': '🇪🇸 Verificar ID España (Boost x5)'},
    'MX': {'link': 'https://bitso.com/?ref=LINK_MEXICO', 'name': '🇲🇽 Activar Cuenta México (Boost x5)'},
    'AR': {'link': 'https://lemon.me/LINK_ARGENTINA', 'name': '🇦🇷 Validar Wallet Arg (Boost x5)'},
    'CO': {'link': 'https://binance.com/LINK_COLOMBIA', 'name': '🇨🇴 Misión Colombia (Boost x5)'},
    'DEFAULT': {'link': 'https://otieu.com/4/10302294', 'name': '🌍 Verificación Global (Boost x2)'} 
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if hasattr(db, 'add_user'):
        await db.add_user(user.id, user.first_name, user.username)

    welcome_text = (
        f"🐝 *HIVE MIND v1.0*\n\n"
        f"Hola, {user.first_name}. Estás a un paso de la Colmena.\n\n"
        "💎 **PROYECTO:** Minería Social & Recompensas USD.\n"
        "🛡️ **ESTADO:** Verificación Requerida.\n\n"
        "1️⃣ Entra al enlace seguro.\n"
        "2️⃣ Obtén tu **Hash de Acceso** (Código).\n"
        "3️⃣ Pégalo aquí para iniciar el minero."
    )
    keyboard = [[InlineKeyboardButton("🛡️ INICIAR PROTOCOLO", url=LANDING_PAGE_URL)]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    user = update.effective_user
    
    # --- MENÚ DE TAREAS Y MINERÍA ---
    if "TAREAS" in text or "MINAR" in text or "PANEL" in text:
        await tasks_menu(update, context)
        return

    # 1. CASO EMAIL
    if context.user_data.get('waiting_for_email'):
        if re.match(r"[^@]+@[^@]+\.[^@]+", text):
            context.user_data['email'] = text
            context.user_data['waiting_for_email'] = False
            
            if hasattr(db, 'update_email'):
                await db.update_email(user.id, text)

            msg_wait = await update.message.reply_text("⚙️ *Sincronizando Nodo Minero...*", parse_mode="Markdown")
            await asyncio.sleep(1.5)
            try: await context.bot.delete_message(chat_id=user.id, message_id=msg_wait.message_id)
            except: pass
            
            # --- FINAL DEL REGISTRO (DOBLE ECONOMÍA) ---
            keyboard = [[InlineKeyboardButton("⛏️ IR AL PANEL DE CONTROL", callback_data="go_tasks")]]
            await update.message.reply_text(
                "✅ *NODO ACTIVO*\n\n"
                "💎 **Token:** HIVE (Minería Lenta)\n"
                "💵 **Billetera:** USD (Habilitada)\n\n"
                "⚠️ *Tu velocidad actual es muy baja (Larva).* Ve al panel para mejorarla.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return
        else:
            await update.message.reply_text("❌ Email inválido.")
            return

    # 2. CASO CÓDIGO HIVE-777-XX
    if text.startswith("HIVE-777"):
        parts = text.split('-')
        country_code = 'DEFAULT'
        if len(parts) >= 3:
            country_code = parts[2]
        
        context.user_data['country'] = country_code
        
        wait_msg = await update.message.reply_text(f"🌍 *Nodo Localizado: {country_code}* \nEstableciendo conexión segura...", parse_mode="Markdown")
        await asyncio.sleep(1.5)
        try: await context.bot.delete_message(chat_id=user.id, message_id=wait_msg.message_id)
        except: pass
            
        context.user_data['waiting_for_email'] = True
        await update.message.reply_text(
            f"✅ *CONEXIÓN ESTABLECIDA*\n\n"
            "📧 Escribe tu **Email** para crear tu ID Único de Minero:",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("❌ Código incorrecto.")

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    EL CORAZÓN DE LA MONETIZACIÓN:
    Muestra HIVE (Cripto) + USD (Dinero) + Misiones (Tus ganancias)
    """
    user_country = context.user_data.get('country', 'DEFAULT')
    offer = OFFERS.get(user_country, OFFERS['DEFAULT'])
    
    # Simulación de saldos (En el futuro esto vendrá de DB)
    hive_balance = "0.0045"
    usd_balance = "0.00"
    nft_status = "❌ Inactivo"

    text = (
        f"📟 **PANEL DE COMANDO HIVE ({user_country})**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⛏️ **HIVE MINADOS:** `{hive_balance}` HIVE\n"
        f"💵 **SALDO RETIRABLE:** `${usd_balance} USD`\n"
        f"🎒 **NFT BOOST:** {nft_status}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ **ACELERADOR DE MINADO**\n"
        "Para retirar tus USD, necesitas minar más rápido. Adquiere un **NFT Invisible (Boost)** completando esta misión:\n\n"
        f"🔥 **MISIÓN RECOMENDADA:**\n"
        f"👉 [{offer['name']}]({offer['link']})\n"
        "_(Recompensa: NFT Boost x5 + $2.00 USD Bono)_\n\n"
        "⚠️ *Advertencia:* El uso de VPN anulará la entrega del NFT."
    )
    
    # Botones Estratégicos
    keyboard = [
        [InlineKeyboardButton(f"🚀 ACTIVAR BOOST & GANAR $", url=offer['link'])],
        [InlineKeyboardButton("🔄 Actualizar Saldo", callback_data="go_tasks")],
        [InlineKeyboardButton("👥 Invitar (Gana 10% HIVE)", callback_data="invite_friends")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "go_tasks":
        await tasks_menu(update, context)
        
    elif query.data == "invite_friends":
        link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"
        await query.message.reply_text(
            f"🧬 **EXPANDE LA COLMENA**\n\n"
            "Invita usuarios y gana el **10%** de los HIVE que ellos minen + Bonos en USD.\n\n"
            f"🔗 Tu enlace genético:\n`{link}`",
            parse_mode="Markdown"
        )

# Comandos base
async def help_command(update, context): await update.message.reply_text("Ayuda: /start")
async def invite_command(update, context): await update.message.reply_text("Invitar: ...")
async def reset_command(update, context): 
    context.user_data.clear()
    await update.message.reply_text("Reset completo.")
