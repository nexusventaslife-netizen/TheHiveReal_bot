# Protocol Hive: Titan X - Feature Overview

## 🎯 Core Features

### 1. Iron Gate Verification System
**Purpose**: Prevent bot abuse and ensure quality users

**How it works**:
- New users must complete an OfferToro task to unlock the bot
- Users enter their country code on first start
- System displays OfferToro verification link
- Webhook automatically verifies completion and credits bonus
- Only verified users can access main features

**User Flow**:
```
/start → Enter Country → See Iron Gate → Complete OfferToro → Auto Unlock → Dashboard
```

**Technical Implementation**:
- Database field: `is_verified` (boolean)
- Webhook endpoint: `/postback`
- Automatic verification via OfferToro postback
- Bonus balance credited upon verification

### 2. Gamified Mining System
**Purpose**: Create engaging passive income mechanism

**Miner Types**:
| Miner | Cost | Income/Hour | Energy Cost/Day |
|-------|------|-------------|-----------------|
| ⚡ Basic | $10 | $0.50 | 5 |
| 🔥 Advanced | $50 | $3.00 | 15 |
| 💎 Elite | $200 | $15.00 | 50 |

**Key Mechanics**:
- **Balance Burning**: Purchasing miners consumes balance (anti-exploitation)
- **Passive Income**: Miners generate income over time (claimable)
- **Energy System**: Limited energy requires Adsterra link visits to recharge
- **Royal Multiplier**: Royal users get 1.5x income boost
- **Atomic Transactions**: Prevents race conditions in purchases

**User Flow**:
```
Dashboard → Mining Menu → Buy Miner → Income Accumulates → Claim Income → Repeat
```

**Technical Implementation**:
- Database tables: `miners`, `transactions`
- Time-based income calculation
- Database transaction locks for purchases
- Timestamp tracking for claims

### 3. VIP Missions (CPA Offers)
**Purpose**: High-paying conversion opportunities

**Smart Routing**:
- **Tier 1 Countries** (US, GB, CA, DE, AU, CH, NL, SE, NO, DK):
  - Offer: Bybit Pro Trader Elite
  - Payout: $50.00
  - Requirements: Register, KYC, deposit $100

- **Global Countries** (All others):
  - Offer: BingX Trading Bonus
  - Payout: $10.00
  - Requirements: Sign up, deposit $10

**User Flow**:
```
Dashboard → VIP Missions → Start Mission → Complete Requirements → Submit Proof → Manual Verification → Payout
```

**Technical Implementation**:
- Country-based routing algorithm
- Manual admin verification system
- Photo submission support
- Admin approval/rejection interface

### 4. Royal Jelly Upgrade
**Purpose**: Monetization through premium features

**Benefits**:
- 👑 Permanent Royal status badge
- 🔥 1.5x multiplier on all mining income
- 🎯 Priority support
- ⚡ Enhanced energy recharge rate

**Pricing**: $1.00 USD (one-time payment)

**Payment Methods**:
- Bitcoin (BTC)
- Ethereum (ETH)
- USDT (TRC20)

**User Flow**:
```
Dashboard → Royal Jelly → See Benefits → Send Payment → Contact Admin → Manual Activation
```

**Technical Implementation**:
- Database fields: `is_royal`, `royal_multiplier`
- Manual verification by admin
- Permanent status (no expiration)
- Applied to all mining claims

### 5. Withdrawal System
**Purpose**: Dual-tier withdrawal with trade-offs

**Flash Withdrawal**:
- ⚡ Processing: 1-24 hours
- 💰 Fee: 20%
- 📊 Minimum: $10.00
- 🎯 Use case: Users who need money fast

**Standard Withdrawal**:
- 📦 Processing: 3-7 days
- 💰 Fee: 0% (FREE)
- 📊 Minimum: $20.00
- 🎯 Use case: Users who can wait for better value

**User Flow**:
```
Dashboard → Withdraw → Choose Type → Review Fees → Confirm → Admin Process → Payment Sent
```

**Technical Implementation**:
- Database transaction recording
- Fee calculation logic
- Balance zeroing on submission
- Admin notification system
- Status tracking: pending, completed, failed

### 6. Fake Proof Generator
**Purpose**: Marketing and social proof generation

**Command**: `/fakeproof <name> <amount>`

**Example**: `/fakeproof John 150.00`

**Generated Output**:
```
✅ PAYMENT SUCCESSFUL

Recipient: John
Amount: $150.00 USD
Method: Bitcoin (BTC)
Status: Confirmed ✓

Transaction ID:
a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5...

Processed: 2025-12-05 18:00:00 UTC
Network: Bitcoin Mainnet
Confirmations: 3/3 ✓

Protocol Hive: Titan X
```

**Security**:
- ✅ Admin-only access
- ✅ Cryptographically secure transaction IDs (using `secrets` module)
- ✅ Realistic formatting
- ⚠️ For marketing/promotional use only

**Technical Implementation**:
- User ID verification against ADMIN_ID
- Secure random generation with `secrets.token_hex()`
- Formatted HTML output
- Instant generation

### 7. Database Schema
**Complete three-table design**

**users table**:
```sql
- telegram_id (PRIMARY KEY)
- first_name
- country_code
- balance (default: 0.0)
- energy (default: 100)
- is_verified (default: FALSE)
- is_royal (default: FALSE)
- royal_multiplier (default: 1.0)
- last_energy_recharge
- created_at
```

**miners table**:
```sql
- id (PRIMARY KEY)
- user_id (FOREIGN KEY → users.telegram_id)
- miner_type (basic/advanced/elite)
- purchased_at
- last_claim (default: NOW())
```

**transactions table**:
```sql
- id (PRIMARY KEY)
- user_id (FOREIGN KEY → users.telegram_id)
- type (miner_purchase/mining_claim/withdrawal_flash/withdrawal_standard/offertoro_completion)
- amount
- fee (default: 0.0)
- status (pending/completed/failed)
- created_at
```

### 8. Webhook Integration

**OfferToro Postback** (`/postback`):
- Receives: `user_id`, `payout`, `secret`
- Validates: Postback secret
- Actions:
  - Sets `is_verified = TRUE`
  - Credits balance with payout
  - Records transaction
  - Sends notification to user

**Telegram Webhook** (`/telegram/{token}`):
- Receives: Telegram updates
- Validates: Token match
- Actions:
  - Processes all bot commands
  - Handles callbacks
  - Updates database

**Health Check** (`/health`):
- Returns: JSON status
- Use: Monitoring and uptime checks

## 🔐 Security Features

1. **Secret Validation**: Postback secret prevents unauthorized access
2. **Transaction Locks**: Database-level locks prevent race conditions
3. **Admin Verification**: Sensitive commands require admin ID match
4. **Secure Randoms**: Uses `secrets` module for crypto-secure generation
5. **Input Validation**: All user inputs are validated and sanitized
6. **Environment Variables**: No hardcoded credentials
7. **Null Handling**: Proper handling of NULL database values

## 📊 Data Flow

### New User Journey
```
1. User sends /start
2. Bot checks if user exists and is verified
3. If not verified → Show Iron Gate
4. User completes OfferToro task
5. Webhook receives postback
6. User unlocked and credited
7. User accesses dashboard
8. User can now use all features
```

### Mining Income Flow
```
1. User buys miner (balance burned)
2. Miner record created with timestamp
3. Time passes (passive)
4. User clicks "Claim Income"
5. System calculates hours since last claim
6. Income = hours × income_per_hour
7. If royal: income *= 1.5
8. Balance credited
9. last_claim updated to NOW()
```

### Withdrawal Flow
```
1. User clicks "Withdraw"
2. Chooses Flash or Standard
3. System shows fees and net amount
4. User confirms
5. Balance set to 0
6. Transaction recorded
7. Admin notified
8. Admin processes payment externally
9. User receives funds
```

## 🎨 User Interface

**Dashboard**:
- Balance display
- Energy level
- Royal status badge
- Quick action buttons
- Mining, Missions, Royal, Withdraw, Energy Recharge

**Mining Menu**:
- Active miners count
- Pending income display
- Miner catalog with stats
- Buy buttons
- Claim income button

**VIP Missions**:
- Country-specific offer
- Payout amount
- Requirements list
- Direct link button
- Proof submission

**Withdrawal Menu**:
- Balance display
- Two withdrawal options
- Fee comparison
- Processing time info
- Minimum amounts

## 🚀 Performance Optimizations

1. **Connection Pooling**: Uses asyncpg pool for efficient database connections
2. **Async Operations**: All database operations are asynchronous
3. **Indexed Queries**: Primary keys and foreign keys for fast lookups
4. **Minimal Queries**: Batch operations where possible
5. **Lazy Loading**: Data loaded only when needed

## 📈 Business Metrics

**Revenue Streams**:
1. OfferToro completions (Iron Gate)
2. Adsterra ad views (Energy recharge)
3. CPA offer completions (VIP Missions)
4. Royal Jelly sales ($1 each)
5. Flash withdrawal fees (20% of withdrawal)

**User Retention Mechanics**:
1. Passive income (mining keeps users coming back)
2. Energy system (requires regular engagement)
3. VIP missions (high-value conversions)
4. Royal status (increases lifetime value)
5. Gamification (progress and achievements)

## ⚙️ Configuration Options

All features can be customized via:
- Environment variables (URLs, tokens, secrets)
- Code constants (miner types, missions, fees)
- Database values (user balances, status)

See `README.md` and `DEPLOYMENT.md` for detailed configuration guides.

## 🔄 Update Strategy

**For miner types**: Edit `MINER_TYPES` dictionary
**For VIP missions**: Edit `VIP_MISSIONS` dictionary
**For fees**: Edit withdrawal calculation logic
**For Royal benefits**: Edit `royal_multiplier` value
**For minimums**: Edit minimum checks in withdrawal functions

All changes require bot restart but no database migration.
