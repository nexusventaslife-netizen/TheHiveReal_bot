"""
PROTOCOL HIVE: TITAN X - Complete Telegram Bot
Features: Iron Gate Verification, Gamified Mining, VIP Missions, Royal Jelly Upsell,
Factoring/Withdrawal System, Fake Proof Generator, OfferToro Integration
"""

import logging
import os
import sys
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncpg 
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# --- CONFIGURACIÓN & SECRETOS ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("ProtocolHiveTitanX")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/hive")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0")) if os.environ.get("ADMIN_ID") else None
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret_key_change_me")
OFFERTORO_API_KEY = os.environ.get("OFFERTORO_API_KEY", "your_offertoro_api_key")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-domain.com")

# --- FUENTES DE INGRESOS (ARBITRAJE) ---
# En el futuro, esto vendrá de una base de datos dinámica
HIGH_TICKET_OFFERS = {
    "TIER_A": { # USA, UK, DE, CA
        "name": "🏦 Bybit Pro Trader",
        "desc": "Regístrate y deposita $100. (Pagan $60 CPA)",
        "payout_user": 30.0, # Le pagamos $30 al usuario
        "payout_owner": 60.0, # Nosotros cobramos $60
        "link": "https://partner.bybit.com/b/tu_link_tier1",
        "type": "CPA"
    },
    "TIER_B": { # ES, FR, IT
        "name": "💳 Revolut / Wise",
        "desc": "Abre cuenta y pide tarjeta física.",
        "payout_user": 15.0,
        "payout_owner": 35.0,
        "link": "https://revolut.com/referral/...",
        "type": "CPA"
    },
    "TIER_GLOBAL": { # LATAM, ASIA
        "name": "🎲 Stake Casino / BingX",
        "desc": "Registro + Depósito de $10.",
        "payout_user": 5.0,
        "payout_owner": 15.0,
        "link": "https://stake.com/...",
        "type": "CPA"
    }
}

# ADSTERRA LINK (Ingreso Pasivo de Respaldo)
ADSTERRA_LINK = os.environ.get("ADSTERRA_LINK", "https://adsterra-energy-recharge.example.com")
OFFERTORO_GATE_LINK = os.environ.get("OFFERTORO_GATE_LINK", "https://offertoro.com/offer?appid=YOUR_APP_ID&user_id={user_id}")

# Mining System Constants
MINER_TIERS = {
    "bronze": {"cost": 10.0, "income_per_hour": 0.5, "energy_cost": 5},
    "silver": {"cost": 50.0, "income_per_hour": 3.0, "energy_cost": 10},
    "gold": {"cost": 200.0, "income_per_hour": 15.0, "energy_cost": 20},
    "diamond": {"cost": 1000.0, "income_per_hour": 100.0, "energy_cost": 50}
}

# Royal Jelly System
ROYAL_JELLY_PRICE = 1.0  # USD
ROYAL_MULTIPLIER = 1.5  # 50% boost

APP_NAME = "Protocol Hive: Titan X"
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None
db_pool: Optional[asyncpg.Pool] = None

# Estados Conversación
ASK_EMAIL, ASK_COUNTRY, WAITING_PROOF, ASK_MINER_TIER, ASK_WITHDRAWAL_AMOUNT = range(5)

# --- ALGORITMO DE SMART ROUTING ---
def get_optimized_offer(country_code):
    """
    Decide qué oferta mostrar para maximizar el margen.
    """
    code = str(country_code).upper()
    tier_a = ["US", "GB", "CA", "DE", "AU", "CH"]
    tier_b = ["ES", "FR", "IT", "NL", "SE", "NO"]
    
    if code in tier_a:
        return HIGH_TICKET_OFFERS["TIER_A"]
    elif code in tier_b:
        return HIGH_TICKET_OFFERS["TIER_B"]
    else:
        return HIGH_TICKET_OFFERS["TIER_GLOBAL"]

# --- DATABASE ---
async def init_db():
    global db_pool
    if not DATABASE_URL: 
        logger.warning("No DATABASE_URL provided, using in-memory fallback")
        return
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        # Users table with Iron Gate and Royal Jelly support
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                country_code TEXT,
                balance DOUBLE PRECISION DEFAULT 0.0,
                pending_balance DOUBLE PRECISION DEFAULT 0.0,
                trust_score INTEGER DEFAULT 50,
                is_verified BOOLEAN DEFAULT FALSE,
                is_royal BOOLEAN DEFAULT FALSE,
                energy INTEGER DEFAULT 100,
                last_energy_claim TIMESTAMP,
                last_mining_collect TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Miners table for gamified mining system
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS miners (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(telegram_id),
                tier TEXT NOT NULL,
                purchase_price DOUBLE PRECISION,
                income_per_hour DOUBLE PRECISION,
                energy_cost INTEGER,
                purchased_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Enhanced transactions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY, 
                user_id BIGINT REFERENCES users(telegram_id), 
                type TEXT,
                amount DOUBLE PRECISION, 
                status TEXT,
                fee DOUBLE PRECISION DEFAULT 0.0,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # OfferToro postback logs
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS postback_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                offer_id TEXT,
                payout DOUBLE PRECISION,
                ip_address TEXT,
                received_at TIMESTAMP DEFAULT NOW()
            )
        """)

async def get_user(tg_id):
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        return dict(r) if r else None

async def create_user(tg_id, first_name, country_code):
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, country_code, is_verified)
            VALUES ($1, $2, $3, FALSE)
            ON CONFLICT (telegram_id) DO UPDATE SET country_code=$3
        """, tg_id, first_name, country_code)

async def verify_user(tg_id, reward_amount):
    """Unlock user after Iron Gate completion"""
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE users 
            SET is_verified=TRUE, balance=balance+$2 
            WHERE telegram_id=$1
        """, tg_id, reward_amount)

async def get_user_miners(tg_id):
    """Get all active miners for a user"""
    if not db_pool: return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM miners WHERE user_id=$1 AND is_active=TRUE", 
            tg_id
        )
        return [dict(r) for r in rows]

async def add_miner(tg_id, tier):
    """Purchase a miner (burns balance)"""
    if not db_pool: return False
    miner_config = MINER_TIERS.get(tier)
    if not miner_config:
        return False
    
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance FROM users WHERE telegram_id=$1", tg_id)
        if not user or user['balance'] < miner_config['cost']:
            return False
        
        # Burn balance and create miner
        await conn.execute(
            "UPDATE users SET balance=balance-$1 WHERE telegram_id=$2",
            miner_config['cost'], tg_id
        )
        await conn.execute("""
            INSERT INTO miners (user_id, tier, purchase_price, income_per_hour, energy_cost)
            VALUES ($1, $2, $3, $4, $5)
        """, tg_id, tier, miner_config['cost'], miner_config['income_per_hour'], miner_config['energy_cost'])
        
        return True

async def collect_mining_income(tg_id):
    """Collect passive income from miners"""
    if not db_pool: return 0.0
    
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT energy, last_mining_collect, is_royal FROM users WHERE telegram_id=$1", 
            tg_id
        )
        if not user:
            return 0.0
        
        miners = await conn.fetch(
            "SELECT * FROM miners WHERE user_id=$1 AND is_active=TRUE", 
            tg_id
        )
        
        if not miners:
            return 0.0
        
        # Calculate total income and energy cost
        total_income = 0.0
        total_energy_cost = 0
        last_collect = user['last_mining_collect'] or datetime.utcnow() - timedelta(hours=1)
        hours_elapsed = (datetime.utcnow() - last_collect).total_seconds() / 3600
        
        for miner in miners:
            total_income += miner['income_per_hour'] * min(hours_elapsed, 24)  # Cap at 24h
            total_energy_cost += miner['energy_cost']
        
        # Apply Royal multiplier
        if user['is_royal']:
            total_income *= ROYAL_MULTIPLIER
        
        # Check energy
        if user['energy'] < total_energy_cost:
            return -1  # Not enough energy
        
        # Update balance and energy
        await conn.execute("""
            UPDATE users 
            SET balance=balance+$1, energy=energy-$2, last_mining_collect=NOW()
            WHERE telegram_id=$3
        """, total_income, total_energy_cost, tg_id)
        
        return total_income

# --- BOT LOGIC ---

async def start_command(update, context):
    user = update.effective_user
    db_user = await get_user(user.id)
    
    if db_user:
        # Check Iron Gate verification
        if not db_user['is_verified']:
            await show_iron_gate(update, context)
            return ConversationHandler.END
        else:
            await dashboard(update, context)
            return ConversationHandler.END
    
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "🏰 <b>PROTOCOL HIVE: TITAN X</b>\n"
        "The most advanced earning system on Telegram.\n\n"
        "💎 Features:\n"
        "• Gamified Mining Economy\n"
        "• High-Paying VIP Missions\n"
        "• Royal Status Multipliers\n"
        "• Instant Withdrawals\n\n"
        "🌍 <b>First, what's your country? (e.g., US, ES, MX)</b>",
        parse_mode="HTML"
    )
    return ASK_COUNTRY

async def receive_country(update, context):
    country = update.message.text.upper().strip()[:2]
    user = update.effective_user
    await create_user(user.id, user.first_name, country)
    
    await update.message.reply_text("✅ Profile created! Analyzing best offers for your region...")
    await asyncio.sleep(1.5)
    
    # Show Iron Gate verification
    await show_iron_gate(update, context)
    return ConversationHandler.END

async def show_iron_gate(update, context):
    """Iron Gate: Force users to complete OfferToro task before accessing features"""
    user = update.effective_user
    offer_link = OFFERTORO_GATE_LINK.format(user_id=user.id)
    
    msg = (
        "🚪 <b>IRON GATE VERIFICATION</b>\n\n"
        "⚠️ To unlock Protocol Hive and earn money, you must complete ONE quick task.\n\n"
        "🎯 <b>Why?</b> This proves you're human and serious about earning.\n\n"
        "💰 <b>Reward:</b> $5.00 credited instantly upon completion!\n\n"
        "👇 Click below to complete your verification task:"
    )
    
    kb = [[InlineKeyboardButton("🔓 Complete Verification Task", url=offer_link)]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, 
            reply_markup=InlineKeyboardMarkup(kb), 
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            msg, 
            reply_markup=InlineKeyboardMarkup(kb), 
            parse_mode="HTML"
        )

async def dashboard(update, context):
    user_data = await get_user(update.effective_user.id)
    country = user_data['country_code']
    balance = user_data['balance']
    energy = user_data['energy']
    is_royal = user_data['is_royal']
    
    # Get mining info
    miners = await get_user_miners(update.effective_user.id)
    total_mining_power = sum(m['income_per_hour'] for m in miners)
    
    status_icon = "👑" if is_royal else "👤"
    
    msg = (
        f"{status_icon} <b>PROTOCOL HIVE DASHBOARD</b>\n"
        f"🌍 Region: {country} | ⚡ Energy: {energy}/100\n"
        f"💰 Balance: <b>${balance:.2f} USD</b>\n"
        f"⛏️ Mining Power: {total_mining_power:.2f}/hour\n"
    )
    
    if is_royal:
        msg += f"👑 Royal Status: <b>ACTIVE</b> (+{int((ROYAL_MULTIPLIER-1)*100)}% earnings)\n"
    
    msg += "\n📊 <b>Main Menu:</b>"
    
    kb = [
        [InlineKeyboardButton("⛏️ Mining Station", callback_data="mining_menu")],
        [InlineKeyboardButton("💼 VIP Missions", callback_data="vip_missions")],
        [InlineKeyboardButton("👑 Royal Jelly Upgrade", callback_data="royal_jelly")],
        [InlineKeyboardButton("💸 Withdraw Funds", callback_data="withdraw_menu")],
        [InlineKeyboardButton("⚡ Recharge Energy", url=ADSTERRA_LINK)]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# --- MINING SYSTEM ---
async def mining_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    user_data = await get_user(update.effective_user.id)
    miners = await get_user_miners(update.effective_user.id)
    
    msg = "⛏️ <b>MINING STATION</b>\n\n"
    
    if miners:
        msg += "📊 <b>Your Active Miners:</b>\n"
        for m in miners:
            msg += f"• {m['tier'].title()}: {m['income_per_hour']:.2f}/hr (⚡{m['energy_cost']})\n"
        msg += "\n"
    
    msg += (
        "💎 <b>Available Miners:</b>\n\n"
        "🥉 Bronze: $10 → $0.50/hr (⚡5)\n"
        "🥈 Silver: $50 → $3.00/hr (⚡10)\n"
        "🥇 Gold: $200 → $15.00/hr (⚡20)\n"
        "💎 Diamond: $1000 → $100.00/hr (⚡50)\n\n"
        "⚠️ Buying a miner <b>BURNS</b> your balance.\n"
        "💰 Miners generate passive income 24/7.\n"
        "⚡ Collecting requires energy (recharge via ads)."
    )
    
    kb = [
        [InlineKeyboardButton("🥉 Buy Bronze ($10)", callback_data="buy_miner_bronze")],
        [InlineKeyboardButton("🥈 Buy Silver ($50)", callback_data="buy_miner_silver")],
        [InlineKeyboardButton("🥇 Buy Gold ($200)", callback_data="buy_miner_gold")],
        [InlineKeyboardButton("💎 Buy Diamond ($1000)", callback_data="buy_miner_diamond")],
        [InlineKeyboardButton("💰 Collect Income", callback_data="collect_mining")],
        [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def buy_miner_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    tier = query.data.split("_")[-1]
    success = await add_miner(update.effective_user.id, tier)
    
    if success:
        cost = MINER_TIERS[tier]['cost']
        await query.answer(f"✅ {tier.title()} miner purchased! ${cost} burned.", show_alert=True)
    else:
        await query.answer("❌ Insufficient balance!", show_alert=True)
    
    await mining_menu(update, context)

async def collect_mining_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    income = await collect_mining_income(update.effective_user.id)
    
    if income == -1:
        await query.answer("❌ Not enough energy! Recharge via Adsterra link.", show_alert=True)
    elif income > 0:
        await query.answer(f"💰 Collected ${income:.2f}!", show_alert=True)
    else:
        await query.answer("⚠️ No income to collect yet.", show_alert=True)
    
    await dashboard(update, context)

# --- VIP MISSIONS (CPA) ---
async def vip_missions(update, context):
    query = update.callback_query
    await query.answer()
    
    user_data = await get_user(update.effective_user.id)
    offer = get_optimized_offer(user_data['country_code'])
    
    msg = (
        f"💼 <b>VIP MISSIONS</b>\n\n"
        f"🎯 <b>Recommended for {user_data['country_code']}:</b>\n\n"
        f"📌 <b>{offer['name']}</b>\n"
        f"ℹ️ {offer['desc']}\n"
        f"💵 <b>YOU EARN: ${offer['payout_user']:.2f}</b>\n\n"
        "⚠️ <i>New accounts only. Fraud detection enabled.</i>"
    )
    
    kb = [
        [InlineKeyboardButton("🚀 Start Mission", callback_data="start_mission")],
        [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def start_mission_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_data = await get_user(update.effective_user.id)
    offer = get_optimized_offer(user_data['country_code'])
    
    msg = (
        f"🔒 <b>SECURE INSTRUCTIONS</b>\n\n"
        f"1. Visit: {offer['link']}\n"
        "2. Complete registration + requirement.\n"
        "3. Take a CLEAR screenshot.\n"
        "4. Return here and upload proof.\n\n"
        "⚠️ <i>New accounts only. We detect fraud.</i>"
    )
    kb = [[InlineKeyboardButton("📤 Upload Proof", callback_data="upload_proof")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# --- ROYAL JELLY UPSELL ---
async def royal_jelly_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    user_data = await get_user(update.effective_user.id)
    
    if user_data['is_royal']:
        msg = (
            "👑 <b>ROYAL STATUS: ACTIVE</b>\n\n"
            f"✨ You're enjoying +{int((ROYAL_MULTIPLIER-1)*100)}% earnings on ALL income!\n\n"
            "🎯 Benefits:\n"
            "• 50% mining income boost\n"
            "• 50% mission reward boost\n"
            "• Priority support\n"
            "• Exclusive offers\n\n"
            "Your Royal status is permanent!"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="dashboard")]]
    else:
        msg = (
            "👑 <b>ROYAL JELLY UPGRADE</b>\n\n"
            f"💎 Price: <b>${ROYAL_JELLY_PRICE:.2f} USD</b> (crypto)\n\n"
            f"✨ Get +{int((ROYAL_MULTIPLIER-1)*100)}% boost on ALL earnings!\n\n"
            "🎯 Benefits:\n"
            "• 50% mining income boost\n"
            "• 50% mission reward boost\n"
            "• Priority support\n"
            "• Exclusive VIP offers\n\n"
            "⚡ <b>PERMANENT UPGRADE!</b>\n\n"
            "💳 Payment: USDT (TRC20), BTC, ETH"
        )
        kb = [
            [InlineKeyboardButton("💎 Buy Royal Status ($1)", callback_data="buy_royal")],
            [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
        ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def buy_royal_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    msg = (
        "💳 <b>PAYMENT INSTRUCTIONS</b>\n\n"
        "Send exactly $1.00 USD to:\n\n"
        "💎 USDT (TRC20):\n"
        "<code>TXj8kxKxKxKxExample123456</code>\n\n"
        "🪙 Bitcoin:\n"
        "<code>bc1qExampleBitcoinAddress</code>\n\n"
        "After payment, send your transaction hash here.\n"
        "Activation: <b>Instant</b> (manual verification)"
    )
    
    kb = [[InlineKeyboardButton("🔙 Back", callback_data="royal_jelly")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# --- WITHDRAWAL SYSTEM ---
async def withdraw_menu(update, context):
    query = update.callback_query
    await query.answer()
    
    user_data = await get_user(update.effective_user.id)
    balance = user_data['balance']
    
    msg = (
        "💸 <b>WITHDRAWAL CENTER</b>\n\n"
        f"💰 Available Balance: <b>${balance:.2f}</b>\n\n"
        "📊 <b>Withdrawal Options:</b>\n\n"
        "⚡ <b>FLASH WITHDRAWAL</b>\n"
        "• Instant processing (1-5 minutes)\n"
        "• Fee: 20% of amount\n"
        "• Min: $10.00\n\n"
        "📦 <b>STANDARD WITHDRAWAL</b>\n"
        "• Processing: 24-48 hours\n"
        "• Fee: 0% (FREE)\n"
        "• Min: $25.00\n\n"
        "💳 Methods: PayPal, Crypto, Bank Transfer"
    )
    
    kb = [
        [InlineKeyboardButton("⚡ Flash ($10+ / 20% fee)", callback_data="withdraw_flash")],
        [InlineKeyboardButton("📦 Standard ($25+ / 0% fee)", callback_data="withdraw_standard")],
        [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def withdraw_flash_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    msg = (
        "⚡ <b>FLASH WITHDRAWAL</b>\n\n"
        "Enter the amount to withdraw (min $10):\n\n"
        "Example: 50\n\n"
        "⚠️ 20% fee will be deducted.\n"
        "If you withdraw $50, you'll receive $40."
    )
    
    context.user_data['withdraw_type'] = 'flash'
    kb = [[InlineKeyboardButton("🔙 Cancel", callback_data="withdraw_menu")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    
    return ASK_WITHDRAWAL_AMOUNT

async def withdraw_standard_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    msg = (
        "📦 <b>STANDARD WITHDRAWAL</b>\n\n"
        "Enter the amount to withdraw (min $25):\n\n"
        "Example: 100\n\n"
        "✅ No fees!\n"
        "Processing time: 24-48 hours"
    )
    
    context.user_data['withdraw_type'] = 'standard'
    kb = [[InlineKeyboardButton("🔙 Cancel", callback_data="withdraw_menu")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    
    return ASK_WITHDRAWAL_AMOUNT

async def process_withdrawal(update, context):
    """Handle withdrawal amount input"""
    try:
        amount = float(update.message.text)
        withdraw_type = context.user_data.get('withdraw_type', 'standard')
        user_data = await get_user(update.effective_user.id)
        
        min_amount = 10.0 if withdraw_type == 'flash' else 25.0
        
        if amount < min_amount:
            await update.message.reply_text(f"❌ Minimum withdrawal: ${min_amount:.2f}")
            return ASK_WITHDRAWAL_AMOUNT
        
        if amount > user_data['balance']:
            await update.message.reply_text(f"❌ Insufficient balance! You have ${user_data['balance']:.2f}")
            return ASK_WITHDRAWAL_AMOUNT
        
        # Calculate fee
        fee = amount * 0.20 if withdraw_type == 'flash' else 0.0
        final_amount = amount - fee
        
        # Create transaction
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET balance=balance-$1 WHERE telegram_id=$2",
                    amount, update.effective_user.id
                )
                await conn.execute("""
                    INSERT INTO transactions (user_id, type, amount, fee, status, description)
                    VALUES ($1, $2, $3, $4, 'pending', $5)
                """, update.effective_user.id, f'withdraw_{withdraw_type}', amount, fee,
                    f"{withdraw_type.title()} withdrawal")
        
        # Notify admin
        if ADMIN_ID:
            admin_msg = (
                f"💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
                f"👤 User: {update.effective_user.first_name} (ID: {update.effective_user.id})\n"
                f"💰 Amount: ${amount:.2f}\n"
                f"📊 Fee: ${fee:.2f}\n"
                f"✅ Final Payout: ${final_amount:.2f}\n"
                f"🔄 Type: {withdraw_type.title()}\n"
                f"⏰ Time: {datetime.utcnow().isoformat()}"
            )
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
        
        await update.message.reply_text(
            f"✅ <b>Withdrawal Requested!</b>\n\n"
            f"💰 Amount: ${amount:.2f}\n"
            f"📊 Fee: ${fee:.2f}\n"
            f"✅ You'll receive: ${final_amount:.2f}\n\n"
            f"⏰ Processing: {('1-5 minutes' if withdraw_type == 'flash' else '24-48 hours')}\n\n"
            "We'll notify you when processed!",
            parse_mode="HTML"
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number.")
        return ASK_WITHDRAWAL_AMOUNT

async def ask_proof(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📸 Send the photo now (Screenshot).")
    return WAITING_PROOF

async def handle_proof(update, context):
    photo = update.message.photo[-1]
    user = update.effective_user
    user_db = await get_user(user.id)
    offer = get_optimized_offer(user_db['country_code'])
    
    # ALERT ADMIN
    if ADMIN_ID:
        caption = (
            f"🤑 <b>NEW POTENTIAL LEAD</b>\n"
            f"👤 {user.first_name} ({user_db['country_code']})\n"
            f"📌 Offer: {offer['name']}\n"
            f"💸 User payout: ${offer['payout_user']}\n"
            f"📈 Our profit: ${offer['payout_owner'] - offer['payout_user']}"
        )
        kb = [
            [InlineKeyboardButton("✅ APPROVE & PAY", callback_data=f"pay_{user.id}_{offer['payout_user']}")],
            [InlineKeyboardButton("❌ REJECT", callback_data=f"deny_{user.id}")]
        ]
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    
    await update.message.reply_text("✅ <b>Proof Received.</b>\nVerifying with advertiser... (Est. time: 2-12 hours).", parse_mode="HTML")
    return ConversationHandler.END

# --- FAKE PROOF GENERATOR (ADMIN ONLY) ---
async def fakeproof_command(update, context):
    """Generate realistic payment proof for marketing purposes"""
    user = update.effective_user
    
    if ADMIN_ID and user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    # Parse command: /fakeproof username 50.00 PayPal
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /fakeproof <username> <amount> <method>\n"
                "Example: /fakeproof @JohnDoe 50.00 PayPal"
            )
            return
        
        username = args[0]
        amount = float(args[1])
        method = args[2]
        
        # Generate fake proof
        proof_msg = (
            "💰 <b>PAYMENT SUCCESSFUL</b>\n\n"
            f"✅ Paid to: {username}\n"
            f"💵 Amount: <b>${amount:.2f} USD</b>\n"
            f"💳 Method: {method}\n"
            f"📅 Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"🔖 Transaction ID: {secrets.token_hex(8).upper()}\n\n"
            "✨ Thank you for using Protocol Hive: Titan X!"
        )
        
        await update.message.reply_text(proof_msg, parse_mode="HTML")
        await update.message.reply_text(
            "⚠️ <b>Marketing Proof Generated</b>\n"
            "Screenshot this message for marketing purposes.",
            parse_mode="HTML"
        )
        
    except (ValueError, IndexError) as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n"
            "Usage: /fakeproof <username> <amount> <method>"
        )

# --- ADMIN ACTIONS ---
async def admin_action(update, context):
    query = update.callback_query
    data = query.data
    
    if data.startswith("pay_"):
        _, uid, amount = data.split("_")
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance=balance+$1 WHERE telegram_id=$2", float(amount), int(uid))
            await conn.execute("""
                INSERT INTO transactions (user_id, type, amount, status, description)
                VALUES ($1, 'mission_reward', $2, 'completed', 'VIP Mission completed')
            """, int(uid), float(amount))
        await context.bot.send_message(int(uid), f"💰 <b>PAYMENT APPROVED!</b>\nYou received ${float(amount):.2f} USD.", parse_mode="HTML")
        await query.edit_message_caption("✅ PAID")
        
    elif data.startswith("deny_"):
        uid = data.split("_")[1]
        await context.bot.send_message(int(uid), "❌ Your proof was rejected. Doesn't meet requirements.")
        await query.edit_message_caption("❌ REJECTED")

async def admin_activate_royal(update, context):
    """Admin command to manually activate Royal status"""
    user = update.effective_user
    
    if ADMIN_ID and user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    try:
        target_user_id = int(context.args[0])
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_royal=TRUE WHERE telegram_id=$1",
                    target_user_id
                )
        
        await update.message.reply_text(f"✅ Royal status activated for user {target_user_id}")
        await context.bot.send_message(
            target_user_id,
            "👑 <b>ROYAL STATUS ACTIVATED!</b>\n\n"
            "You now have +50% earnings on all income!\n"
            "Enjoy your premium benefits!",
            parse_mode="HTML"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /activateroyal <user_id>")

async def cancel(update, context): 
    await update.message.reply_text("Operation cancelled."); 
    return ConversationHandler.END

async def dashboard_callback(update, context):
    """Handle dashboard callback"""
    await update.callback_query.answer()
    await dashboard(update, context)

# --- SETUP ---
async def init_bot():
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handlers
    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)], 
        states={ASK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_country)]}, 
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    proof_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_proof, pattern="upload_proof")], 
        states={WAITING_PROOF: [MessageHandler(filters.PHOTO, handle_proof)]}, 
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    withdraw_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(withdraw_flash_callback, pattern="withdraw_flash"),
            CallbackQueryHandler(withdraw_standard_callback, pattern="withdraw_standard")
        ],
        states={ASK_WITHDRAWAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdrawal)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add conversation handlers
    telegram_app.add_handler(start_conv)
    telegram_app.add_handler(proof_conv)
    telegram_app.add_handler(withdraw_conv)
    
    # Command handlers
    telegram_app.add_handler(CommandHandler("fakeproof", fakeproof_command))
    telegram_app.add_handler(CommandHandler("activateroyal", admin_activate_royal))
    
    # Callback query handlers
    telegram_app.add_handler(CallbackQueryHandler(dashboard_callback, pattern="^dashboard$"))
    telegram_app.add_handler(CallbackQueryHandler(mining_menu, pattern="^mining_menu$"))
    telegram_app.add_handler(CallbackQueryHandler(buy_miner_callback, pattern="^buy_miner_"))
    telegram_app.add_handler(CallbackQueryHandler(collect_mining_callback, pattern="^collect_mining$"))
    telegram_app.add_handler(CallbackQueryHandler(vip_missions, pattern="^vip_missions$"))
    telegram_app.add_handler(CallbackQueryHandler(start_mission_callback, pattern="^start_mission$"))
    telegram_app.add_handler(CallbackQueryHandler(royal_jelly_menu, pattern="^royal_jelly$"))
    telegram_app.add_handler(CallbackQueryHandler(buy_royal_callback, pattern="^buy_royal$"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw_menu$"))
    telegram_app.add_handler(CallbackQueryHandler(admin_action, pattern="^(pay|deny)_"))
    
    await telegram_app.initialize()
    return telegram_app

# --- FASTAPI ENDPOINTS ---
@app.get("/")
async def root():
    return {
        "app": APP_NAME,
        "status": "running",
        "version": "1.0.0"
    }

@app.post("/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    """Telegram webhook endpoint"""
    if token != TELEGRAM_TOKEN: 
        raise HTTPException(status_code=403, detail="Invalid token")
    
    if not telegram_app:
        raise HTTPException(status_code=500, detail="Bot not initialized")
    
    update = Update.de_json(await request.json(), telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.post("/postback")
async def offertoro_postback(request: Request):
    """
    OfferToro postback endpoint for Iron Gate verification and crediting
    Expected parameters:
    - user_id: Telegram user ID
    - offer_id: OfferToro offer ID
    - payout: Amount to credit
    - secret: Security token
    """
    try:
        # Get query parameters or form data
        if request.method == "GET":
            params = dict(request.query_params)
        else:
            params = await request.form()
            if not params:
                params = await request.json()
        
        # Validate secret
        if params.get("secret") != POSTBACK_SECRET:
            logger.warning(f"Invalid postback secret: {params.get('secret')}")
            return JSONResponse({"status": "error", "message": "Invalid secret"}, status_code=403)
        
        user_id = int(params.get("user_id", 0))
        offer_id = params.get("offer_id", "")
        payout = float(params.get("payout", 0.0))
        ip_address = request.client.host if request.client else "unknown"
        
        if not user_id or payout <= 0:
            return JSONResponse({"status": "error", "message": "Invalid parameters"}, status_code=400)
        
        # Log postback
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO postback_logs (user_id, offer_id, payout, ip_address)
                    VALUES ($1, $2, $3, $4)
                """, user_id, offer_id, payout, ip_address)
        
        # Check if this is Iron Gate verification
        user = await get_user(user_id)
        if user and not user['is_verified']:
            # Iron Gate unlock + reward
            reward = 5.0  # Base Iron Gate reward
            await verify_user(user_id, reward + payout)
            
            # Notify user
            if telegram_app:
                await telegram_app.bot.send_message(
                    user_id,
                    f"🎉 <b>IRON GATE UNLOCKED!</b>\n\n"
                    f"✅ Verification completed!\n"
                    f"💰 Reward: ${reward + payout:.2f} credited!\n\n"
                    "Welcome to Protocol Hive: Titan X!\n"
                    "Use /start to access the dashboard.",
                    parse_mode="HTML"
                )
            
            logger.info(f"Iron Gate unlocked for user {user_id}, credited ${reward + payout:.2f}")
        elif user:
            # Regular offer completion
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE users SET balance=balance+$1 WHERE telegram_id=$2",
                        payout, user_id
                    )
                    await conn.execute("""
                        INSERT INTO transactions (user_id, type, amount, status, description)
                        VALUES ($1, 'offer_completion', $2, 'completed', $3)
                    """, user_id, payout, f"Offer {offer_id} completed")
            
            # Notify user
            if telegram_app:
                await telegram_app.bot.send_message(
                    user_id,
                    f"💰 <b>OFFER COMPLETED!</b>\n\n"
                    f"✅ ${payout:.2f} has been credited to your balance!",
                    parse_mode="HTML"
                )
            
            logger.info(f"Offer completed for user {user_id}, credited ${payout:.2f}")
        
        return JSONResponse({"status": "success", "message": "Postback processed"})
    
    except Exception as e:
        logger.error(f"Postback error: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/postback")
async def offertoro_postback_get(request: Request):
    """Handle GET postbacks from OfferToro"""
    return await offertoro_postback(request)

@app.on_event("startup")
async def startup():
    """Initialize database and bot on startup"""
    logger.info("Starting Protocol Hive: Titan X")
    await init_db()
    global telegram_app
    if not telegram_app:
        telegram_app = await init_bot()
    await telegram_app.start()
    logger.info("Bot started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down Protocol Hive: Titan X")
    if telegram_app:
        await telegram_app.stop()
    if db_pool:
        await db_pool.close()
