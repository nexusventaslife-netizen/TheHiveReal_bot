import os
import logging
import hashlib
from datetime import datetime
from functools import wraps

from quart import Quart, request, jsonify
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

import aiohttp
import aiosqlite

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENV VARS
# ---------------------------------------------------------------------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

CPALEAD_ID = os.environ.get("CPALEAD_ID", "")
OFFERTORO_ID = os.environ.get("OFFERTORO_ID", "")
POLLFISH_KEY = os.environ.get("POLLFISH_KEY", "")
AYETSTUDIOS_KEY = os.environ.get("AYETSTUDIOS_KEY", "")

UDEMY_AFFILIATE = os.environ.get("UDEMY_AFFILIATE", "griddled")
FIVERR_AFFILIATE = os.environ.get("FIVERR_AFFILIATE", "griddled")

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET", "")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")

# ---------------------------------------------------------------------------
# GLOBAL STATE
# ---------------------------------------------------------------------------

app = Quart(__name__)
application: Application | None = None
http_session: aiohttp.ClientSession | None = None
db: aiosqlite.Connection | None = None

DB_PATH = "database.db"

# ---------------------------------------------------------------------------
# COUNTRY CONFIG
# ---------------------------------------------------------------------------

COUNTRY_DATA = {
    "US": {
        "name": "USA",
        "flag": "US",
        "max_daily": 180,
        "methods": ["paypal", "stripe", "venmo"],
        "min_withdraw": 5.0,
        "currency": "USD",
    },
    "MX": {
        "name": "Mexico",
        "flag": "MX",
        "max_daily": 60,
        "methods": ["paypal", "oxxo", "spei"],
        "min_withdraw": 2.0,
        "currency": "MXN",
    },
    "BR": {
        "name": "Brasil",
        "flag": "BR",
        "max_daily": 70,
        "methods": ["pix", "paypal"],
        "min_withdraw": 2.0,
        "currency": "BRL",
    },
    "AR": {
        "name": "Argentina",
        "flag": "AR",
        "max_daily": 50,
        "methods": ["mercadopago", "binance"],
        "min_withdraw": 1.0,
        "currency": "ARS",
    },
    "CO": {
        "name": "Colombia",
        "flag": "CO",
        "max_daily": 50,
        "methods": ["nequi", "daviplata", "bancolombia"],
        "min_withdraw": 2.0,
        "currency": "COP",
    },
    "ES": {
        "name": "Espana",
        "flag": "ES",
        "max_daily": 130,
        "methods": ["paypal", "bizum", "sepa"],
        "min_withdraw": 3.0,
        "currency": "EUR",
    },
    "CN": {
        "name": "China",
        "flag": "CN",
        "max_daily": 80,
        "methods": ["alipay", "wechat", "unionpay", "crypto"],
        "min_withdraw": 100.0,
        "currency": "CNY",
    },
    "RU": {
        "name": "Russia",
        "flag": "RU",
        "max_daily": 60,
        "methods": ["crypto", "yoomoney", "qiwi", "webmoney"],
        "min_withdraw": 500.0,
        "currency": "RUB",
    },
    "KR": {
        "name": "South Korea",
        "flag": "KR",
        "max_daily": 140,
        "methods": ["paypal", "toss", "kakaopay", "naverpay", "crypto"],
        "min_withdraw": 10000.0,
        "currency": "KRW",
    },
    "VE": {
        "name": "Venezuela",
        "flag": "VE",
        "max_daily": 35,
        "methods": ["crypto", "binance", "airtm", "reserve"],
        "min_withdraw": 2.0,
        "currency": "USD",
    },
    "NG": {
        "name": "Nigeria",
        "flag": "NG",
        "max_daily": 50,
        "methods": ["paystack", "flutterwave", "crypto"],
        "min_withdraw": 5000.0,
        "currency": "NGN",
    },
    "AU": {
        "name": "Australia",
        "flag": "AU",
        "max_daily": 180,
        "methods": ["paypal", "stripe", "poli", "bpay", "crypto"],
        "min_withdraw": 10.0,
        "currency": "AUD",
    },
    "IN": {
        "name": "India",
        "flag": "IN",
        "max_daily": 60,
        "methods": ["paypal", "paytm", "phonepe", "upi", "crypto"],
        "min_withdraw": 500.0,
        "currency": "INR",
    },
    "ZA": {
        "name": "South Africa",
        "flag": "ZA",
        "max_daily": 70,
        "methods": ["paypal", "ozow", "snapscan", "crypto"],
        "min_withdraw": 100.0,
        "currency": "ZAR",
    },
    "GLOBAL": {
        "name": "Global",
        "flag": "GLOBAL",
        "max_daily": 80,
        "methods": ["paypal", "binance", "crypto", "payoneer", "wise"],
        "min_withdraw": 2.0,
        "currency": "USD",
    },
}

# ---------------------------------------------------------------------------
# MARKETPLACE & TASK PLATFORMS
# ---------------------------------------------------------------------------

MARKETPLACE_PLATFORMS = {
    "udemy": {
        "name": "Udemy",
        "url": "https://udemy.com",
        "commission": 15,
        "description": "Cursos de Freelancing Marketing Programacion",
    },
    "coursera": {
        "name": "Coursera",
        "url": "https://coursera.org",
        "commission": 20,
        "description": "Certificaciones profesionales",
    },
    "skillshare": {
        "name": "Skillshare",
        "url": "https://skillshare.com",
        "commission": 25,
        "description": "Diseno Video Creatividad",
    },
    "fiverr": {
        "name": "Fiverr",
        "url": "https://fiverr.com",
        "commission": 30,
        "description": "Vende tus servicios freelance",
    },
    "upwork": {
        "name": "Upwork",
        "url": "https://upwork.com",
        "commission": 10,
        "description": "Consigue clientes a largo plazo",
    },
}

TASK_PLATFORMS = {
    "cpalead": {"name": "CPALead", "api_key": CPALEAD_ID},
    "offertoro": {"name": "OfferToro", "api_key": OFFERTORO_ID},
    "pollfish": {"name": "Pollfish", "api_key": POLLFISH_KEY},
    "ayetstudios": {"name": "AyetStudios", "api_key": AYETSTUDIOS_KEY},
}

# ---------------------------------------------------------------------------
# DECORADOR ERRORES
# ---------------------------------------------------------------------------


def error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TelegramError as e:
            logger.error(f"Telegram error in {func.__name__}: {e}")
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)

    return wrapper


# ---------------------------------------------------------------------------
# DB (SQLite + aiosqlite)
# ---------------------------------------------------------------------------


async def init_db() -> bool:
    global db
    try:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                country TEXT DEFAULT 'GLOBAL',
                subscription TEXT DEFAULT 'FREE',
                tokens INTEGER DEFAULT 100,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                wallet_address TEXT,
                payment_method TEXT,
                payment_email TEXT,
                total_earned REAL DEFAULT 0,
                pending_payout REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS tasks_completed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id TEXT,
                platform TEXT,
                reward REAL,
                status TEXT DEFAULT 'pending',
                completed_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                commission_earned REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                destination TEXT,
                status TEXT DEFAULT 'pending',
                processed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await db.commit()
        logger.info("SQLite DB inicializada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error inicializando SQLite: {e}", exc_info=True)
        return False


async def get_or_create_user(
    user_id: int,
    first_name: str,
    username: str | None,
    ref_code: str | None = None,
    country_code: str = "GLOBAL",
):
    if db is None:
        return None
    try:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            await db.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            await db.commit()
            return dict(row)

        my_ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
        wallet = "0x" + os.urandom(20).hex()

        referred_by_id = None
        if ref_code:
            async with db.execute(
                "SELECT id FROM users WHERE referral_code = ?", (ref_code,)
            ) as cursor:
                ref_row = await cursor.fetchone()
                if ref_row:
                    referred_by_id = ref_row["id"]

        await db.execute(
            """
            INSERT INTO users (
                id, first_name, username, referral_code, referred_by,
                wallet_address, country
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                first_name,
                username,
                my_ref_code,
                referred_by_id,
                wallet,
                country_code,
            ),
        )

        if referred_by_id:
            await db.execute(
                """
                INSERT OR IGNORE INTO referrals (referrer_id, referred_id, commission_earned)
                VALUES (?, ?, 1.00)
                """,
                (referred_by_id, user_id),
            )
            await db.execute(
                """
                UPDATE users
                   SET tokens = tokens + 100,
                       total_earned = total_earned + 1.0
                 WHERE id = ?
                """,
                (referred_by_id,),
            )

        await db.commit()

        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as c2:
            new_row = await c2.fetchone()
        logger.info(f"Usuario creado: {user_id} - {first_name}")
        return dict(new_row) if new_row else None
    except Exception as e:
        logger.error(f"Error get_or_create_user: {e}", exc_info=True)
        return None


async def add_task_earning(user_id: int, task_id: str, platform: str, reward: float):
    if reward <= 0 or reward > 100:
        logger.warning(f"Reward invalido: {reward}")
        return False
    if db is None:
        return False
    try:
        await db.execute(
            """
            INSERT INTO tasks_completed (user_id, task_id, platform, reward, status)
            VALUES (?, ?, ?, ?, 'completed')
            """,
            (user_id, task_id, platform, reward),
        )
        await db.execute(
            """
            UPDATE users
               SET total_earned    = total_earned + ?,
                   pending_payout  = pending_payout + ?,
                   tokens          = tokens + 10,
                   tasks_completed = tasks_completed + 1
             WHERE id = ?
            """,
            (reward, reward, user_id),
        )
        await db.commit()
        logger.info(f"Tarea completada: user={user_id}, reward={reward}")
        return True
    except Exception as e:
        logger.error(f"Error add_task_earning: {e}", exc_info=True)
        return False


async def fetch_live_tasks(platform_name: str):
    if platform_name not in TASK_PLATFORMS:
        return []
    platform = TASK_PLATFORMS[platform_name]
    if not platform["api_key"]:
        return []
    try:
        assert http_session is not None
        async with http_session.get(
            f"https://api.{platform_name}.com/offers",
            params={"api_key": platform["api_key"]},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("offers", [])[:5]
    except aiohttp.ClientError as e:
        logger.error(f"Error HTTP {platform_name}: {e}")
    except Exception as e:
        logger.error(f"Error inesperado {platform_name}: {e}", exc_info=True)
    return []


# ---------------------------------------------------------------------------
# HANDLERS TELEGRAM
# ---------------------------------------------------------------------------


@error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_code = context.args[0] if context.args else None

    user_data = await get_or_create_user(
        user.id,
        user.first_name or "",
        user.username or "user",
        ref_code,
    )
    if not user_data:
        await update.message.reply_text("Error al inicializar. Usa /start de nuevo")
        return

    country_config = COUNTRY_DATA.get(user_data["country"], COUNTRY_DATA["GLOBAL"])

    welcome_msg = (
        "BIENVENIDO A GRIDDLED V3\n\n"
        f"Hola {user.first_name}\n\n"
        f"Tu pais: {country_config['name']}\n"
        f"Potencial diario: ${country_config['max_daily']}\n"
        f"Tokens: {user_data['tokens']}\n"
        f"Plan: {user_data['subscription']}\n\n"
        "Metodos de pago:\n"
    )

    for method in country_config["methods"][:3]:
        welcome_msg += f"- {method.upper()}\n"

    welcome_msg += "\nEmpieza ahora:"

    keyboard = [
        ["Ver Tareas", "Dashboard"],
        ["Marketplace", "Referir"],
        ["Config Pagos", "Stats"],
    ]

    await update.message.reply_text(
        welcome_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


@error_handler
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cargando tareas disponibles...")

    tasks: list[dict] = []
    task_id = 1

    for platform_name in ["cpalead", "offertoro", "pollfish"]:
        live_tasks = await fetch_live_tasks(platform_name)
        for task in live_tasks[:3]:
            tasks.append(
                {
                    "id": task_id,
                    "title": task.get("name", f"Tarea {task_id}"),
                    "reward": float(task.get("payout", 0.25)),
                    "platform": platform_name,
                    "task_id": task.get("id", str(task_id)),
                }
            )
            task_id += 1

    if not tasks:
        tasks = [
            {"id": 1, "title": "Encuesta 2min", "reward": 0.25, "platform": "pollfish", "task_id": "demo_1"},
            {"id": 2, "title": "Instalar App", "reward": 0.80, "platform": "cpalead", "task_id": "demo_2"},
            {"id": 3, "title": "Ver Video 30s", "reward": 0.10, "platform": "generic", "task_id": "demo_3"},
            {"id": 4, "title": "Review", "reward": 0.35, "platform": "generic", "task_id": "demo_4"},
            {"id": 5, "title": "Validar Dato", "reward": 0.15, "platform": "generic", "task_id": "demo_5"},
            {"id": 6, "title": "Etiquetar Foto", "reward": 0.08, "platform": "generic", "task_id": "demo_6"},
            {"id": 7, "title": "Red Social", "reward": 0.40, "platform": "generic", "task_id": "demo_7"},
            {"id": 8, "title": "Research", "reward": 0.60, "platform": "generic", "task_id": "demo_8"},
        ]

    tasks_msg = "TAREAS DISPONIBLES\n\n"
    for task in tasks:
        tasks_msg += f"{task['id']}. {task['title']}\n   ${task['reward']:.2f}\n\n"
    tasks_msg += f"Escribe el numero (1-{len(tasks)})"

    context.user_data["tasks"] = tasks
    await update.message.reply_text(tasks_msg)


@error_handler
async def handle_task_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = update.message.text or ""
    if not text.isdigit():
        return

    task_num = int(text)
    tasks: list[dict] = context.user_data.get("tasks", [])
    if task_num < 1 or task_num > len(tasks):
        return

    task = tasks[task_num - 1]

    msg = (
        f"Tarea: {task['title']}\n\n"
        f"Ganaras: ${task['reward']:.2f}\n"
        "Bonus: +10 tokens\n\n"
        "Pasos:\n"
        "1. Abre el link\n"
        "2. Completa la tarea\n"
        "3. Presiona Complete"
    )

    keyboard = [
        [InlineKeyboardButton("Abrir Tarea", url="https://example.com/task")],
        [InlineKeyboardButton("Complete", callback_data=f"done_{task_num}")],
        [InlineKeyboardButton("Cancelar", callback_data="cancel")],
    ]

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


@error_handler
async def task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("done_"):
        return

    task_num = int(query.data.split("_")[1])
    tasks: list[dict] = context.user_data.get("tasks", [])
    if task_num < 1 or task_num > len(tasks):
        await query.edit_message_text("Tarea no valida")
        return

    task = tasks[task_num - 1]
    user_id = query.from_user.id

    success = await add_task_earning(
        user_id, task["task_id"], task["platform"], task["reward"]
    )

    if success:
        msg = (
            "TAREA COMPLETADA\n\n"
            f"+${task['reward']:.2f}\n"
            "+10 tokens\n\n"
            "Usa /dashboard para ver tu progreso"
        )
        await query.edit_message_text(msg)
    else:
        await query.edit_message_text("Error procesando. Intenta de nuevo")


@error_handler
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db is None:
        await update.message.reply_text("Error de base de datos")
        return
    try:
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            user_row = await cur.fetchone()
        if not user_row:
            await update.message.reply_text("Usuario no encontrado")
            return
        user_data = dict(user_row)

        async with db.execute(
            "SELECT COUNT(*) AS c FROM referrals WHERE referrer_id = ?", (user_id,)
        ) as cur:
            ref_row = await cur.fetchone()
        refs_count = ref_row["c"] if ref_row else 0

        country_config = COUNTRY_DATA.get(
            user_data["country"], COUNTRY_DATA["GLOBAL"]
        )

        msg = (
            "TU DASHBOARD\n\n"
            f"{country_config['name']}\n"
            f"Plan: {user_data['subscription']}\n"
            f"Tokens: {user_data['tokens']}\n\n"
            "FINANZAS:\n"
            f"Total ganado: ${user_data['total_earned']:.2f}\n"
            f"Pendiente: ${user_data['pending_payout']:.2f}\n"
            f"Retirado: ${user_data['total_withdrawn']:.2f}\n"
            f"Minimo retiro: ${country_config['min_withdraw']:.2f}\n\n"
            f"Tareas: {user_data['tasks_completed']}\n"
            f"Referidos: {refs_count}\n\n"
            f"Wallet: {user_data['wallet_address']}\n"
            f"Codigo: {user_data['referral_code']}"
        )

        keyboard = [
            [InlineKeyboardButton("Ver Tareas", callback_data="show_tasks")],
            [InlineKeyboardButton("Retirar", callback_data="withdraw")],
            [InlineKeyboardButton("Referir", callback_data="refer")],
        ]

        await update.message.reply_text(
            msg, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error dashboard: {e}", exc_info=True)
        await update.message.reply_text("Error cargando dashboard")


@error_handler
async def marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "MARKETPLACE\n\nCursos y servicios con comision:\n\n"

    keyboard: list[list[InlineKeyboardButton]] = []
    for key, platform in MARKETPLACE_PLATFORMS.items():
        msg += (
            f"{platform['name']}\n"
            f"Comision: {platform['commission']}%\n"
            f"{platform['description']}\n\n"
        )
        url = (
            f"{platform['url']}?ref={UDEMY_AFFILIATE}"
            if key == "udemy"
            else f"{platform['url']}?ref={FIVERR_AFFILIATE}"
        )
        keyboard.append([InlineKeyboardButton(platform["name"], url=url)])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


@error_handler
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db is None:
        await update.message.reply_text("Error BD")
        return
    try:
        async with db.execute(
            "SELECT referral_code FROM users WHERE id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            await update.message.reply_text("Usuario no encontrado")
            return
        ref_code = row["referral_code"]

        async with db.execute(
            "SELECT COUNT(*) AS c, COALESCE(SUM(commission_earned),0) AS t "
            "FROM referrals WHERE referrer_id = ?",
            (user_id,),
        ) as cur:
            stats = await cur.fetchone()
        refs_count = stats["c"]
        refs_total = stats["t"]

        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start={ref_code}"

        msg = (
            "PROGRAMA DE REFERIDOS\n\n"
            f"Tu codigo: {ref_code}\n"
            f"Tu link: {ref_link}\n\n"
            "ESTADISTICAS:\n"
            f"Referidos: {refs_count}\n"
            f"Comisiones: ${refs_total:.2f}\n\n"
            "GANANCIAS:\n"
            "$1.00 por registro\n"
            "15% de por vida\n\n"
            "5 amigos = $7.50/dia"
        )

        keyboard = [
            [InlineKeyboardButton("WhatsApp", url=f"https://wa.me/?text={ref_link}")],
            [InlineKeyboardButton("Telegram", url=f"https://t.me/share/url?url={ref_link}")],
        ]

        await update.message.reply_text(
            msg, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error refer: {e}", exc_info=True)
        await update.message.reply_text("Error cargando referidos")


@error_handler
async def config_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_or_create_user(user.id, user.first_name or "", user.username)
    if not user_data:
        await update.message.reply_text("Error")
        return

    country_config = COUNTRY_DATA.get(
        user_data["country"], COUNTRY_DATA["GLOBAL"]
    )

    msg = f"CONFIGURAR PAGO\n\nMetodos para {country_config['name']}:\n\n"

    keyboard: list[list[InlineKeyboardButton]] = []
    for method in country_config["methods"]:
        keyboard.append(
            [InlineKeyboardButton(method.upper(), callback_data=f"pay_{method}")]
        )

    await update.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard)
    )


@error_handler
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db is None:
        await update.message.reply_text("Error BD")
        return
    try:
        async with db.execute(
            "SELECT COUNT(*) AS c FROM users WHERE is_active = 1"
        ) as cur:
            u_row = await cur.fetchone()
        active_users = u_row["c"]

        async with db.execute(
            "SELECT COALESCE(SUM(total_earned),0) AS t FROM users"
        ) as cur:
            t_row = await cur.fetchone()
        total_paid = t_row["t"]

        async with db.execute(
            "SELECT COUNT(*) AS c FROM tasks_completed WHERE status = 'completed'"
        ) as cur:
            tc_row = await cur.fetchone()
        total_tasks = tc_row["c"]

        msg = (
            "ESTADISTICAS GLOBALES\n\n"
            f"Usuarios activos: {active_users}\n"
            f"Total pagado: ${total_paid:.2f}\n"
            f"Tareas completadas: {total_tasks}\n\n"
            "Pais TOP: Brasil\n"
            "Racha: 127 dias"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error stats: {e}", exc_info=True)
        await update.message.reply_text("Error cargando stats")


@error_handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_tasks":
        fake_update = Update(
            update.update_id, message=query.message  # type: ignore[arg-type]
        )
        await show_tasks(fake_update, context)
    elif query.data == "withdraw":
        await query.edit_message_text(
            "Configura tu metodo de pago primero usando Config Pagos"
        )
    elif query.data == "refer":
        fake_update = Update(
            update.update_id, message=query.message, effective_user=query.from_user
        )
        await refer(fake_update, context)
    elif query.data.startswith("pay_"):
        method = query.data.split("_", 1)[1]
        await query.edit_message_text(
            f"Configurando {method.upper()}\n\nEnvia tu email/ID:"
        )
    elif query.data == "cancel":
        await query.edit_message_text("Cancelado")


# ---------------------------------------------------------------------------
# QUART ROUTES
# ---------------------------------------------------------------------------


@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    try:
        data = await request.get_json()
        assert application is not None
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Error webhook: {e}", exc_info=True)
        return "error", 500


@app.route("/health")
async def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route("/")
async def index():
    return jsonify({"name": "GRIDDLED V3", "version": "3.0", "status": "active"}), 200


# ---------------------------------------------------------------------------
# STARTUP / SHUTDOWN
# ---------------------------------------------------------------------------


@app.before_serving
async def startup():
    global application, http_session

    logger.info("Iniciando GRIDDLED V3 (SQLite)...")

    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no configurado")

    if not await init_db():
        raise RuntimeError("Error inicializando BD")

    http_session = aiohttp.ClientSession()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("tareas", show_tasks))
    application.add_handler(CommandHandler("marketplace", marketplace))
    application.add_handler(CommandHandler("referir", refer))
    application.add_handler(CommandHandler("configurar", config_payments))
    application.add_handler(CommandHandler("stats", stats))

    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^Ver Tareas$"), show_tasks)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^Dashboard$"), dashboard)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^Marketplace$"), marketplace)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^Referir$"), refer)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^Config Pagos$"), config_payments)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^Stats$"), stats)
    )

    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), handle_task_num)
    )

    application.add_handler(CallbackQueryHandler(task_done, pattern=r"^done_"))
    application.add_handler(CallbackQueryHandler(handle_callback))

    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    await application.start()

    logger.info("Bot iniciado correctamente")


@app.after_serving
async def shutdown():
    global application, http_session, db

    logger.info("Cerrando bot...")

    if http_session:
        await http_session.close()
    if application:
        await application.stop()
        await application.shutdown()
    if db:
        await db.close()

    logger.info("Bot cerrado correctamente")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
