# Quick Start Guide - Protocol Hive: Titan X

Get your Telegram bot up and running in 5 minutes!

## Prerequisites Checklist

Before starting, make sure you have:

- [ ] Python 3.11 or higher installed
- [ ] PostgreSQL database (local or cloud)
- [ ] Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- [ ] Your Telegram User ID (get from [@userinfobot](https://t.me/userinfobot))
- [ ] OfferToro account and app ID (optional but recommended)
- [ ] Adsterra monetization link (optional)

## Step 1: Get Your Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Follow the prompts to choose a name and username
4. Save the token that BotFather gives you (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

## Step 2: Get Your Telegram User ID

1. Open Telegram and search for [@userinfobot](https://t.me/userinfobot)
2. Start the bot
3. It will send you your user ID (a number like `123456789`)
4. Save this number - you'll use it as ADMIN_ID

## Step 3: Set Up PostgreSQL

### Option A: Local PostgreSQL (Development)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql  # macOS

# Start PostgreSQL
sudo systemctl start postgresql  # Ubuntu/Debian
brew services start postgresql  # macOS

# Create database
sudo -u postgres psql -c "CREATE DATABASE hive;"

# Your DATABASE_URL will be:
# postgresql://postgres:@localhost/hive
```

### Option B: Cloud PostgreSQL (Production)

**Free Options**:
- [ElephantSQL](https://www.elephantsql.com/) - Free tier: 20MB
- [Supabase](https://supabase.com/) - Free tier: 500MB
- [Railway](https://railway.app/) - $5/month credits free

After creating a database, you'll get a DATABASE_URL like:
```
postgresql://user:password@host:5432/database
```

## Step 4: Clone and Configure

```bash
# Clone repository
git clone https://github.com/nexusventaslife-netizen/TheHiveReal_bot.git
cd TheHiveReal_bot

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env with your values
nano .env  # or use any text editor
```

Edit `.env` and set these **REQUIRED** values:
```bash
TELEGRAM_TOKEN=your_bot_token_from_botfather
DATABASE_URL=your_postgresql_connection_string
ADMIN_ID=your_telegram_user_id
```

Optional but recommended:
```bash
POSTBACK_SECRET=choose_a_random_secret_key
OFFERTORO_LINK=https://www.offertoro.com/ifr/show/YOUR_APP_ID
ADSTERRA_LINK=https://www.adsterra.com/your_link
CRYPTO_PAYMENT_ADDRESS=your_crypto_wallet_address
```

## Step 5: Run the Bot

```bash
# Load environment variables and run
export $(cat .env | xargs)
python main.py
```

Or run directly:
```bash
# Set variables in terminal
export TELEGRAM_TOKEN="your_token_here"
export DATABASE_URL="your_database_url"
export ADMIN_ID="your_user_id"

# Run bot
python main.py
```

You should see:
```
INFO - Starting Protocol Hive: Titan X...
INFO - Database initialized successfully
INFO - Telegram bot initialized successfully
INFO - Protocol Hive: Titan X started successfully!
```

## Step 6: Test Your Bot

1. Open Telegram and search for your bot (by username)
2. Send `/start`
3. You should see the Iron Gate verification message
4. Enter a country code (e.g., `US`)
5. You'll see the dashboard (since Iron Gate validation requires OfferToro setup)

## Step 7: Access Admin Features

As admin, you can:

### Generate Fake Proof
```
/fakeproof TestUser 100.00
```

You should receive a realistic-looking payment proof message.

### Manually Verify Users (if needed)

If you want to bypass Iron Gate for testing:

```bash
# Connect to your database
psql $DATABASE_URL

# Verify a user
UPDATE users SET is_verified = TRUE WHERE telegram_id = YOUR_USER_ID;

# Give them balance to test mining
UPDATE users SET balance = 100.0 WHERE telegram_id = YOUR_USER_ID;
```

## Step 8: Set Up Webhooks (Production)

For production deployment, you need to set up webhooks:

### Set Telegram Webhook
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/telegram/<YOUR_TOKEN>"
```

### Configure OfferToro Postback
In your OfferToro dashboard:
1. Go to Settings → Postback URL
2. Set to: `https://your-domain.com/postback?user_id={user_id}&payout={payout}&secret=YOUR_SECRET`
3. Replace `YOUR_SECRET` with your POSTBACK_SECRET

## Troubleshooting

### Bot not responding
```bash
# Check if bot is running
ps aux | grep python

# Check logs
journalctl -u hive-bot -f  # if using systemd

# Test database connection
psql $DATABASE_URL -c "SELECT 1;"
```

### "TELEGRAM_TOKEN environment variable is required"
Make sure you've set the environment variable:
```bash
export TELEGRAM_TOKEN="your_token_here"
```

Or add it to `.env` file.

### Database connection errors
Check your DATABASE_URL format:
```
postgresql://user:password@host:port/database
```

Test connection:
```bash
psql $DATABASE_URL -c "\dt"
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

## Next Steps

Once your bot is running:

1. **Set up OfferToro**: Create account, get app ID, configure postback
2. **Set up Adsterra**: Create account, get monetization link
3. **Configure VIP Missions**: Edit mission links in main.py
4. **Customize miners**: Adjust costs and income in main.py
5. **Deploy to production**: See DEPLOYMENT.md for options
6. **Monitor performance**: Check health endpoint at `/health`

## Production Deployment

For production, you have several options:

- **Heroku**: Easiest, includes free PostgreSQL
- **Railway**: Modern, easy deployment
- **VPS**: Full control, requires more setup
- **Docker**: Containerized deployment

See `DEPLOYMENT.md` for detailed instructions for each option.

## Testing Features

### Test Mining System
1. Manually add balance (via database)
2. Buy a Basic Miner ($10)
3. Wait a few seconds
4. Claim mining income
5. Verify balance increased

### Test VIP Missions
1. Click "VIP Missions"
2. Verify correct mission shown for your country
3. Submit a test screenshot
4. Check admin receives notification

### Test Withdrawals
1. Ensure you have balance ($10+ for Flash, $20+ for Standard)
2. Click "Withdraw Funds"
3. Choose withdrawal type
4. Confirm
5. Verify balance reset and admin notified

### Test Royal Jelly
1. Click "Royal Jelly Upgrade"
2. Note the benefits and payment address
3. Manually activate via database to test:
   ```sql
   UPDATE users SET is_royal = TRUE, royal_multiplier = 1.5 WHERE telegram_id = YOUR_ID;
   ```
4. Verify 1.5x multiplier applies to mining claims

## Support

- **GitHub Issues**: Report bugs or request features
- **Documentation**: See README.md for full documentation
- **Deployment**: See DEPLOYMENT.md for production setup
- **Features**: See FEATURES.md for detailed feature documentation

## Security Reminders

- ✅ Never commit `.env` file to git (it's in .gitignore)
- ✅ Keep TELEGRAM_TOKEN secret
- ✅ Use strong POSTBACK_SECRET
- ✅ Regular database backups
- ✅ Use HTTPS in production
- ✅ Keep dependencies updated

## Development Tips

### Auto-reload during development
```bash
pip install watchdog
watchmedo auto-restart -p "*.py" -- python main.py
```

### View database contents
```bash
psql $DATABASE_URL

# List all users
SELECT * FROM users;

# List all miners
SELECT * FROM miners;

# List all transactions
SELECT * FROM transactions ORDER BY created_at DESC LIMIT 10;
```

### Test webhook locally with ngrok
```bash
# Install ngrok
npm install -g ngrok

# Start ngrok
ngrok http 8000

# Use the https URL for webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-ngrok-url.ngrok.io/telegram/<TOKEN>"
```

## Congratulations! 🎉

Your Protocol Hive: Titan X bot is now running!

For more information, see:
- `README.md` - Complete documentation
- `DEPLOYMENT.md` - Production deployment guides
- `FEATURES.md` - Detailed feature overview
