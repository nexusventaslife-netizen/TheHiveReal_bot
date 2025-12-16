import logging
import asyncio
import random
import string
import datetime
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes
import database as db

# Configuración de Logs
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE SISTEMA (SUPREMACÍA AUS V48.5 - PAYPAL PRO) ---
ADMIN_ID = 123456789  # <--- CAMBIA ESTO POR TU ID REAL DE TELEGRAM
INITIAL_USD = 0.05
INITIAL_HIVE = 500
HIVE_EXCHANGE_RATE = 0.0001 

# COSTOS Y LÍMITES
COST_PREMIUM_MONTH = 10 
COST_OBRERO = 50000
COST_MAPA = 100000
COST_ENERGY_REFILL = 500 
MAX_ENERGY = 100

# DIRECCIONES DE PAGO
# Enlace Profesional (NCP) - Botón Nativo
LINK_PAGO_GLOBAL = "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC"
CRYPTO_WALLET_USDT = "TU_DIRECCION_USDT_TRC20_AQUI" 

# ASSETS
IMG_BEEBY = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- ARSENAL MAESTRO DE ENLACES ---
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

# --- TEXTOS MULTI-IDIOMA ---
TEXTS = {
    'es': {
        'welcome_caption': (
            "🧬 **SISTEMA HIVE DETECTADO (V48.5)**\n"
            "───────────────────────\n"
            "Saludos, Operador `{name}`. Soy **Beeby**.\n\n"
            "Para iniciar tu carrera en la Colmena y generar ingresos, verifica tu humanidad.\n\n"
            "👇 **PASO 1:**\n"
            "Obtén tu CÓDIGO DE SEGURIDAD abajo y envíalo al chat."
        ),
        'ask_terms': (
            "✅ **CÓDIGO CORRECTO**\n"
            "───────────────────────\n"
            "⚠️ **PASO LEGAL (REQUIRED):**\n"
            "¿Aceptas las reglas del juego para continuar?"
        ),
        'ask_email': (
            "🤝 **CONTRATO ACEPTADO**\n"
            "───────────────────────\n"
            "📧 **PASO 3 (FINAL):**\n"
            "Escribe tu **CORREO ELECTRÓNICO** para activar tu Billetera Dual:"
        ),
        'ask_bonus': (
            "✅ **CUENTA VINCULADA**\n"
            "───────────────────────\n"
            "🎁 **PRIMERA MISIÓN DISPONIBLE**\n"
            "Valida tu identidad en Timebucks para activar el flujo de **$0.01 USD**."
        ),
        'btn_claim_bonus': "💰 VALIDAR Y GANAR $0.05",
        'dashboard_body': """
🎮 **CENTRO DE COMANDO HIVE**
──────────────────────────
👤 **Operador:** {name}
🛡️ **Clase:** {status}
📢 **Evento:** *Bybit Trading Wars*

💵 **SALDO REAL (Retirable):**
**${usd:.2f} USD** _(Mínimo Retiro: $10)_

🐝 **TOKENS HIVE:**
**{hive} HIVE**
_(Moneda de Juego)_

🔧 **ESTADO:**
{skills}
──────────────────────────
""",
        'premium_pitch': """
👑 **EVOLUCIÓN DE PERSONAJE: LICENCIA DE REINA**
──────────────────────────
¡Domina la economía de la Colmena!

⚡ **Turbo Minería (x2):** Doble recompensa.
🔓 **Llave Maestra:** Retiros rápidos ($5).
💎 **Merc
