import logging
import re
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
HIVE_PRICE = 0.012
INITIAL_BONUS = 100
ADMIN_ID = 123456789  # Reemplaza con tu ID de administrador

# --- LINKS MAESTROS ---
RENDER_URL = "https://thehivereal-bot.onrender.com"
LINK_ENTRY_DETECT = f"{RENDER_URL}/ingreso"

# --- ☢️ ARSENAL DE MONETIZACIÓN ---
LINKS = {
    # 🎰 CASINOS & JACKPOTS
    'BCGAME': "https://bc.game/i-477hgd5fl-n/",
    'BETFURY': "https://t.me/misterFury_bot/app?startapp=tgReLUser7012661",
    'FREEBITCOIN': "https://freebitco.in/?r=55837744",
    'COINTIPLY': "https://cointiply.com/r/jR1L6y",

    # 📈 FINTECH & TRADING
    'BYBIT': "https://www.bybit.com/invite?ref=BBJWAX4",
    'PLUS500': "https://www.plus500.com/en-uy/refer-friend",
    'REVOLUT': "Https://revolut.com/referral/?referral-code=alejandroperdbhx",
    'NEXO': "Https://nexo.com/ref/rbkekqnarx?src=android-link",
    'YOUHODLER': "https://app.youhodler.com/sign-up?ref=SXSSSNB1",
    'WISE': "Https://wise.com/invite/ahpc/josealejandrop73",
    'AIRTM': "Https://app.airtm.com/ivt/jos3vkujiyj",

    # ☁️ MINERÍA PASIVA
    'PACKETSTREAM': "https://packetstream.io/?psr=7hMP",
    'HONEYGAIN': "Https://join.honeygain.com/ALEJOE9F32",
    'PAWNS': "https://pawns.app/?r=18399810",
    'TRAFFMONETIZER': "https://traffmonetizer.com/?aff=2034896",

    # 📱 TRABAJO & JUEGOS
    'PAIDWORK': "https://www.paidwork.com/?r=nexus.ventas.life",
    'GAMEHAG': "https://gamehag.com/r/NWUD9QNR",
    'COINPAYU': "https://www.coinpayu.com/?r=TU_CODIGO",  # Completar con tu link
    'SPROUTGIGS': "https://sproutgigs.com/?a=83fb1bf9",

    # 🔄 OFERTAS CPA
    'FREECASH': "https://freecash.com/r/XYN98"
}

# --- TEXTOS MULTILENGUAJE ---
TEXTS = {
    'es': {
        'welcome': "🐝 **THE ONE HIVE** `v7.2`\n👤 Usuario: `{name}`\n\n💎 Bienvenido. Genera riqueza mediante minería, casinos y referidos.\n\n👇 **Empieza ahora:**",
        'btn_start': "🛡️ EMPEZAR",
        'dashboard_title': "🖥️ **TABLERO PRINCIPAL**",
        'metrics': "📊 **Estadísticas**",
        'wallet': "💰 **Tu Billetera**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'balance_usd': "💵 **Equivalente: ${usd:.2f} USD**",
        'menu_jackpot': "🎰 CASINO & JACKPOT",
        'menu_fintech': "📈 FINTECH",
        'menu_work': "📱 TRABAJO",
        'menu_passive': "☁️ MINERÍA",
        'menu_team': "👥 REFERIDOS",
        'menu_withdraw': "🏧 RETIRADAS",
        'menu_profile': "⚙️ PERFIL",
        'help': "ℹ️ Este bot te permite ganar tokens con minería, referidos, y juegos. Usa las opciones del menú para explorar."
    },
    'en': {
        'welcome': "🐝 **THE ONE HIVE** `v7.2`\n👤 User: `{name}`\n\n💎 Welcome. Generate wealth via mining, casinos, and referrals.\n\n👇 **Start Now:**",
        'btn_start': "🛡️ START",
        'dashboard_title': "🖥️ **DASHBOARD**",
        'metrics': "📊 **Statistics**",
        'wallet': "💰 **Your Wallet**",
        'balance_hive': "🪙 **{tokens} HIVE**",
        'balance_usd': "💵 **Equivalent: ${usd:.2f} USD**",
        'menu_jackpot': "🎰 CASINOS & JACKPOT",
        'menu_fintech': "📈 FINTECH",
        'menu_work': "📱 WORK",
        'menu_passive': "☁️ MINING",
        'menu_team': "👥 REFERRALS",
        'menu_withdraw': "🏧 WITHDRAW",
        'menu_profile': "⚙️ PROFILE",
        'help': "ℹ️ This bot lets you earn tokens through mining, referrals, and games. Use the menu options to explore."
    }
}

# --- FUNCIONES MULTILENGUAJE ---
def get_text(lang_code, key):
    """Devuelve el texto traducido según el idioma."""
    lang = 'en'
    if lang_code and lang_code.startswith('es'):
        lang = 'es'
    return TEXTS[lang].get(key, TEXTS['en'][key])

# --- FUNCIONES CLAVE ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start: Muestra menú principal y registra al usuario."""
    user = update.effective_user
    lang = user.language_code

    # Procesar referidos
    args = context.args
    referrer_id = args[0] if args and args[0] != str(user.id) else None

    # Registrar usuario
    if hasattr(db, 'add_user'):
        await db.add_user(user.id, user.first_name, user.username, referrer_id)

    # Mostrar bienvenida
    txt = get_text(lang, 'welcome').format(name=user.first_name)
    kb = [[InlineKeyboardButton(get_text(lang, 'btn_start'), url=LINK_ENTRY_DETECT)]]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help para mostrar información básica."""
    lang = update.effective_user.language_code
    txt = get_text(lang, 'help')
    await update.message.reply_text(txt, parse_mode="Markdown")

# --- FUNCIONES DEL DASHBOARD ---
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dashboard personal del usuario."""
    user = update.effective_user
    lang = user.language_code
    user_data = await db.get_user(user.id)
    tokens = user_data.get('tokens', INITIAL_BONUS) if user_data else INITIAL_BONUS
    usd = tokens * HIVE_PRICE

    txt = (
        f"{get_text(lang, 'dashboard_title')}\n"
        f"🔹 Usuario: `{user.id}`\n"
        f"{get_text(lang, 'metrics')}\n"
        f"{get_text(lang, 'balance_hive').format(tokens=tokens)}\n"
        f"{get_text(lang, 'balance_usd').format(usd=usd)}\n"
    )

    kb = [
        [InlineKeyboardButton(get_text(lang, 'menu_jackpot'), callback_data="jackpot_zone"),
         InlineKeyboardButton(get_text(lang, 'menu_fintech'), callback_data="fintech_vault")],
        [InlineKeyboardButton(get_text(lang, 'menu_work'), callback_data="work_zone"),
         InlineKeyboardButton(get_text(lang, 'menu_passive'), callback_data="passive_income")]
    ]

    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# Otros submenús como jackpot_zone, work_zone, etc. no han sido modificados.
