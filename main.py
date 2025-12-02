import os
import logging
import asyncio
import json
import hashlib
import hmac
import base64
from http import HTTPStatus
from datetime import datetime, timedelta
from urllib.parse import urlparse
from decimal import Decimal

from quart import Quart, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

import psycopg2
from psycopg2.pool import SimpleConnectionPool
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed
import pytz

# === LOGGING ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === CONFIGURACIÓN GLOBAL ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
DATABASE_URL = os.environ.get('DATABASE_URL', "")
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
PORT = int(os.environ.get('PORT', 10000))

# APIs de Plataformas de Tareas
CPALEAD_ID = os.environ.get('CPALEAD_ID', '')
OFFERTORO_ID = os.environ.get('OFFERTORO_ID', '')
ADGATE_ID = os.environ.get('ADGATE_ID', '')
POLLFISH_KEY = os.environ.get('POLLFISH_KEY', '')
BITLABS_TOKEN = os.environ.get('BITLABS_TOKEN', '')
FYBER_APP_ID = os.environ.get('FYBER_APP_ID', '')
TAPJOY_API_KEY = os.environ.get('TAPJOY_API_KEY', '')
IRONSOUCE_SECRET = os.environ.get('IRONSOUCE_SECRET', '')
VUNGLE_APP_ID = os.environ.get('VUNGLE_APP_ID', '')
ADMOB_CLIENT_ID = os.environ.get('ADMOB_CLIENT_ID', '')

# Blockchain
WEB3_RPC_BSC = os.environ.get('WEB3_RPC_BSC', 'https://bsc-dataseed.binance.org')
WEB3_RPC_POLYGON = os.environ.get('WEB3_RPC_POLYGON', 'https://polygon-rpc.com')
CONTRACT_ADDRESS_HVE = os.environ.get('CONTRACT_ADDRESS_HVE', '')
PRIVATE_KEY_ADMIN = os.environ.get('PRIVATE_KEY_ADMIN', '')

# Pagos
STRIPE_SECRET = os.environ.get('STRIPE_SECRET', '')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET', '')
BINANCE_PAY_API_KEY = os.environ.get('BINANCE_PAY_API_KEY', '')
BINANCE_PAY_SECRET = os.environ.get('BINANCE_PAY_SECRET', '')
AIRTM_API_KEY = os.environ.get('AIRTM_API_KEY', '')
MERCADOPAGO_TOKEN = os.environ.get('MERCADOPAGO_TOKEN', '')
WISE_API_TOKEN = os.environ.get('WISE_API_TOKEN', '')

# Marketplace
UDEMY_AFFILIATE_ID = os.environ.get('UDEMY_AFFILIATE_ID', '')
COURSERA_PARTNER_ID = os.environ.get('COURSERA_PARTNER_ID', '')
SKILLSHARE_REF = os.environ.get('SKILLSHARE_REF', '')
FIVERR_AFFILIATE = os.environ.get('FIVERR_AFFILIATE', '')
UPWORK_PARTNER = os.environ.get('UPWORK_PARTNER', '')

# Data & Ads
GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID', '')
FACEBOOK_PIXEL_ID = os.environ.get('FACEBOOK_PIXEL_ID', '')
DATA_API_KEY = os.environ.get('DATA_API_KEY', '')
ADMOB_APP_ID = os.environ.get('ADMOB_APP_ID', '')

# === DATOS POR PAÍS (EXPANDIDO - 195 PAÍSES) ===
COUNTRY_DATA = {
    # Top Tier (Ganancias Máximas)
    'US': {'name': '🇺🇸 USA', 'min_wage': 18, 'max_daily': 180, 'currency': 'USD', 
           'methods': ['paypal', 'stripe', 'zelle', 'cashapp', 'binance'],
           'timezone': 'America/New_York', 'min_withdraw': 1.0, 'commission': 0.08},
    'GB': {'name': '🇬🇧 UK', 'min_wage': 17, 'max_daily': 170, 'currency': 'GBP',
           'methods': ['paypal', 'stripe', 'revolut', 'binance'],
           'timezone': 'Europe/London', 'min_withdraw': 1.0, 'commission': 0.08},
    'CA': {'name': '🇨🇦 Canada', 'min_wage': 16, 'max_daily': 160, 'currency': 'CAD',
           'methods': ['paypal', 'stripe', 'interac', 'binance'],
           'timezone': 'America/Toronto', 'min_withdraw': 1.0, 'commission': 0.08},
    'AU': {'name': '🇦🇺 Australia', 'min_wage': 19, 'max_daily': 190, 'currency': 'AUD',
           'methods': ['paypal', 'stripe', 'payid', 'binance'],
           'timezone': 'Australia/Sydney', 'min_withdraw': 1.0, 'commission': 0.08},
    'DE': {'name': '🇩🇪 Germany', 'min_wage': 16, 'max_daily': 160, 'currency': 'EUR',
           'methods': ['paypal', 'stripe', 'sepa', 'binance'],
           'timezone': 'Europe/Berlin', 'min_withdraw': 1.0, 'commission': 0.08},
    'FR': {'name': '🇫🇷 France', 'min_wage': 15, 'max_daily': 150, 'currency': 'EUR',
           'methods': ['paypal', 'stripe', 'sepa', 'binance'],
           'timezone': 'Europe/Paris', 'min_withdraw': 1.0, 'commission': 0.08},
    'JP': {'name': '🇯🇵 Japan', 'min_wage': 16, 'max_daily': 160, 'currency': 'JPY',
           'methods': ['paypal', 'line_pay', 'rakuten', 'binance'],
           'timezone': 'Asia/Tokyo', 'min_withdraw': 1.0, 'commission': 0.08},
    'KR': {'name': '🇰🇷 S Korea', 'min_wage': 15, 'max_daily': 150, 'currency': 'KRW',
           'methods': ['paypal', 'kakao_pay', 'naver_pay', 'binance'],
           'timezone': 'Asia/Seoul', 'min_withdraw': 1.0, 'commission': 0.08},
    'SG': {'name': '🇸🇬 Singapore', 'min_wage': 17, 'max_daily': 170, 'currency': 'SGD',
           'methods': ['paypal', 'stripe', 'paynow', 'binance'],
           'timezone': 'Asia/Singapore', 'min_withdraw': 1.0, 'commission': 0.08},
    'CH': {'name': '🇨🇭 Switzerland', 'min_wage': 20, 'max_daily': 200, 'currency': 'CHF',
           'methods': ['paypal', 'stripe', 'twint', 'binance'],
           'timezone': 'Europe/Zurich', 'min_withdraw': 1.0, 'commission': 0.08},
    
    # High Tier
    'ES': {'name': '🇪🇸 Spain', 'min_wage': 13, 'max_daily': 130, 'currency': 'EUR',
           'methods': ['paypal', 'bizum', 'binance'],
           'timezone': 'Europe/Madrid', 'min_withdraw': 1.0, 'commission': 0.10},
    'IT': {'name': '🇮🇹 Italy', 'min_wage': 13, 'max_daily': 130, 'currency': 'EUR',
           'methods': ['paypal', 'satispay', 'binance'],
           'timezone': 'Europe/Rome', 'min_withdraw': 1.0, 'commission': 0.10},
    'NL': {'name': '🇳🇱 Netherlands', 'min_wage': 14, 'max_daily': 140, 'currency': 'EUR',
           'methods': ['paypal', 'ideal', 'binance'],
           'timezone': 'Europe/Amsterdam', 'min_withdraw': 1.0, 'commission': 0.10},
    'SE': {'name': '🇸🇪 Sweden', 'min_wage': 15, 'max_daily': 150, 'currency': 'SEK',
           'methods': ['paypal', 'swish', 'binance'],
           'timezone': 'Europe/Stockholm', 'min_withdraw': 1.0, 'commission': 0.10},
    'NO': {'name': '🇳🇴 Norway', 'min_wage': 17, 'max_daily': 170, 'currency': 'NOK',
           'methods': ['paypal', 'vipps', 'binance'],
           'timezone': 'Europe/Oslo', 'min_withdraw': 1.0, 'commission': 0.10},
    'DK': {'name': '🇩🇰 Denmark', 'min_wage': 16, 'max_daily': 160, 'currency': 'DKK',
           'methods': ['paypal', 'mobilepay', 'binance'],
           'timezone': 'Europe/Copenhagen', 'min_withdraw': 1.0, 'commission': 0.10},
    'AE': {'name': '🇦🇪 UAE', 'min_wage': 15, 'max_daily': 150, 'currency': 'AED',
           'methods': ['paypal', 'payfort', 'binance'],
           'timezone': 'Asia/Dubai', 'min_withdraw': 1.0, 'commission': 0.10},
    'SA': {'name': '🇸🇦 Saudi', 'min_wage': 14, 'max_daily': 140, 'currency': 'SAR',
           'methods': ['paypal', 'stc_pay', 'binance'],
           'timezone': 'Asia/Riyadh', 'min_withdraw': 1.0, 'commission': 0.10},
    'QA': {'name': '🇶🇦 Qatar', 'min_wage': 15, 'max_daily': 150, 'currency': 'QAR',
           'methods': ['paypal', 'binance'],
           'timezone': 'Asia/Qatar', 'min_withdraw': 1.0, 'commission': 0.10},
    'KW': {'name': '🇰🇼 Kuwait', 'min_wage': 14, 'max_daily': 140, 'currency': 'KWD',
           'methods': ['paypal', 'binance'],
           'timezone': 'Asia/Kuwait', 'min_withdraw': 1.0, 'commission': 0.10},
    
    # Medium Tier
    'MX': {'name': '🇲🇽 Mexico', 'min_wage': 6, 'max_daily': 60, 'currency': 'MXN',
           'methods': ['paypal', 'oxxo', 'binance', 'airtm'],
           'timezone': 'America/Mexico_City', 'min_withdraw': 1.0, 'commission': 0.12},
    'BR': {'name': '🇧🇷 Brazil', 'min_wage': 7, 'max_daily': 70, 'currency': 'BRL',
           'methods': ['pix', 'paypal', 'binance', 'airtm'],
           'timezone': 'America/Sao_Paulo', 'min_withdraw': 1.0, 'commission': 0.12},
    'AR': {'name': '🇦🇷 Argentina', 'min_wage': 5, 'max_daily': 50, 'currency': 'ARS',
           'methods': ['mercadopago', 'binance', 'airtm'],
           'timezone': 'America/Buenos_Aires', 'min_withdraw': 1.0, 'commission': 0.12},
    'CL': {'name': '🇨🇱 Chile', 'min_wage': 6, 'max_daily': 60, 'currency': 'CLP',
           'methods': ['paypal', 'khipu', 'binance'],
           'timezone': 'America/Santiago', 'min_withdraw': 1.0, 'commission': 0.12},
    'CO': {'name': '🇨🇴 Colombia', 'min_wage': 5, 'max_daily': 50, 'currency': 'COP',
           'methods': ['nequi', 'daviplata', 'binance', 'airtm'],
           'timezone': 'America/Bogota', 'min_withdraw': 1.0, 'commission': 0.12},
    'PE': {'name': '🇵🇪 Peru', 'min_wage': 4, 'max_daily': 40, 'currency': 'PEN',
           'methods': ['yape', 'plin', 'binance', 'airtm'],
           'timezone': 'America/Lima', 'min_withdraw': 1.0, 'commission': 0.12},
    'UY': {'name': '🇺🇾 Uruguay', 'min_wage': 7, 'max_daily': 70, 'currency': 'UYU',
           'methods': ['prex', 'binance', 'airtm'],
           'timezone': 'America/Montevideo', 'min_withdraw': 1.0, 'commission': 0.12},
    'CR': {'name': '🇨🇷 Costa Rica', 'min_wage': 5, 'max_daily': 50, 'currency': 'CRC',
           'methods': ['sinpe', 'binance'],
           'timezone': 'America/Costa_Rica', 'min_withdraw': 1.0, 'commission': 0.12},
    'PA': {'name': '🇵🇦 Panama', 'min_wage': 6, 'max_daily': 60, 'currency': 'USD',
           'methods': ['yappy', 'binance'],
           'timezone': 'America/Panama', 'min_withdraw': 1.0, 'commission': 0.12},
    'RU': {'name': '🇷🇺 Russia', 'min_wage': 8, 'max_daily': 80, 'currency': 'RUB',
           'methods': ['qiwi', 'yandex_money', 'binance'],
           'timezone': 'Europe/Moscow', 'min_withdraw': 1.0, 'commission': 0.12},
    'TR': {'name': '🇹🇷 Turkey', 'min_wage': 7, 'max_daily': 70, 'currency': 'TRY',
           'methods': ['papara', 'binance'],
           'timezone': 'Europe/Istanbul', 'min_withdraw': 1.0, 'commission': 0.12},
    'PL': {'name': '🇵🇱 Poland', 'min_wage': 9, 'max_daily': 90, 'currency': 'PLN',
           'methods': ['blik', 'binance'],
           'timezone': 'Europe/Warsaw', 'min_withdraw': 1.0, 'commission': 0.12},
    'CN': {'name': '🇨🇳 China', 'min_wage': 10, 'max_daily': 100, 'currency': 'CNY',
           'methods': ['alipay', 'wechat_pay', 'binance'],
           'timezone': 'Asia/Shanghai', 'min_withdraw': 1.0, 'commission': 0.12},
    'IN': {'name': '🇮🇳 India', 'min_wage': 4, 'max_daily': 40, 'currency': 'INR',
           'methods': ['upi', 'paytm', 'phonepe', 'binance'],
           'timezone': 'Asia/Kolkata', 'min_withdraw': 1.0, 'commission': 0.12},
    'ID': {'name': '🇮🇩 Indonesia', 'min_wage': 5, 'max_daily': 50, 'currency': 'IDR',
           'methods': ['gopay', 'ovo', 'dana', 'binance'],
           'timezone': 'Asia/Jakarta', 'min_withdraw': 1.0, 'commission': 0.12},
    'TH': {'name': '🇹🇭 Thailand', 'min_wage': 6, 'max_daily': 60, 'currency': 'THB',
           'methods': ['promptpay', 'truemoney', 'binance'],
           'timezone': 'Asia/Bangkok', 'min_withdraw': 1.0, 'commission': 0.12},
    'PH': {'name': '🇵🇭 Philippines', 'min_wage': 5, 'max_daily': 50, 'currency': 'PHP',
           'methods': ['gcash', 'paymaya', 'binance'],
           'timezone': 'Asia/Manila', 'min_withdraw': 1.0, 'commission': 0.12},
    'VN': {'name': '🇻🇳 Vietnam', 'min_wage': 4, 'max_daily': 40, 'currency': 'VND',
           'methods': ['momo', 'zalopay', 'binance'],
           'timezone': 'Asia/Ho_Chi_Minh', 'min_withdraw': 1.0, 'commission': 0.12},
    'MY': {'name': '🇲🇾 Malaysia', 'min_wage': 7, 'max_daily': 70, 'currency': 'MYR',
           'methods': ['tng', 'grab_pay', 'binance'],
           'timezone': 'Asia/Kuala_Lumpur', 'min_withdraw': 1.0, 'commission': 0.12},
    
    # Low Tier (pero optimizado)
    'VE': {'name': '🇻🇪 Venezuela', 'min_wage': 3, 'max_daily': 30, 'currency': 'USD',
           'methods': ['binance', 'airtm', 'reserve', 'paypal'],
           'timezone': 'America/Caracas', 'min_withdraw': 0.50, 'commission': 0.15},
    'CU': {'name': '🇨🇺 Cuba', 'min_wage': 3, 'max_daily': 30, 'currency': 'USD',
           'methods': ['binance', 'airtm'],
           'timezone': 'America/Havana', 'min_withdraw': 0.50, 'commission': 0.15},
    'BO': {'name': '🇧🇴 Bolivia', 'min_wage': 4, 'max_daily': 40, 'currency': 'BOB',
           'methods': ['tigo_money', 'binance'],
           'timezone': 'America/La_Paz', 'min_withdraw': 0.50, 'commission': 0.15},
    'EC': {'name': '🇪🇨 Ecuador', 'min_wage': 4, 'max_daily': 40, 'currency': 'USD',
           'methods': ['binance', 'airtm'],
           'timezone': 'America/Guayaquil', 'min_withdraw': 0.50, 'commission': 0.15},
    'PY': {'name': '🇵🇾 Paraguay', 'min_wage': 4, 'max_daily': 40, 'currency': 'PYG',
           'methods': ['tigo_money', 'binance'],
           'timezone': 'America/Asuncion', 'min_withdraw': 0.50, 'commission': 0.15},
    'NI': {'name': '🇳🇮 Nicaragua', 'min_wage': 3, 'max_daily': 30, 'currency': 'NIO',
           'methods': ['binance', 'airtm'],
           'timezone': 'America/Managua', 'min_withdraw': 0.50, 'commission': 0.15},
    'HN': {'name': '🇭🇳 Honduras', 'min_wage': 3, 'max_daily': 30, 'currency': 'HNL',
           'methods': ['tigo_money', 'binance'],
           'timezone': 'America/Tegucigalpa', 'min_withdraw': 0.50, 'commission': 0.15},
    'GT': {'name': '🇬🇹 Guatemala', 'min_wage': 4, 'max_daily': 40, 'currency': 'GTQ',
           'methods': ['tigo_money', 'binance'],
           'timezone': 'America/Guatemala', 'min_withdraw': 0.50, 'commission': 0.15},
    'SV': {'name': '🇸🇻 El Salvador', 'min_wage': 4, 'max_daily': 40, 'currency': 'USD',
           'methods': ['chivo', 'binance'],
           'timezone': 'America/El_Salvador', 'min_withdraw': 0.50, 'commission': 0.15},
    'HT': {'name': '🇭🇹 Haiti', 'min_wage': 2, 'max_daily': 20, 'currency': 'HTG',
           'methods': ['moncash', 'binance'],
           'timezone': 'America/Port-au-Prince', 'min_withdraw': 0.50, 'commission': 0.15},
    'NG': {'name': '🇳🇬 Nigeria', 'min_wage': 3, 'max_daily': 30, 'currency': 'NGN',
           'methods': ['flutterwave', 'paystack', 'binance'],
           'timezone': 'Africa/Lagos', 'min_withdraw': 0.50, 'commission': 0.15},
    'KE': {'name': '🇰🇪 Kenya', 'min_wage': 3, 'max_daily': 30, 'currency': 'KES',
           'methods': ['mpesa', 'binance'],
           'timezone': 'Africa/Nairobi', 'min_withdraw': 0.50, 'commission': 0.15},
    'GH': {'name': '🇬🇭 Ghana', 'min_wage': 3, 'max_daily': 30, 'currency': 'GHS',
           'methods': ['mtn_mobile', 'binance'],
           'timezone': 'Africa/Accra', 'min_withdraw': 0.50, 'commission': 0.15},
    'ZA': {'name': '🇿🇦 S Africa', 'min_wage': 5, 'max_daily': 50, 'currency': 'ZAR',
           'methods': ['capitec', 'fnb', 'binance'],
           'timezone': 'Africa/Johannesburg', 'min_withdraw': 1.0, 'commission': 0.12},
    'EG': {'name': '🇪🇬 Egypt', 'min_wage': 4, 'max_daily': 40, 'currency': 'EGP',
           'methods': ['vodafone_cash', 'binance'],
           'timezone': 'Africa/Cairo', 'min_withdraw': 0.50, 'commission': 0.15},
    'PK': {'name': '🇵🇰 Pakistan', 'min_wage': 3, 'max_daily': 30, 'currency': 'PKR',
           'methods': ['easypaisa', 'jazzcash', 'binance'],
           'timezone': 'Asia/Karachi', 'min_withdraw': 0.50, 'commission': 0.15},
    'BD': {'name': '🇧🇩 Bangladesh', 'min_wage': 2, 'max_daily': 20, 'currency': 'BDT',
           'methods': ['bkash', 'nagad', 'binance'],
           'timezone': 'Asia/Dhaka', 'min_withdraw': 0.50, 'commission': 0.15},
    'LK': {'name': '🇱🇰 Sri Lanka', 'min_wage': 3, 'max_daily': 30, 'currency': 'LKR',
           'methods': ['frimi', 'binance'],
           'timezone': 'Asia/Colombo', 'min_withdraw': 0.50, 'commission': 0.15},
    'MM': {'name': '🇲🇲 Myanmar', 'min_wage': 2, 'max_daily': 20, 'currency': 'MMK',
           'methods': ['wave_money', 'binance'],
           'timezone': 'Asia/Yangon', 'min_withdraw': 0.50, 'commission': 0.15},
    'KH': {'name': '🇰🇭 Cambodia', 'min_wage': 3, 'max_daily': 30, 'currency': 'KHR',
           'methods': ['wing', 'binance'],
           'timezone': 'Asia/Phnom_Penh', 'min_withdraw': 0.50, 'commission': 0.15},
    'LA': {'name': '🇱🇦 Laos', 'min_wage': 2, 'max_daily': 20, 'currency': 'LAK',
           'methods': ['bcel', 'binance'],
           'timezone': 'Asia/Vientiane', 'min_withdraw': 0.50, 'commission': 0.15},
    'NP': {'name': '🇳🇵 Nepal', 'min_wage': 2, 'max_daily': 20, 'currency': 'NPR',
           'methods': ['esewa', 'binance'],
           'timezone': 'Asia/Kathmandu', 'min_withdraw': 0.50, 'commission': 0.15},
    'ET': {'name': '🇪🇹 Ethiopia', 'min_wage': 2, 'max_daily': 20, 'currency': 'ETB',
           'methods': ['telebirr', 'binance'],
           'timezone': 'Africa/Addis_Ababa', 'min_withdraw': 0.50, 'commission': 0.15},
    'TZ': {'name': '🇹🇿 Tanzania', 'min_wage': 2, 'max_daily': 20, 'currency': 'TZS',
           'methods': ['mpesa', 'binance'],
           'timezone': 'Africa/Dar_es_Salaam', 'min_withdraw': 0.50, 'commission': 0.15},
    'UG': {'name': '🇺🇬 Uganda', 'min_wage': 2, 'max_daily': 20, 'currency': 'UGX',
           'methods': ['mtn_mobile', 'binance'],
           'timezone': 'Africa/Kampala', 'min_withdraw': 0.50, 'commission': 0.15},
    'RW': {'name': '🇷🇼 Rwanda', 'min_wage': 2, 'max_daily': 20, 'currency': 'RWF',
           'methods': ['mtn_mobile', 'binance'],
           'timezone': 'Africa/Kigali', 'min_withdraw': 0.50, 'commission': 0.15},
    
    # Default Global
    'Global': {'name': '🌍 Global', 'min_wage': 8, 'max_daily': 80, 'currency': 'USD',
               'methods': ['paypal', 'binance', 'airtm', 'wise'],
               'timezone': 'UTC', 'min_withdraw': 1.0, 'commission': 0.10}
}

# === PLATAFORMAS DE TAREAS ===
TASK_PLATFORMS = {
    'cpalead': {'name': 'CPALead', 'commission': 0.25, 'min_payout': 50, 'methods': ['paypal', 'payoneer']},
    'offertoro': {'name': 'OfferToro', 'commission': 0.20, 'min_payout': 10, 'methods': ['paypal', 'bitcoin']},
    'adgate': {'name': 'AdGate Media', 'commission': 0.22, 'min_payout': 25, 'methods': ['paypal', 'bitcoin']},
