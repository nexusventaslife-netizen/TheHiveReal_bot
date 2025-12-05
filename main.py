"""
PROTOCOL HIVE: TITAN X
Complete Telegram bot with Iron Gate verification, Mining System, VIP Missions,
Royal Jelly upsell, Withdrawal system, and Fake Proof generator.
Production-ready, single-file implementation.
"""

import logging
import os
import asyncio
import random
import secrets
from datetime import datetime, timedelta
from typing import Optional
import asyncpg
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# --- CONFIGURATION & SECRETS ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("ProtocolHiveTitanX")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_ID = int(os.environ.get("ADMIN_ID")) if os.environ.get("ADMIN_ID") else None
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "secret_key_12345")
OFFERTORO_LINK = os.environ.get("OFFERTORO_LINK", "https://www.offertoro.com/ifr/show/123456")
ADSTERRA_LINK = os.environ.get("ADSTERRA_LINK", "https://www.adsterra.com/your_link")
CRYPTO_PAYMENT_ADDRESS = os.environ.get("CRYPTO_PAYMENT_ADDRESS", "0xYourWalletAddress")

# --- VIP MISSIONS (CPA OFFERS) ---
VIP_MISSIONS = {
    "TIER_1": {  # USA, UK, DE, CA, AU
        "name": "🏦 Bybit Pro Trader Elite",
        "desc": "Register, verify KYC, and deposit $100 minimum",
        "payout_user": 50.0,
        "link": "https://partner.bybit.com/b/your_tier1_link",
        "type": "CPA"
    },
    "GLOBAL": {  # All other countries
        "name": "🎲 BingX Trading Bonus",
        "desc": "Sign up and make first deposit of $10",
        "payout_user": 10.0,
        "link": "https://bingx.com/invite/your_global_link",
        "type": "CPA"
    }
}

# Mining configuration
MINER_TYPES = {
    "basic": {"name": "⚡ Basic Miner", "cost": 10.0, "income_per_hour": 0.5, "energy_cost": 5},
    "advanced": {"name": "🔥 Advanced Miner", "cost": 50.0, "income_per_hour": 3.0, "energy_cost": 15},
    "elite": {"name": "💎 Elite Miner", "cost": 200.0, "income_per_hour": 15.0, "energy_cost": 50}
}

APP_NAME = "Protocol Hive: Titan X"
app = FastAPI(title=APP_NAME)
telegram_app: Optional[Application] = None
db_pool: Optional[asyncpg.Pool] = None

# Conversation states
ASK_COUNTRY, WAITING_PROOF, WITHDRAW_AMOUNT = range(3)

# --- DATABASE SCHEMA ---
async def init_db():
    """Initialize complete database schema"""
    global db_pool
    if not DATABASE_URL:
        logger.warning("No DATABASE_URL provided, running without database")
        return
    
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        async with db_pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    country_code TEXT,
                    balance DOUBLE PRECISION DEFAULT 0.0,
                    energy INTEGER DEFAULT 100,
                    is_verified BOOLEAN DEFAULT FALSE,
                    is_royal BOOLEAN DEFAULT FALSE,
                    royal_multiplier DOUBLE PRECISION DEFAULT 1.0,
                    last_energy_recharge TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Miners table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS miners (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    miner_type TEXT,
                    purchased_at TIMESTAMP DEFAULT NOW(),
                    last_claim TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Transactions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id),
                    type TEXT,
                    amount DOUBLE PRECISION,
                    fee DOUBLE PRECISION DEFAULT 0.0,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

async def get_user(tg_id):
    """Get user from database"""
    if not db_pool:
        return None
    async with db_pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)
        return dict(r) if r else None

async def create_user(tg_id, first_name, country_code):
    """Create new user"""
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name, country_code, is_verified)
            VALUES ($1, $2, $3, FALSE)
            ON CONFLICT (telegram_id) DO NOTHING
        """, tg_id, first_name, country_code)

async def get_user_miners(user_id):
    """Get all miners owned by user"""
    if not db_pool:
        return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM miners WHERE user_id=$1", user_id)
        return [dict(r) for r in rows]

# --- SMART ROUTING ---
def get_vip_mission(country_code):
    """Route users to appropriate CPA offer based on country"""
    tier_1 = ["US", "GB", "CA", "DE", "AU", "CH", "NL", "SE", "NO", "DK"]
    code = str(country_code).upper()
    
    if code in tier_1:
        return VIP_MISSIONS["TIER_1"]
    else:
        return VIP_MISSIONS["GLOBAL"]

# --- BOT COMMANDS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with Iron Gate verification"""
    user = update.effective_user
    db_user = await get_user(user.id)
    
    if db_user and db_user['is_verified']:
        # User is verified, show dashboard
        await show_dashboard(update, context)
        return ConversationHandler.END
    
    # New user or unverified - show Iron Gate
    await update.message.reply_text(
        f"🚪 <b>IRON GATE VERIFICATION</b>\n\n"
        f"Welcome {user.first_name}! To access <b>Protocol Hive: Titan X</b>, "
        f"you must complete ONE verification task.\n\n"
        f"⚠️ This is required to prevent bots and ensure fair access.\n\n"
        f"🌍 First, what's your country code? (Example: US, GB, ES, MX)",
        parse_mode="HTML"
    )
    return ASK_COUNTRY

async def receive_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country input and show Iron Gate task"""
    country = update.message.text.upper().strip()[:2]
    user = update.effective_user
    
    # Create or update user
    await create_user(user.id, user.first_name, country)
    
    msg = (
        f"🔒 <b>IRON GATE ACTIVATION</b>\n\n"
        f"Country detected: {country}\n\n"
        f"🎯 <b>MANDATORY TASK:</b>\n"
        f"Complete ONE offer on OfferToro to unlock full access.\n\n"
        f"1️⃣ Click the link below\n"
        f"2️⃣ Complete any offer (surveys, apps, etc.)\n"
        f"3️⃣ Wait for automatic verification (1-5 minutes)\n\n"
        f"💰 You'll receive bonus credits upon completion!\n\n"
        f"🔗 <b>Verification Link:</b> {OFFERTORO_LINK}"
    )
    
    kb = [
        [InlineKeyboardButton("🔓 Complete OfferToro Task", url=OFFERTORO_LINK)],
        [InlineKeyboardButton("✅ I Completed It - Check Status", callback_data="check_verification")]
    ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return ConversationHandler.END

async def check_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user passed Iron Gate"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    if db_user and db_user['is_verified']:
        await query.edit_message_text(
            "✅ <b>IRON GATE UNLOCKED!</b>\n\n"
            "Welcome to Protocol Hive: Titan X!\n"
            "Loading your dashboard...",
            parse_mode="HTML"
        )
        await asyncio.sleep(1)
        await show_dashboard(update, context)
    else:
        await query.edit_message_text(
            "⏳ <b>Verification Pending</b>\n\n"
            "We haven't received confirmation yet.\n\n"
            "Please make sure you:\n"
            "1. Completed an offer fully\n"
            "2. Waited 1-5 minutes for processing\n\n"
            "Try checking again in a few minutes.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Check Again", callback_data="check_verification")
            ]]),
            parse_mode="HTML"
        )

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main dashboard for verified users"""
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    if not db_user or not db_user['is_verified']:
        await update.effective_message.reply_text("Please complete Iron Gate verification first. Use /start")
        return
    
    balance = db_user['balance']
    energy = db_user['energy']
    is_royal = db_user['is_royal']
    multiplier = db_user['royal_multiplier']
    
    royal_badge = "👑 ROYAL" if is_royal else ""
    
    msg = (
        f"💎 <b>PROTOCOL HIVE: TITAN X</b> {royal_badge}\n\n"
        f"👤 {db_user['first_name']} | 🌍 {db_user['country_code']}\n"
        f"💰 Balance: <b>${balance:.2f}</b>\n"
        f"⚡ Energy: <b>{energy}/100</b>\n"
    )
    
    if is_royal:
        msg += f"🔥 Royal Multiplier: <b>{multiplier}x</b>\n"
    
    msg += "\n<b>Choose an option:</b>"
    
    kb = [
        [InlineKeyboardButton("⛏️ Mining System", callback_data="mining_menu")],
        [InlineKeyboardButton("🎯 VIP Missions (CPA)", callback_data="vip_missions")],
        [InlineKeyboardButton("👑 Royal Jelly Upgrade", callback_data="royal_jelly")],
        [InlineKeyboardButton("💸 Withdraw Funds", callback_data="withdraw_menu")],
        [InlineKeyboardButton("🔋 Recharge Energy", url=ADSTERRA_LINK)]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.effective_message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def mining_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mining system interface"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    miners = await get_user_miners(user_id)
    
    # Calculate pending income
    total_income = 0.0
    for miner in miners:
        miner_config = MINER_TYPES.get(miner['miner_type'])
        if miner_config and miner['last_claim']:
            hours_since_claim = (datetime.utcnow() - miner['last_claim'].replace(tzinfo=None)).total_seconds() / 3600
            income = hours_since_claim * miner_config['income_per_hour']
            total_income += income
    
    msg = (
        f"⛏️ <b>MINING SYSTEM</b>\n\n"
        f"💰 Your Balance: ${db_user['balance']:.2f}\n"
        f"⚡ Energy: {db_user['energy']}/100\n"
        f"🤖 Active Miners: {len(miners)}\n"
        f"💵 Pending Income: ${total_income:.2f}\n\n"
        f"<b>Available Miners:</b>\n\n"
    )
    
    kb = []
    for miner_id, miner_info in MINER_TYPES.items():
        msg += (
            f"{miner_info['name']}\n"
            f"  💰 Cost: ${miner_info['cost']} (burns balance)\n"
            f"  📈 Income: ${miner_info['income_per_hour']}/hour\n"
            f"  ⚡ Energy: {miner_info['energy_cost']}/day\n\n"
        )
        kb.append([InlineKeyboardButton(
            f"Buy {miner_info['name']}",
            callback_data=f"buy_miner_{miner_id}"
        )])
    
    kb.append([InlineKeyboardButton("💎 Claim Mining Income", callback_data="claim_mining")])
    kb.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")])
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def buy_miner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle miner purchase"""
    query = update.callback_query
    await query.answer()
    
    miner_type = query.data.replace("buy_miner_", "")
    miner_config = MINER_TYPES.get(miner_type)
    
    if not miner_config:
        await query.answer("Invalid miner type", show_alert=True)
        return
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    # Use transaction to prevent race conditions
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Re-check balance within transaction
            current_balance = await conn.fetchval(
                "SELECT balance FROM users WHERE telegram_id = $1 FOR UPDATE",
                user_id
            )
            
            if current_balance < miner_config['cost']:
                await query.answer(
                    f"❌ Insufficient balance! Need ${miner_config['cost']:.2f}",
                    show_alert=True
                )
                return
            
            # Deduct balance and add miner atomically
            await conn.execute(
                "UPDATE users SET balance = balance - $1 WHERE telegram_id = $2",
                miner_config['cost'], user_id
            )
            await conn.execute(
                "INSERT INTO miners (user_id, miner_type) VALUES ($1, $2)",
                user_id, miner_type
            )
            await conn.execute(
                "INSERT INTO transactions (user_id, type, amount, status) VALUES ($1, $2, $3, $4)",
                user_id, "miner_purchase", miner_config['cost'], "completed"
            )
    
    await query.answer(f"✅ {miner_config['name']} purchased!", show_alert=True)
    await mining_menu(update, context)

async def claim_mining(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim mining income"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    miners = await get_user_miners(user_id)
    
    total_income = 0.0
    for miner in miners:
        miner_config = MINER_TYPES.get(miner['miner_type'])
        if miner_config and miner['last_claim']:
            hours_since_claim = (datetime.utcnow() - miner['last_claim'].replace(tzinfo=None)).total_seconds() / 3600
            income = hours_since_claim * miner_config['income_per_hour']
            total_income += income
    
    if total_income <= 0:
        await query.answer("No income to claim yet!", show_alert=True)
        return
    
    # Apply royal multiplier if applicable
    if db_user['is_royal']:
        total_income *= db_user['royal_multiplier']
    
    # Update balance and reset claim times
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance = balance + $1 WHERE telegram_id = $2",
            total_income, user_id
        )
        await conn.execute(
            "UPDATE miners SET last_claim = NOW() WHERE user_id = $1",
            user_id
        )
        await conn.execute(
            "INSERT INTO transactions (user_id, type, amount, status) VALUES ($1, $2, $3, $4)",
            user_id, "mining_claim", total_income, "completed"
        )
    
    await query.answer(f"✅ Claimed ${total_income:.2f}!", show_alert=True)
    await mining_menu(update, context)

async def vip_missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show VIP CPA missions"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    mission = get_vip_mission(db_user['country_code'])
    
    msg = (
        f"🎯 <b>VIP MISSIONS (High-Paying CPA)</b>\n\n"
        f"Your Region: {db_user['country_code']}\n\n"
        f"<b>🔥 FEATURED OFFER:</b>\n\n"
        f"{mission['name']}\n"
        f"📋 {mission['desc']}\n"
        f"💰 <b>Your Reward: ${mission['payout_user']:.2f}</b>\n\n"
        f"<b>Instructions:</b>\n"
        f"1. Click the mission link below\n"
        f"2. Complete the requirements fully\n"
        f"3. Take a clear screenshot as proof\n"
        f"4. Submit for manual verification\n\n"
        f"⏱️ Average approval time: 2-12 hours"
    )
    
    kb = [
        [InlineKeyboardButton("🚀 Start Mission", url=mission['link'])],
        [InlineKeyboardButton("📤 Submit Proof", callback_data="submit_mission_proof")],
        [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def royal_jelly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Royal Jelly upsell"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    if db_user['is_royal']:
        msg = (
            f"👑 <b>YOU ARE ROYAL!</b>\n\n"
            f"Current multiplier: <b>{db_user['royal_multiplier']}x</b>\n\n"
            f"All mining income is boosted by {db_user['royal_multiplier']}x!\n"
            f"Royal status is permanent. 🎉"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="dashboard")]]
    else:
        msg = (
            f"👑 <b>ROYAL JELLY UPGRADE</b>\n\n"
            f"Unlock <b>ROYAL STATUS</b> for life!\n\n"
            f"<b>Benefits:</b>\n"
            f"• 🔥 1.5x multiplier on all mining income\n"
            f"• 👑 Royal badge on your profile\n"
            f"• 🎯 Priority support\n"
            f"• ⚡ Bonus energy recharge rate\n\n"
            f"<b>One-time payment: $1.00 USD</b>\n\n"
            f"💳 Payment Methods:\n"
            f"• Bitcoin (BTC)\n"
            f"• Ethereum (ETH)\n"
            f"• USDT (TRC20)\n\n"
            f"Send exactly $1.00 to:\n"
            f"<code>{CRYPTO_PAYMENT_ADDRESS}</code>\n\n"
            f"After payment, send transaction hash to admin."
        )
        kb = [
            [InlineKeyboardButton("💳 I Paid - Activate Royal", callback_data="activate_royal")],
            [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
        ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def activate_royal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate royal status (manual verification)"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📨 Please send your transaction hash to the admin for verification.\n\n"
        "Once verified, your Royal status will be activated immediately!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="dashboard")
        ]])
    )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal options"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    msg = (
        f"💸 <b>WITHDRAWAL SYSTEM</b>\n\n"
        f"Available Balance: <b>${db_user['balance']:.2f}</b>\n\n"
        f"<b>Choose Withdrawal Type:</b>\n\n"
        f"⚡ <b>FLASH Withdrawal</b>\n"
        f"  • Instant processing (1-24 hours)\n"
        f"  • 20% service fee\n"
        f"  • Minimum: $10.00\n\n"
        f"📦 <b>STANDARD Withdrawal</b>\n"
        f"  • Regular processing (3-7 days)\n"
        f"  • No fees (0%)\n"
        f"  • Minimum: $20.00\n\n"
        f"Select your preferred method:"
    )
    
    kb = [
        [InlineKeyboardButton("⚡ Flash (20% fee)", callback_data="withdraw_flash")],
        [InlineKeyboardButton("📦 Standard (No fee)", callback_data="withdraw_standard")],
        [InlineKeyboardButton("🔙 Back", callback_data="dashboard")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def withdraw_flash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle flash withdrawal"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    if db_user['balance'] < 10.0:
        await query.answer("❌ Minimum $10 required for Flash withdrawal!", show_alert=True)
        return
    
    amount = db_user['balance']
    fee = amount * 0.20
    net_amount = amount - fee
    
    msg = (
        f"⚡ <b>FLASH WITHDRAWAL</b>\n\n"
        f"Gross Amount: ${amount:.2f}\n"
        f"Fee (20%): -${fee:.2f}\n"
        f"<b>Net Amount: ${net_amount:.2f}</b>\n\n"
        f"Processing time: 1-24 hours\n\n"
        f"Confirm withdrawal?"
    )
    
    kb = [
        [InlineKeyboardButton("✅ Confirm Flash Withdrawal", callback_data="confirm_flash")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="withdraw_menu")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def withdraw_standard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle standard withdrawal"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    if db_user['balance'] < 20.0:
        await query.answer("❌ Minimum $20 required for Standard withdrawal!", show_alert=True)
        return
    
    amount = db_user['balance']
    
    msg = (
        f"📦 <b>STANDARD WITHDRAWAL</b>\n\n"
        f"Amount: ${amount:.2f}\n"
        f"Fee: $0.00 (No fee!)\n"
        f"<b>Net Amount: ${amount:.2f}</b>\n\n"
        f"Processing time: 3-7 days\n\n"
        f"Confirm withdrawal?"
    )
    
    kb = [
        [InlineKeyboardButton("✅ Confirm Standard Withdrawal", callback_data="confirm_standard")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="withdraw_menu")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdrawal confirmation"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    
    is_flash = query.data == "confirm_flash"
    amount = db_user['balance']
    fee = amount * 0.20 if is_flash else 0.0
    net_amount = amount - fee
    
    # Record transaction
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance = 0.0 WHERE telegram_id = $1",
            user_id
        )
        await conn.execute(
            "INSERT INTO transactions (user_id, type, amount, fee, status) VALUES ($1, $2, $3, $4, $5)",
            user_id, "withdrawal_flash" if is_flash else "withdrawal_standard", 
            net_amount, fee, "pending"
        )
    
    withdrawal_type = "Flash" if is_flash else "Standard"
    
    await query.edit_message_text(
        f"✅ <b>WITHDRAWAL SUBMITTED</b>\n\n"
        f"Type: {withdrawal_type}\n"
        f"Amount: ${net_amount:.2f}\n"
        f"Status: Pending\n\n"
        f"You will receive payment details via message soon!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")
        ]]),
        parse_mode="HTML"
    )
    
    # Notify admin
    if ADMIN_ID:
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
            f"User: {db_user['first_name']} ({user_id})\n"
            f"Type: {withdrawal_type}\n"
            f"Amount: ${net_amount:.2f}\n"
            f"Fee: ${fee:.2f}",
            parse_mode="HTML"
        )

async def fakeproof_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to generate fake proof for marketing"""
    user_id = update.effective_user.id
    
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized. Admin only.")
        return
    
    # Parse arguments
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /fakeproof <name> <amount>\n"
            "Example: /fakeproof John 150.00"
        )
        return
    
    name = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Use numbers only.")
        return
    
    # Generate realistic fake proof with secure random
    fake_tx_id = secrets.token_hex(32)  # 64 characters
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    msg = (
        f"✅ <b>PAYMENT SUCCESSFUL</b>\n\n"
        f"Recipient: {name}\n"
        f"Amount: <b>${amount:.2f} USD</b>\n"
        f"Method: Bitcoin (BTC)\n"
        f"Status: Confirmed ✓\n\n"
        f"Transaction ID:\n"
        f"<code>{fake_tx_id}</code>\n\n"
        f"Processed: {timestamp}\n"
        f"Network: Bitcoin Mainnet\n"
        f"Confirmations: 3/3 ✓\n\n"
        f"<i>Protocol Hive: Titan X</i>"
    )
    
    await update.message.reply_text(msg, parse_mode="HTML")

# --- WEBHOOK HANDLERS ---

@app.post("/postback")
async def offertoro_postback(request: Request):
    """Handle OfferToro postback for Iron Gate verification"""
    try:
        params = dict(request.query_params)
        
        # Verify secret
        if params.get("secret") != POSTBACK_SECRET:
            logger.warning("Invalid postback secret")
            return JSONResponse({"status": "error", "message": "Invalid secret"}, status_code=403)
        
        user_id = params.get("user_id")
        payout = float(params.get("payout", 0))
        
        if not user_id:
            return JSONResponse({"status": "error", "message": "Missing user_id"}, status_code=400)
        
        user_id = int(user_id)
        
        # Unlock Iron Gate and credit bonus
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_verified = TRUE, balance = balance + $1 WHERE telegram_id = $2",
                    payout, user_id
                )
                await conn.execute(
                    "INSERT INTO transactions (user_id, type, amount, status) VALUES ($1, $2, $3, $4)",
                    user_id, "offertoro_completion", payout, "completed"
                )
        
        # Notify user
        if telegram_app:
            await telegram_app.bot.send_message(
                user_id,
                f"🎉 <b>IRON GATE UNLOCKED!</b>\n\n"
                f"✅ Verification complete\n"
                f"💰 Bonus credited: ${payout:.2f}\n\n"
                f"You now have full access to Protocol Hive: Titan X!\n"
                f"Use /start to access your dashboard.",
                parse_mode="HTML"
            )
        
        logger.info(f"OfferToro postback processed for user {user_id}, amount: ${payout}")
        return JSONResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Postback error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    """Handle Telegram webhook updates"""
    if token != TELEGRAM_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": APP_NAME}

# --- BOT INITIALIZATION ---

async def init_telegram_app():
    """Initialize Telegram application"""
    global telegram_app
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handler for new users
    start_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_country)]
        },
        fallbacks=[CommandHandler("start", start_command)]
    )
    
    # Command handlers
    telegram_app.add_handler(start_conv)
    telegram_app.add_handler(CommandHandler("fakeproof", fakeproof_command))
    
    # Callback query handlers
    telegram_app.add_handler(CallbackQueryHandler(check_verification, pattern="^check_verification$"))
    telegram_app.add_handler(CallbackQueryHandler(show_dashboard, pattern="^dashboard$"))
    telegram_app.add_handler(CallbackQueryHandler(mining_menu, pattern="^mining_menu$"))
    telegram_app.add_handler(CallbackQueryHandler(buy_miner, pattern="^buy_miner_"))
    telegram_app.add_handler(CallbackQueryHandler(claim_mining, pattern="^claim_mining$"))
    telegram_app.add_handler(CallbackQueryHandler(vip_missions, pattern="^vip_missions$"))
    telegram_app.add_handler(CallbackQueryHandler(royal_jelly, pattern="^royal_jelly$"))
    telegram_app.add_handler(CallbackQueryHandler(activate_royal, pattern="^activate_royal$"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw_menu$"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_flash, pattern="^withdraw_flash$"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_standard, pattern="^withdraw_standard$"))
    telegram_app.add_handler(CallbackQueryHandler(confirm_withdrawal, pattern="^confirm_(flash|standard)$"))
    
    await telegram_app.initialize()
    await telegram_app.start()
    
    logger.info("Telegram bot initialized successfully")
    return telegram_app

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"Starting {APP_NAME}...")
    
    # Validate required environment variables
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required")
    if not ADMIN_ID:
        logger.warning("ADMIN_ID not set - admin features will be disabled")
    
    await init_db()
    await init_telegram_app()
    logger.info(f"{APP_NAME} started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down...")
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    if db_pool:
        await db_pool.close()
    logger.info("Shutdown complete")

# --- MAIN ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
