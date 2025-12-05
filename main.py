"""
TITAN NEXUS - ENHANCED (Optimized + Hardening + Phash + Idempotency + Payout Provider Stub)

Este archivo integra las optimizaciones solicitadas y añade un endpoint /version
para comprobar el commit SHA desplegado (lee commit_sha.txt creado en build
o la variable de entorno RENDER_COMMIT_SHA).

Requisitos extra: pillow, imagehash, aiohttp
pip install pillow imagehash aiohttp
"""

import os
import logging
import hashlib
import hmac
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

import asyncpg
from email_validator import validate_email, EmailNotValidError

from PIL import Image
import imagehash
import aiohttp

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# ==============================================================================
# CONFIG & CONSTANTS
# ==============================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("TitanNexusEnhanced")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "postback_secret")
OFFERTORO_PUB_ID = os.environ.get("OFFERTORO_PUB_ID", "0")
OFFERTORO_SECRET = os.environ.get("OFFERTORO_SECRET", "0")

# Payout provider config (example)
PAYOUT_API_URL = os.environ.get("PAYOUT_API_URL", "")  # e.g. https://api.payout.example/v1/payouts
PAYOUT_API_KEY = os.environ.get("PAYOUT_API_KEY", "")

# Admin fastapi token
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change_me_token")

# Wallet placeholders
ADMIN_WALLET_TRC20 = os.environ.get("ADMIN_WALLET_TRC20", "TQn9Y...")
ADMIN_WALLET_TON = os.environ.get("ADMIN_WALLET_TON", "UQ_TON...")

TOKEN_NAME = os.environ.get("TOKEN_NAME", "$NEXUS")
MINING_RATE_ADS = float(os.environ.get("MINING_RATE_ADS", "10.0"))
TOKEN_INITIAL_VALUE_USD = float(os.environ.get("TOKEN_INITIAL_VALUE_USD", "0.01"))

# Phash threshold (tune this value by experiments)
PHASH_THRESHOLD = int(os.environ.get("PHASH_THRESHOLD", "8"))

# Conversation states
(WAITING_EMAIL, WAITING_PROOF_CPA, WAITING_PROOF_PREMIUM, WAITING_PROOF_NFT, WAITING_P2P_PRICE) = range(5)

# Path to commit file written during build (Render build step should write this)
COMMIT_FILE_PATH = Path(__file__).parent.joinpath("commit_sha.txt")

app = FastAPI()
db_pool: Optional[asyncpg.Pool] = None
telegram_app: Optional[Application] = None

# Background queues
payout_queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
background_tasks_started = False

# ==============================================================================
# STATIC INVENTORY (WHITE-HAT)
# ==============================================================================

APPS_CPA = [
    {"id": "APP_UTIL_1", "nombre": "TaskApp Lite", "pago_nexus": 100, "pago_usd": 0.50, "link": "https://example.com/app1"},
    {"id": "APP_UTIL_2", "nombre": "WorkTool Pro", "pago_nexus": 250, "pago_usd": 2.00, "link": "https://example.com/app2"},
]

HIGH_TICKET = [
    {"id": "FINTECH_NEOBANK", "nombre": "💳 Neobank: Cuenta Global", "pago_usd": 15.0, "link": "https://example.com/neobank", "req": "Crear cuenta"},
    {"id": "SAAS_VPN", "nombre": "🛡️ SecureVPN", "pago_usd": 25.0, "link": "https://example.com/vpn", "req": "Suscripción"},
    {"id": "HOSTING_WEB", "nombre": "🌐 WebHost", "pago_usd": 30.0, "link": "https://example.com/hosting", "req": "Comprar hosting"},
]

NFT_MINERS = {
    "mk1": {"name": "⛏️ NFT ROOKIE", "cost_nexus": 500, "mining_rate": 10.0},
    "mk2": {"name": "⚡ NFT ELITE", "cost_nexus": 2000, "mining_rate": 50.0},
}

# ==============================================================================
# DB INIT & MIGRATIONS (includes additional tables)
# ==============================================================================

async def init_db():
    global db_pool
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not configured: running in ephemeral mode (no persistence).")
        return
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    async with db_pool.acquire() as conn:
        # existing tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                first_name TEXT,
                email TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                terms_accepted BOOLEAN DEFAULT FALSE,
                balance_usd DOUBLE PRECISION DEFAULT 0.0,
                balance_nexus DOUBLE PRECISION DEFAULT 0.0,
                xp INTEGER DEFAULT 0,
                is_premium BOOLEAN DEFAULT FALSE,
                trust_score INTEGER DEFAULT 100,
                wallet_address TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_nfts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                nft_type TEXT,
                minted_on_chain BOOLEAN DEFAULT FALSE,
                price_listing DOUBLE PRECISION DEFAULT 0.0,
                is_listed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS proof_hashes (
                hash_id TEXT PRIMARY KEY,
                user_id BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS p2p_listings (
                id SERIAL PRIMARY KEY,
                seller_id BIGINT,
                nft_id INT,
                price_usd DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                type TEXT,
                amount DOUBLE PRECISION,
                status TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # New migrations: postbacks, admin_audit, image_phash
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS postbacks (
                id SERIAL PRIMARY KEY,
                click_id TEXT UNIQUE,
                provider_oid TEXT,
                user_id BIGINT,
                amount DOUBLE PRECISION,
                currency TEXT,
                raw_payload JSONB,
                signature TEXT,
                processed_at TIMESTAMP NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_postbacks_userid ON postbacks(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_postbacks_created_at ON postbacks(created_at)")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT,
                action TEXT,
                target_type TEXT,
                target_id TEXT,
                before_state JSONB,
                after_state JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS image_phash (
                phash_id TEXT PRIMARY KEY,
                user_id BIGINT,
                image_meta JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_image_phash_created ON image_phash(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_created ON transactions(user_id, created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type_status ON transactions(type, status)")

# ==============================================================================
# HELPERS: DB, USERS, BALANCE, AUDIT
# ==============================================================================

async def fetch_user_row(tg_id: int) -> Optional[asyncpg.Record]:
    if not db_pool:
        return None
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tg_id)

async def get_user(tg_id: int) -> Dict[str, Any]:
    row = await fetch_user_row(tg_id)
    if row:
        return dict(row)
    return {
        "telegram_id": tg_id,
        "first_name": "User",
        "email": None,
        "is_verified": False,
        "terms_accepted": False,
        "balance_usd": 0.0,
        "balance_nexus": 0.0,
        "xp": 0,
        "is_premium": False,
        "trust_score": 100,
        "wallet_address": None
    }

async def upsert_user(tg_id: int, first_name: str):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name) VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE SET first_name = EXCLUDED.first_name
        """, tg_id, first_name)

async def modify_user_balance(tg_id: int, usd: float = 0.0, nexus: float = 0.0):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        if usd != 0.0:
            await conn.execute("UPDATE users SET balance_usd = balance_usd + $1 WHERE telegram_id = $2", usd, tg_id)
        if nexus != 0.0:
            await conn.execute("UPDATE users SET balance_nexus = balance_nexus + $1 WHERE telegram_id = $2", nexus, tg_id)

async def set_user_premium(tg_id: int):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET is_premium = TRUE WHERE telegram_id = $1", tg_id)
        await conn.execute("INSERT INTO user_nfts (user_id, nft_type) VALUES ($1, 'VANGUARD_PASS')", tg_id)

async def add_proof_hash(h: str, tg_id: int):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO proof_hashes (hash_id, user_id) VALUES ($1,$2)", h, tg_id)

async def proof_hash_exists(h: str) -> bool:
    if not db_pool:
        return False
    async with db_pool.acquire() as conn:
        return bool(await conn.fetchval("SELECT 1 FROM proof_hashes WHERE hash_id = $1", h))

async def insert_image_phash(phash_hex: str, user_id: int, meta: Dict[str, Any]):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO image_phash (phash_id, user_id, image_meta) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", phash_hex, user_id, meta)

async def fetch_recent_phashes(days: int = 30) -> List[Dict[str, Any]]:
    if not db_pool:
        return []
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT phash_id, user_id, image_meta FROM image_phash WHERE created_at >= $1", cutoff)
        return [dict(r) for r in rows]

async def insert_postback(click_id: str, provider_oid: str, user_id: int, amount: float, currency: str, raw_payload: dict, signature: str) -> bool:
    """
    Insert postback for idempotency. Returns True if inserted new, False if duplicate.
    """
    if not db_pool:
        return True
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO postbacks (click_id, provider_oid, user_id, amount, currency, raw_payload, signature, status)
                VALUES ($1,$2,$3,$4,$5,$6,$7,'pending')
            """, click_id, provider_oid, user_id, amount, currency, raw_payload, signature)
        return True
    except asyncpg.UniqueViolationError:
        return False

async def mark_postback_processed(click_id: str, status: str = "done"):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE postbacks SET status=$1, processed_at=NOW() WHERE click_id=$2", status, click_id)

async def insert_admin_audit(admin_id: int, action: str, target_type: str, target_id: str, before: Optional[dict], after: Optional[dict]):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO admin_audit (admin_id, action, target_type, target_id, before_state, after_state) VALUES ($1,$2,$3,$4,$5,$6)",
                           admin_id, action, target_type, target_id, before, after)

# ==============================================================================
# SECURITY UTILITIES: phash, hmac verify
# ==============================================================================

def compute_phash_from_bytes(image_bytes: bytes) -> str:
    from io import BytesIO
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    ph = imagehash.phash(img)
    return ph.__str__()  # hex string

def phash_distance(phash_hex_a: str, phash_hex_b: str) -> int:
    a = imagehash.hex_to_hash(phash_hex_a)
    b = imagehash.hex_to_hash(phash_hex_b)
    return (a - b)

def verify_hmac(secret: str, data_str: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), data_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# ==============================================================================
# SECURITY ENGINE (wraps checks)
# ==============================================================================

class SecurityEngine:
    @staticmethod
    async def check_duplicate_image_bytes(image_bytes: bytes, user_id: int) -> Dict[str, Any]:
        """Return dict with: {'duplicate': bool, 'reason': str, 'matched_phash': str or None}"""
        # quick MD5 exact check
        md5h = hashlib.md5(image_bytes).hexdigest()
        if await proof_hash_exists(md5h):
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.execute("UPDATE users SET trust_score = GREATEST(trust_score - 20, 0) WHERE telegram_id=$1", user_id)
            return {"duplicate": True, "reason": "md5_exact", "matched_phash": None}

        # compute phash and compare against recent phashes
        try:
            phash = compute_phash_from_bytes(image_bytes)
        except Exception:
            # fallback: treat as non-duplicate but log
            phash = None

        if phash:
            recent = await fetch_recent_phashes(days=30)
            for r in recent:
                other_phash = r.get("phash_id")
                if other_phash:
                    dist = phash_distance(phash, other_phash)
                    if dist <= PHASH_THRESHOLD:
                        # similar image found
                        # penalize
                        if db_pool:
                            async with db_pool.acquire() as conn:
                                await conn.execute("UPDATE users SET trust_score = GREATEST(trust_score - 20, 0) WHERE telegram_id=$1", user_id)
                        return {"duplicate": True, "reason": "phash_similar", "matched_phash": other_phash}
            # no similar found, store phash
            meta = {"method": "phash", "detected_at": datetime.utcnow().isoformat()}
            await insert_image_phash(phash, user_id, meta)

        # store md5 as well for exact future checks
        await add_proof_hash(md5h, user_id)
        return {"duplicate": False, "reason": "ok", "matched_phash": None}

    @staticmethod
    def verify_postback_signature(data_str: str, signature: str) -> bool:
        return verify_hmac(POSTBACK_SECRET, data_str, signature)

# ==============================================================================
# BOT UI HELPERS
# ==============================================================================

def mk_reply_kb(rows: List[List[str]]):
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def mk_inline_buttons(buttons: List[List[InlineKeyboardButton]]):
    return InlineKeyboardMarkup(buttons)

# ==============================================================================
# BUSINESS LOGIC: Onboarding, Menus, Proofs (with phash)
# ==============================================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.first_name or "User")
    db_user = await get_user(user.id)
    if not db_user.get("email"):
        await update.message.reply_text("🔐 TITAN NEXUS - Por favor escribe tu email para continuar:")
        return WAITING_EMAIL
    if not db_user.get("is_verified"):
        await show_iron_gate(update, context)
        return ConversationHandler.END
    await show_main_hud(update, context)
    return ConversationHandler.END

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        validated = validate_email(text).email
    except EmailNotValidError:
        await update.message.reply_text("❌ Email inválido. Por favor intenta de nuevo.")
        return WAITING_EMAIL
    user_id = update.effective_user.id
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET email=$1, terms_accepted=TRUE WHERE telegram_id=$2", validated, user_id)
    await update.message.reply_text("✅ Email registrado. Ahora completa 1 misión para activar tu wallet.")
    await show_iron_gate(update, context)
    return ConversationHandler.END

async def show_iron_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    toro_link = f"https://www.offertoro.com/ifr/show/{OFFERTORO_PUB_ID}/{user_id}/{OFFERTORO_SECRET}"
    msg = "⛔️ IRON GATE: Completa 1 misión (descarga app) para activar tu wallet $NEXUS."
    kb = [
        [InlineKeyboardButton("🔓 DESCARGAR (Abrir muro)", url=toro_link)],
        [InlineKeyboardButton("🔄 YA COMPLETÉ", callback_data="check_gate")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=mk_inline_buttons(kb))
    else:
        await update.message.reply_text(msg, reply_markup=mk_inline_buttons(kb))

async def show_main_hud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    status = "VANGUARD" if user.get("is_premium") else "ROOKIE"
    msg = (
        f"🌌 TITAN NEXUS | {status}\n"
        f"👤 {user.get('first_name')}\n"
        f"💵 USD: ${user.get('balance_usd',0.0):.2f} | 💎 {TOKEN_NAME}: {user.get('balance_nexus',0.0):.1f}\n"
        f"XP / Pre-Token: {user.get('xp',0)} | Trust: {user.get('trust_score',100)}\n\n"
        "Selecciona una acción:"
    )
    kb = [
        ["⛏️ ADS MINING", "⚡ FAST CASH (TAREAS)"],
        ["🐋 VANGUARD (Premium)", "🛒 NFT MARKET"],
        ["👤 MI PERFIL", "🏦 RETIRAR"]
    ]
    await update.message.reply_text(msg, reply_markup=mk_reply_kb(kb))

# Modules (unchanged)
async def mining_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_link = "https://example.com/ad"
    msg = f"⛏️ MINERÍA ADS: Gana hasta +{MINING_RATE_ADS} {TOKEN_NAME} por interacción.\nAbre el link para contabilizar."
    kb = [[InlineKeyboardButton("🚀 MINAR AHORA", url=ad_link)]]
    await update.message.reply_text(msg, reply_markup=mk_inline_buttons(kb))

async def fast_cash_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tarea = random.choice(APPS_CPA)
    context.user_data['current_task'] = tarea
    msg = (
        f"⚡ MISIÓN: {tarea['nombre']}\n"
        f"Gana: {tarea['pago_nexus']} {TOKEN_NAME} + ${tarea['pago_usd']}\n"
        f"1) Descarga: {tarea['link']}\n2) Sube evidencia."
    )
    kb = [[InlineKeyboardButton("📤 SUBIR EVIDENCIA", callback_data="upload_proof_cpa")]]
    await update.message.reply_text(msg, reply_markup=mk_inline_buttons(kb))

async def vanguard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user.get("is_premium"):
        msg = (
            "🔒 VANGUARD: Acceso Premium.\n"
            "Compra el Pase Vanguard ($15) o quema 5000 $NEXUS para entrar."
        )
        kb = [[InlineKeyboardButton("💎 COMPRAR PASE ($15)", callback_data="buy_premium")]]
        await update.message.reply_text(msg, reply_markup=mk_inline_buttons(kb))
        return
    kb = []
    for off in HIGH_TICKET:
        kb.append([InlineKeyboardButton(f"{off['nombre']} - ${off['pago_usd']}", url=off['link'])])
    await update.message.reply_text("🐋 VANGUARD OFFERS (legales):", reply_markup=mk_inline_buttons(kb))

async def nft_market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🛒 NFT MARKET: Mineros y Pases. Compra mineros con $NEXUS o ve ventas P2P."
    kb = []
    for k, v in NFT_MINERS.items():
        kb.append([InlineKeyboardButton(f"{v['name']} - {v['cost_nexus']} {TOKEN_NAME}", callback_data=f"mint_nft_{k}")])
    kb.append([InlineKeyboardButton("🛍️ MERCADO P2P", callback_data="open_p2p")])
    await update.message.reply_text(msg, reply_markup=mk_inline_buttons(kb))

# ==============================================================================
# PROOF HANDLERS with PHASH checks
# ==============================================================================

async def ask_proof_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.callback_query.answer()
    await u.callback_query.message.reply_text("📸 Sube la captura ahora.")
    data = u.callback_query.data or ""
    if "cpa" in data:
        return WAITING_PROOF_CPA
    if "premium" in data:
        return WAITING_PROOF_PREMIUM
    return ConversationHandler.END

async def process_proof_generic(update: Update, context: ContextTypes.DEFAULT_TYPE, ptype: str):
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text("Envíame una foto válida.")
        return ConversationHandler.END
    photo = update.message.photo[-1]
    f = await photo.get_file()
    image_bytes = await f.download_as_bytearray()

    # Security: perceptual hash + md5 duplicate detection
    dup_result = await SecurityEngine.check_duplicate_image_bytes(image_bytes, user_id)
    if dup_result.get("duplicate"):
        await update.message.reply_text("⚠️ Imagen duplicada detectada. Acción cancelada.")
        return ConversationHandler.END

    # Send to admin for approval
    caption = f"🕵️ NUEVA PRUEBA ({ptype})\nUser: {user_id}"
    kb = []
    if ptype == "CPA":
        kb = [[InlineKeyboardButton("✅ APROBAR CPA", callback_data=f"admin_paycpa_{user_id}")]]
    else:
        kb = [[InlineKeyboardButton("✅ ACTIVAR PREMIUM", callback_data=f"admin_activate_{user_id}")]]
    await context.bot.send_photo(ADMIN_ID, photo.file_id, caption=caption, reply_markup=mk_inline_buttons(kb))
    await update.message.reply_text("✅ Evidencia enviada. Un moderador validará y procesará la recompensa.")
    return ConversationHandler.END

async def handle_proof_cpa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_proof_generic(update, context, "CPA")

async def handle_proof_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_proof_generic(update, context, "PREMIUM")

# ==============================================================================
# ADMIN CALLBACKS (with audit logging)
# ==============================================================================

async def admin_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id != ADMIN_ID:
        return
    q = u.callback_query
    data = (q.data or "").split("_")
    if len(data) < 3:
        await q.answer()
        return
    action = data[1]
    try:
        uid = int(data[2])
    except ValueError:
        await q.answer()
        return

    # snapshot before state
    before = None
    if db_pool:
        async with db_pool.acquire() as conn:
            before_row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", uid)
            before = dict(before_row) if before_row else None

    if action == "paycpa":
        await modify_user_balance(uid, usd=0.50, nexus=100.0)
        await c.bot.send_message(uid, "✅ Tarea aprobada: +100 $NEXUS + $0.50 USD")
        await q.edit_message_caption("✅ CPA aprobado y pagado.")
        after = None
        if db_pool:
            async with db_pool.acquire() as conn:
                after_row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", uid)
                after = dict(after_row) if after_row else None
        await insert_admin_audit(u.effective_user.id, "paycpa", "user", str(uid), before, after)

    elif action == "activate":
        await set_user_premium(uid)
        await c.bot.send_message(uid, "💎 Vanguard activado. Bienvenido.")
        await q.edit_message_caption("✅ Usuario promovido a Premium.")
        after = None
        if db_pool:
            async with db_pool.acquire() as conn:
                after_row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", uid)
                after = dict(after_row) if after_row else None
        await insert_admin_audit(u.effective_user.id, "activate_premium", "user", str(uid), before, after)

# ==============================================================================
# P2P / NFT OFF-CHAIN (transactional safe buy)
# ==============================================================================

async def p2p_sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user
    if len(args) < 2:
        await update.message.reply_text("Uso: /sell <nft_id> <price_usd>")
        return
    try:
        nft_id = int(args[0]); price = float(args[1])
    except ValueError:
        await update.message.reply_text("Parámetros inválidos.")
        return
    if not db_pool:
        await update.message.reply_text("DB no disponible.")
        return
    async with db_pool.acquire() as conn:
        owner = await conn.fetchval("SELECT user_id FROM user_nfts WHERE id=$1", nft_id)
        if owner != user.id:
            await update.message.reply_text("No eres el propietario de ese NFT.")
            return
        await conn.execute("INSERT INTO p2p_listings (seller_id, nft_id, price_usd) VALUES ($1,$2,$3)", user.id, nft_id, price)
    await update.message.reply_text("✅ Oferta publicada. Fee casa: 10% al venderse.")

async def p2p_listings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db_pool:
        await update.message.reply_text("DB no disponible.")
        return
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT p.id, p.nft_id, p.price_usd, u.first_name AS seller FROM p2p_listings p JOIN users u ON u.telegram_id = p.seller_id")
        if not rows:
            await update.message.reply_text("No hay ofertas activas.")
            return
        lines = [f"ID:{r['id']} NFT:{r['nft_id']} ${r['price_usd']:.2f} Seller:{r['seller']}" for r in rows]
        await update.message.reply_text("\n".join(lines))

async def safe_p2p_buy(pool, buyer_id: int, listing_id: int):
    """
    Transactional safe P2P buy. Raises exceptions on failure.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT * FROM p2p_listings WHERE id=$1 FOR UPDATE", listing_id)
            if not row:
                raise Exception("Listing not found")
            nft_id = row['nft_id']
            seller_id = row['seller_id']
            price = float(row['price_usd'])
            bal = await conn.fetchval("SELECT balance_usd FROM users WHERE telegram_id=$1 FOR UPDATE", buyer_id)
            if bal is None or bal < price:
                raise Exception("Insufficient funds")
            fee = price * 0.10
            seller_net = price - fee
            await conn.execute("UPDATE users SET balance_usd = balance_usd - $1 WHERE telegram_id = $2", price, buyer_id)
            await conn.execute("UPDATE users SET balance_usd = balance_usd + $1 WHERE telegram_id = $2", seller_net, seller_id)
            await conn.execute("UPDATE user_nfts SET user_id = $1, is_listed = FALSE WHERE id = $2", buyer_id, nft_id)
            await conn.execute("DELETE FROM p2p_listings WHERE id=$1", listing_id)
            await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1,$2,$3,$4)", buyer_id, "p2p_buy", price, "done")
    return True

async def p2p_buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user
    if len(args) < 1:
        await update.message.reply_text("Uso: /buy <listing_id>")
        return
    lid = int(args[0])
    if not db_pool:
        await update.message.reply_text("DB no disponible.")
        return
    try:
        await safe_p2p_buy(db_pool, user.id, lid)
        await update.message.reply_text("✅ Compra completada. NFT transferido. Fee de la casa cobrada.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error en compra: {str(e)}")

# ==============================================================================
# POSTBACKS / WEBHOOKS (OfferToro) - Secure + Idempotent
# ==============================================================================

@app.get("/postback/offertoro")
async def offertoro_postback(oid: str, user_id: int, amount: float, signature: str, click_id: Optional[str] = ""):
    # Construct verification string according to partner's doc (example)
    data_check = f"{oid}-{click_id}-{user_id}-{amount}"
    if not SecurityEngine.verify_postback_signature(data_check, signature):
        logger.warning("Invalid postback signature for oid=%s click=%s", oid, click_id)
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Idempotency: insert postback; if duplicate -> ignore processing
    inserted = await insert_postback(click_id or f"cb_{random.randint(0,1_000_000)}", oid, user_id, amount, "USD", {"oid": oid, "click_id": click_id, "amount": amount}, signature)
    if not inserted:
        logger.info("Duplicate postback received for click_id=%s - ignoring.", click_id)
        # Return ok to endpoint but do not reprocess actions
        return "1"

    # mark user verified and small onboarding bonus
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_verified = TRUE, xp = xp + 50, balance_usd = balance_usd + $1 WHERE telegram_id = $2", 0.10, user_id)

    # If the network expects you to pay the user, queue a payout job
    # Example: compute user_share and enqueue
    user_share = round(amount * 0.7, 2)
    # push a payout job only if you are responsible to pay user (depends on network)
    # await payout_queue.put({"user_id": user_id, "amount": user_share, "currency": "USD", "external_id": click_id or None})

    # mark processed
    await mark_postback_processed(click_id or "", "done")
    return "1"

# ==============================================================================
# PAYOUT WORKER (calls provider API with idempotency)
# ==============================================================================

async def call_payout_provider(api_url: str, api_key: str, dest: str, amount: float, currency: str, external_id: str) -> Dict[str, Any]:
    """Example async call to payout provider. Replace with provider SDK in prod."""
    if not api_url or not api_key:
        # provider not configured in env; simulate success response
        await asyncio.sleep(0.2)
        return {"status": "simulated", "tx_id": f"sim-{external_id}-{random.randint(1000,9999)}", "fee_charged": 0.0}
    payload = {
        "external_id": external_id,
        "destination": dest,
        "amount": float(amount),
        "currency": currency
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=payload, headers=headers, timeout=30) as resp:
            data = await resp.json()
            return data

async def payout_worker():
    logger.info("Payout worker started.")
    while True:
        job = await payout_queue.get()
        try:
            logger.info("Processing payout job: %s", job)
            user_id = job.get("user_id")
            amount = float(job.get("amount", 0.0))
            currency = job.get("currency", "USD")
            external_id = job.get("external_id") or f"ext-{random.randint(0,999999)}"
            # fetch user wallet (if available)
            dest_wallet = None
            if db_pool:
                async with db_pool.acquire() as conn:
                    dest_wallet = await conn.fetchval("SELECT wallet_address FROM users WHERE telegram_id=$1", user_id)
            if not dest_wallet:
                # cannot pay user: record failure
                logger.warning("No wallet for user %s; marking payout failed.", user_id)
                if db_pool:
                    async with db_pool.acquire() as conn:
                        await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1,$2,$3,$4)", user_id, "payout", amount, "failed_no_wallet")
                payout_queue.task_done()
                continue

            # Record transaction processing row
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1,$2,$3,$4)", user_id, "payout", amount, "processing")

            # Call provider
            resp = await call_payout_provider(PAYOUT_API_URL, PAYOUT_API_KEY, dest_wallet, amount, currency, external_id)
            logger.info("Payout provider response: %s", resp)

            # Update transaction status on success
            if db_pool:
                async with db_pool.acquire() as conn:
                    tx_id = resp.get("tx_id") or resp.get("id") or f"sim-{external_id}"
                    await conn.execute("UPDATE transactions SET status='done' WHERE user_id=$1 AND type='payout' AND status='processing' AND amount=$2", user_id, amount)
            logger.info("Payout job completed: %s", job)
        except Exception:
            logger.exception("Failed to process payout job: %s", job)
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES ($1,$2,$3,$4)", job.get("user_id"), "payout", job.get("amount"), "failed")
        finally:
            payout_queue.task_done()

# ==============================================================================
# BACKGROUND: start workers (ensure idempotent scheduling)
# ==============================================================================

def ensure_background_workers():
    global background_tasks_started
    if background_tasks_started:
        return
    background_tasks_started = True
    loop = asyncio.get_event_loop()
    loop.create_task(payout_worker())
    logger.info("Background workers scheduled (payout_worker).")

# ==============================================================================
# BLOCKCHAIN STUBS (no-op until integrated)
# ==============================================================================

async def blockchain_mint_nft_onchain(user_wallet: str, nft_metadata: dict) -> Dict[str, Any]:
    logger.info("STUB mint onchain user=%s metadata=%s", user_wallet, nft_metadata)
    return {"tx": "simulated_tx_hash", "token_id": random.randint(1000, 9999)}

async def blockchain_transfer_token_to_user(user_wallet: str, amount: float) -> Dict[str, Any]:
    logger.info("STUB token transfer user=%s amount=%s", user_wallet, amount)
    return {"tx": "simulated_transfer_hash"}

# ==============================================================================
# VERSION ENDPOINT: expose commit SHA (reads commit_sha.txt or env var)
# ==============================================================================

@app.get("/version")
async def version():
    """
    Returns deployed commit identifier.
    Build recommendation (Render):
      echo $(git rev-parse --short HEAD) > commit_sha.txt
    Then the app can read commit_sha.txt at runtime.
    Alternatively set env var RENDER_COMMIT_SHA in your build/deploy pipeline.
    """
    try:
        if COMMIT_FILE_PATH.exists():
            sha = COMMIT_FILE_PATH.read_text().strip()
            return {"commit": sha, "source": "commit_file"}
    except Exception as e:
        logger.exception("Failed reading commit file: %s", e)

    sha_env = os.environ.get("RENDER_COMMIT_SHA")
    if sha_env:
        return {"commit": sha_env, "source": "env"}

    raise HTTPException(status_code=404, detail="Version info not available")

# ==============================================================================
# TELEGRAM APP BOOTSTRAP (handlers registration)
# ==============================================================================

async def get_bot_app() -> Application:
    global telegram_app
    if telegram_app is None:
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

        telegram_app.add_handler(CommandHandler("start", start_handler))
        telegram_app.add_handler(MessageHandler(filters.Regex("MINAR|ADS"), mining_menu))
        telegram_app.add_handler(MessageHandler(filters.Regex("FAST CASH"), fast_cash_menu))
        telegram_app.add_handler(MessageHandler(filters.Regex("VANGUARD"), vanguard_menu))
        telegram_app.add_handler(MessageHandler(filters.Regex("NFT|MARKET"), nft_market_menu))

        conv_entry = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("Hola"), start_handler)],
            states={WAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)]},
            fallbacks=[CommandHandler("start", start_handler)]
        )
        conv_proofs = ConversationHandler(
            entry_points=[CallbackQueryHandler(ask_proof_callback, pattern="upload_proof_")],
            states={
                WAITING_PROOF_CPA: [MessageHandler(filters.PHOTO, handle_proof_cpa)],
                WAITING_PROOF_PREMIUM: [MessageHandler(filters.PHOTO, handle_proof_premium)]
            },
            fallbacks=[]
        )
        telegram_app.add_handler(conv_entry)
        telegram_app.add_handler(conv_proofs)

        telegram_app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

        telegram_app.add_handler(CommandHandler("sell", p2p_sell_cmd))
        telegram_app.add_handler(CommandHandler("listings", p2p_listings_cmd))
        telegram_app.add_handler(CommandHandler("buy", p2p_buy_cmd))
        telegram_app.add_handler(CommandHandler("p2p", p2p_listings_cmd))

        # placeholders for some callbacks to keep handler registration stable
        telegram_app.add_handler(CallbackQueryHandler(lambda u,c: None, pattern="buy_premium"))
        telegram_app.add_handler(CallbackQueryHandler(lambda u,c: None, pattern="mint_nft_"))
        telegram_app.add_handler(CallbackQueryHandler(lambda u,c: None, pattern="claim_rewards"))

        await telegram_app.initialize()
    return telegram_app

# ==============================================================================
# STARTUP / SHUTDOWN
# ==============================================================================

@app.on_event("startup")
async def on_startup():
    logger.info("Starting Titan Nexus Enhanced app...")
    await init_db()
    bot = await get_bot_app()
    ensure_background_workers()
    try:
        asyncio.create_task(bot.updater.start_polling())
        logger.info("Telegram polling started (development mode).")
    except Exception:
        logger.exception("Could not start polling; ensure webhooks configured in production.")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down Titan Nexus Enhanced...")
    if telegram_app:
        await telegram_app.shutdown()
    if db_pool:
        await db_pool.close()

# ==============================================================================
# UTILS / ADMIN TEMPLATES
# ==============================================================================

def admin_notify_text_for_proof(user_id: int, ptype: str) -> str:
    return f"🕵️ NUEVA PRUEBA ({ptype})\nUser: {user_id}\nRevisa y aprueba."

# ==============================================================================
# ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    print("Module ready. Run with: uvicorn titan_nexus_enhanced:app --reload")
