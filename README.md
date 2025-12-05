# Protocol Hive: Titan X

A complete, production-ready Telegram bot featuring Iron Gate verification, gamified mining system, VIP missions, Royal Jelly upgrades, and a sophisticated withdrawal system.

## 🌟 Features

### 1. **Iron Gate Verification**
- Forces new users to complete an OfferToro task before accessing the bot
- Automatic verification via webhook postback
- Bonus credits awarded upon completion
- Prevents bots and ensures quality users

### 2. **Gamified Mining System**
- Three miner types: Basic, Advanced, and Elite
- Miners generate passive income over time
- Energy system requiring Adsterra link visits for recharges
- Balance burning mechanism (miners cost balance to purchase)
- Claimable income with Royal multiplier bonuses

### 3. **VIP Missions (CPA)**
- Smart routing based on user country
- **Tier 1** (US, GB, CA, DE, AU, etc.): High-value Bybit missions ($50 payout)
- **Global** (All others): BingX missions ($10 payout)
- Manual proof submission and verification system

### 4. **Royal Jelly Upsell**
- One-time $1 USD crypto payment
- Grants permanent Royal status
- 1.5x multiplier on all mining income
- Royal badge display
- Priority support

### 5. **Withdrawal System**
- **Flash Withdrawal**: Instant processing (1-24 hours) with 20% fee, minimum $10
- **Standard Withdrawal**: Regular processing (3-7 days) with 0% fee, minimum $20
- Automated transaction recording

### 6. **Fake Proof Generator**
- Admin-only `/fakeproof` command
- Generates realistic payment success messages for marketing
- Includes fake transaction IDs, timestamps, and confirmations

### 7. **Complete Database Schema**
- **Users table**: Stores user data, balance, energy, verification status, Royal status
- **Miners table**: Tracks purchased miners and claim times
- **Transactions table**: Records all financial activities

### 8. **Webhook Integration**
- `/postback` endpoint for OfferToro callbacks
- Automatic user verification and balance crediting
- `/telegram/{token}` endpoint for Telegram updates
- `/health` endpoint for monitoring

## 📋 Requirements

- Python 3.11+
- PostgreSQL database
- Telegram Bot Token
- OfferToro account (for Iron Gate)
- Adsterra link (for energy recharge)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nexusventaslife-netizen/TheHiveReal_bot.git
   cd TheHiveReal_bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export TELEGRAM_TOKEN="your_bot_token_here"
   export DATABASE_URL="postgresql://user:pass@localhost/hive"
   export ADMIN_ID="your_telegram_user_id"
   export POSTBACK_SECRET="your_secret_key"
   export OFFERTORO_LINK="https://www.offertoro.com/ifr/show/YOUR_ID"
   export ADSTERRA_LINK="https://www.adsterra.com/your_link"
   export CRYPTO_PAYMENT_ADDRESS="0xYourWalletAddress"
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## 🗄️ Database Setup

The bot automatically creates the required tables on first run. The schema includes:

### Users Table
```sql
CREATE TABLE users (
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
```

### Miners Table
```sql
CREATE TABLE miners (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    miner_type TEXT,
    purchased_at TIMESTAMP DEFAULT NOW(),
    last_claim TIMESTAMP DEFAULT NOW()
)
```

### Transactions Table
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    type TEXT,
    amount DOUBLE PRECISION,
    fee DOUBLE PRECISION DEFAULT 0.0,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_TOKEN` | Your Telegram Bot API token | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `ADMIN_ID` | Telegram user ID of admin | Yes | - |
| `POSTBACK_SECRET` | Secret key for OfferToro postbacks | Yes | `secret_key_12345` |
| `OFFERTORO_LINK` | Your OfferToro offer wall link | No | Example link |
| `ADSTERRA_LINK` | Your Adsterra monetization link | No | Example link |
| `CRYPTO_PAYMENT_ADDRESS` | Wallet address for Royal payments | No | Example address |

### Miner Configuration

Edit `MINER_TYPES` in `main.py` to customize miners:

```python
MINER_TYPES = {
    "basic": {
        "name": "⚡ Basic Miner",
        "cost": 10.0,              # Cost in USD
        "income_per_hour": 0.5,    # Earnings per hour
        "energy_cost": 5           # Energy consumed per day
    },
    # Add more miner types...
}
```

### VIP Mission Configuration

Edit `VIP_MISSIONS` in `main.py` to customize offers:

```python
VIP_MISSIONS = {
    "TIER_1": {
        "name": "🏦 Your Offer Name",
        "desc": "Description of requirements",
        "payout_user": 50.0,       # User reward
        "link": "https://...",     # Offer link
        "type": "CPA"
    },
    # Add more tiers...
}
```

## 🔌 Webhook Setup

### OfferToro Postback URL

Configure your OfferToro postback URL:
```
https://yourdomain.com/postback?user_id={user_id}&payout={payout}&secret=YOUR_SECRET
```

Replace:
- `yourdomain.com` with your domain
- `YOUR_SECRET` with your `POSTBACK_SECRET`
- `{user_id}` and `{payout}` are OfferToro macros (keep as-is)

### Telegram Webhook

Set your Telegram webhook:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://yourdomain.com/telegram/<YOUR_BOT_TOKEN>"
```

## 🎮 Bot Commands

### User Commands
- `/start` - Start the bot and show Iron Gate verification

### Admin Commands
- `/fakeproof <name> <amount>` - Generate fake payment proof for marketing
  - Example: `/fakeproof John 150.00`

## 📱 User Flow

1. **New User**
   - User starts bot with `/start`
   - Enters country code
   - Sees Iron Gate verification requirement
   - Completes OfferToro task
   - Gets verified automatically via webhook
   - Receives bonus balance

2. **Dashboard Access**
   - View balance and energy
   - Access mining system
   - Browse VIP missions
   - Purchase Royal Jelly upgrade
   - Request withdrawals

3. **Mining**
   - Purchase miners (burns balance)
   - Miners generate passive income
   - Claim income periodically
   - Recharge energy via Adsterra links

4. **Withdrawal**
   - Choose Flash (20% fee, fast) or Standard (0% fee, slow)
   - Submit withdrawal request
   - Admin processes payment

## 🛡️ Security Features

- Iron Gate prevents bot abuse
- Postback secret validation
- Admin-only sensitive commands
- Transaction logging
- Balance burning for miners (prevents exploitation)

## 📊 Monitoring

### Health Check
```bash
curl https://yourdomain.com/health
```

Response:
```json
{
  "status": "healthy",
  "app": "Protocol Hive: Titan X"
}
```

## 🐛 Troubleshooting

### Bot not responding
- Check if webhook is set correctly
- Verify `TELEGRAM_TOKEN` is correct
- Check logs for errors

### Database connection issues
- Verify `DATABASE_URL` format
- Ensure PostgreSQL is running
- Check database credentials

### Postback not working
- Verify `POSTBACK_SECRET` matches OfferToro configuration
- Check webhook URL is accessible
- Review server logs for errors

## 📝 License

This project is provided as-is for commercial use.

## 🤝 Support

For support, contact the repository owner or open an issue on GitHub.

## ⚠️ Disclaimer

This bot is designed for legitimate business purposes. Ensure compliance with:
- Telegram Terms of Service
- OfferToro Terms of Service
- Adsterra Terms of Service
- Local regulations regarding online monetization

The "fake proof" feature is intended solely for marketing materials and screenshots. Always operate transparently with users regarding payment terms and timelines.
