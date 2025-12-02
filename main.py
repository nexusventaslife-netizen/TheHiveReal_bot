import os 
import logging
import asyncio
from http import HTTPStatus
from quart import Quart, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
import psycopg2.pool
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_fixed
from web3 import Web3
import json 
from typing import Optional

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Variables Globales ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
DATABASE_URL = os.environ.get('DATABASE_URL') 
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://the-hivereal-bot.onrender.com')

# --- Constantes del Programa ---
REFERRAL_BONUS_HVE = 5 # Token HVE de recompensa para el referidor
INITIAL_HVE_FOR_NEW_USER = 5 # Tokens HVE iniciales para el nuevo usuario

# Costo y Multiplicador de la Suscripción GOLD (Pilar 3)
GOLD_SUBSCRIPTION_COST = 50 
GOLD_MULTIPLIER = 2.0 

# Tasa de comisión de The Hive Real (Ejemplo: 10% del total convertido a HVE)
HIVE_COMMISSION_RATE = 0.10 

# --- Instancias Globales ---
W3: Optional[Web3] = None 
connection_pool = None
application: Optional[Application] = None 
app = Quart(__name__) 

# --- Configuración Específica de Plataformas de Ingreso ---
PLATFORM_CONFIG = {
    "Clickworker": {
        "description": "Plataforma de micro-tareas de alto volumen (data entry, validación).",
        "currency": "CW-PTS",
        "conversion_rate_to_hve": 500 # 500 CW-PTS = 1 HVE
    },
    "Wise (Referidos)": {
        "description": "Bono por referir nuevos usuarios al servicio de transferencias internacionales.",
        "currency": "WISE-BONUS",
        "conversion_rate_to_hve": 0.1 # 1 WISE-BONUS (simulando 10 USD) = 10 HVE. Usamos 0.1 HVE per unit for clarity in display.
    }
}
# --- Funciones de Conexión y Setup ---

def setup_db_pool():
    """Configura el pool de conexiones a PostgreSQL."""
    global connection_pool
    if not DATABASE_URL:
        logger.error("ERROR FATAL: DATABASE_URL no está configurada.")
        return False
    try:
        # Asegura la sintaxis correcta para psycopg2
        connection_string = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            connection_string
        )
        logger.info("✅ Pool de Conexiones a PostgreSQL configurado exitosamente.")
        return True
    except Exception as e:
        logger.error(f"❌ ERROR FATAL DE CONEXIÓN DB: {e}")
        return False

def get_db_conn():
    """Obtiene una conexión del pool."""
    if connection_pool:
        try:
            return connection_pool.getconn()
        except Exception as e:
            logger.error(f"Error al obtener conexión del pool: {e}")
            return None
    return None

def put_db_conn(conn):
    """Devuelve una conexión al pool."""
    if connection_pool and conn:
        connection_pool.putconn(conn)

def init_db():
    """Inicializa la base de datos y crea el esquema y la data económica."""
    if not setup_db_pool():
        return False
    
    conn = get_db_conn()
    if conn is None:
        logger.error("ERROR DB: No se pudo obtener conexión para crear esquema.")
        return False
    
    try:
        with conn.cursor() as cur:
            # 1. Crear tabla de Usuarios (users)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    first_name VARCHAR(255),
                    username VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'FREE',
                    tokens_hve INTEGER DEFAULT 5,
                    wallet_address VARCHAR(42),
                    country VARCHAR(50) DEFAULT 'Global', 
                    effort_hours FLOAT DEFAULT 0,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Asegurar que todas las columnas existen
            cur.execute("""
                DO $$ BEGIN
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS platform_data JSONB DEFAULT '{}';
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS metrics_data JSONB DEFAULT '{}';
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by_id BIGINT;
                END $$;
            """)

            # 2. Crear tabla de Datos Económicos (economic_data) para la Proyección (F1)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS economic_data (
                    country VARCHAR(50) PRIMARY KEY,
                    min_wage FLOAT NOT NULL,
                    cost_of_living_index FLOAT NOT NULL
                );
            """)

            # 3. Insertar datos económicos de simulación (si no existen)
            # min_wage: Salario mínimo por hora (USD/hr simulado)
            # cost_of_living_index: Índice de costo de vida (ej: 100 = Nueva York)
            mock_econ_data = [
                ('Mexico', 1.5, 30.0),
                ('Colombia', 1.8, 35.0),
                ('Argentina', 1.2, 40.0),
                ('Spain', 7.5, 60.0),
                ('Global', 5.0, 50.0) # Default para usuarios sin país
            ]
            for country, min_wage, col_index in mock_econ_data:
                 cur.execute("""
                    INSERT INTO economic_data (country, min_wage, cost_of_living_index) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (country) DO NOTHING;
                 """, (country, min_wage, col_index))
            
        conn.commit()
        logger.info("✅ Base de datos PostgreSQL inicializada. Esquema y datos económicos verificados.")
        return True
    except Exception as e:
        logger.error(f"❌ ERROR al inicializar DB: {e}")
        conn.rollback()
        return False
    finally:
        put_db_conn(conn)

# --- Lógica de Negocio y Utilidades ---

def get_econ_data(country: str, conn) -> tuple[float, float]:
    """
    (F1) Obtiene el salario mínimo por hora y el índice de costo de vida del país.
    Si el país no existe, usa el valor 'Global'.
    """
    if conn is None:
        return 5.0, 50.0 # Valores por defecto en caso de fallo de DB

    country_to_fetch = country if country else 'Global'
    
    try:
        with conn.cursor() as cur:
            # Primero intenta con el país específico
            cur.execute(
                "SELECT min_wage, cost_of_living_index FROM economic_data WHERE country = %s;",
                (country_to_fetch,)
            )
            data = cur.fetchone()

            if data:
                return data

            # Si el país no está, intenta con 'Global'
            if country_to_fetch != 'Global':
                 cur.execute(
                    "SELECT min_wage, cost_of_living_index FROM economic_data WHERE country = 'Global';"
                 )
                 data_global = cur.fetchone()
                 if data_global:
                     return data_global
            
            # Fallback si ni 'Global' existe
            return 5.0, 50.0 

    except Exception as e:
        logger.error(f"Error al obtener datos económicos para {country}: {e}")
        return 5.0, 50.0 # Fallback
        
def calc_max_earnings(min_wage, effort_hours, cost_living):
    """Calcula proyección de ingresos USD simulada."""
    # Simulación de fórmula de proyección de ingreso máximo diario
    base = min_wage * effort_hours
    # Ajuste: Penalización del 20% del potencial de base ajustado por el costo de vida
    adjusted = base - (cost_living / 100 * base * 0.2) 
    return max(0, round(adjusted, 2))

def get_eth_balance(address: str):
    """Obtiene saldo nativo de una wallet (simulado)."""
    return "0.0000"

def format_platform_balances(platform_data: dict) -> str:
    """Formatea los tokens de las plataformas en una cadena legible."""
    if not platform_data:
        return "— Sin ganancias registradas en plataformas."
    
    text = []
    for platform, data in platform_data.items():
        tokens = data.get('tokens', 0)
        currency = PLATFORM_CONFIG.get(platform, {}).get('currency', 'PTS')
        hve_conversion = data.get('hve_conversion', 0)
        
        text.append(f"• **{platform}**: {tokens:.2f} {currency} (≈ {hve_conversion:.2f} HVE)")
    
    return "\n".join(text)

# --- Handlers de Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler del comando /start e inicializa la lógica de referidos y muestra info."""
    user = update.effective_user
    user_id = user.id
    is_admin = str(user_id) == ADMIN_USER_ID
    conn = get_db_conn()
    wallet = "N/A"
    platform_data = {}
    metrics_data = {} 
    user_status = 'FREE'
    country = 'Global' # Valor inicial
    hours = 0
    tokens = INITIAL_HVE_FOR_NEW_USER
    
    referrer_id = None
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
    
    referrer_rewarded = False
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tokens_hve, is_admin, country, effort_hours, wallet_address, platform_data, metrics_data, referred_by_id, status FROM users WHERE id = %s;",
                    (user_id,)
                )
                user_data = cur.fetchone()
                
                if user_data is None:
                    # --- NUEVO USUARIO ---
                    wallet = "0x" + os.urandom(20).hex()
                    
                    # Datos simulados de ganancias iniciales
                    initial_cw_pts = 5000.0 
                    initial_wise_bonus = 3.0
                    
                    platform_data = {
                        "Clickworker": {
                            "tokens": initial_cw_pts, 
                            "hve_conversion": initial_cw_pts / PLATFORM_CONFIG["Clickworker"]["conversion_rate_to_hve"]
                        },
                        "Wise (Referidos)": {
                            "tokens": initial_wise_bonus, 
                            "hve_conversion": initial_wise_bonus / PLATFORM_CONFIG["Wise (Referidos)"]["conversion_rate_to_hve"]
                        }
                    }
                    metrics_data = {
                        "weekly_hve_earned": 45.00,
                        "virality_tokens": 15.00,
                        "last_liquidation": "2025-12-01"
                    }
                    
                    cur.execute("""
                        INSERT INTO users (id, first_name, username, is_admin, wallet_address, platform_data, metrics_data, tokens_hve, referred_by_id, status) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (user_id, user.first_name, user.username, is_admin, wallet, json.dumps(platform_data), json.dumps(metrics_data), INITIAL_HVE_FOR_NEW_USER, referrer_id, user_status))
                    
                    if referrer_id and referrer_id != user_id:
                        cur.execute(
                            "UPDATE users SET tokens_hve = tokens_hve + %s WHERE id = %s RETURNING tokens_hve;",
                            (REFERRAL_BONUS_HVE, referrer_id)
                        )
                        if cur.rowcount > 0:
                            referrer_rewarded = True
                            try:
                                await context.bot.send_message(
                                    chat_id=referrer_id, 
                                    text=f"🎁 **¡Recompensa de Referido!**\n\nHas ganado **{REFERRAL_BONUS_HVE} HVE** porque **{user.first_name}** se unió a través de tu código.",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except Exception:
                                logger.warning(f"No se pudo notificar al referidor {referrer_id}.")
                                
                    conn.commit()
                else:
                    # --- USUARIO EXISTENTE ---
                    tokens, is_admin_db, country, hours, wallet, platform_data, metrics_data, existing_referrer_id, user_status = user_data
                    
                    platform_data = platform_data if platform_data else {}
                    metrics_data = metrics_data if metrics_data else {}
                    
                    # Actualizar nombre y username por si han cambiado
                    cur.execute(
                        "UPDATE users SET first_name = %s, username = %s WHERE id = %s;",
                        (user.first_name, user.username, user_id)
                    )
                    conn.commit()
                    
            # (F1) Obtener datos económicos dinámicamente
            min_wage, cost_living = get_econ_data(country, conn)
            max_daily = calc_max_earnings(min_wage, hours if hours > 0 else 4, cost_living)
        except Exception as e:
            logger.error(f"Error SQL en /start: {e}")
            max_daily = 5.00
        finally:
            put_db_conn(conn)
    else:
        max_daily = 5.00
        
    plataform_summary = format_platform_balances(platform_data)
    
    weekly_hve = metrics_data.get('weekly_hve_earned', 0.00)
    virality_tokens = metrics_data.get('virality_tokens', 0.00)
    
    # Texto de bienvenida adaptado al status
    status_emoji = "⭐ GOLD" if user_status == 'GOLD' else "🆓 FREE"
    multiplier_info = f" (Multiplicador Activo: {GOLD_MULTIPLIER}X)" if user_status == 'GOLD' else ""

    referral_message = ""
    if referrer_id and referrer_rewarded:
         referral_message = f"\n\n**🎉 ¡Bienvenido!** Fuiste referido. Tu mentor ganó {REFERRAL_BONUS_HVE} HVE."
    
    # Mensaje de configuración de país si es 'Global'
    country_setting_msg = ""
    if country == 'Global':
         country_setting_msg = "\n\n⚠️ **¡Configura tu país!** Usa `/set_country <nombre_país>` para una proyección más precisa."
    
    welcome_text = (
        f"¡Hola, {user.first_name}! ¡Bienvenido a The Hive Real!{referral_message}\n\n"
        f"**🏆 Tu Estado: {status_emoji}{multiplier_info}**\n"
        f"🌎 Tu País Actual: **{country}**\n"
        f"🔑 Tu Wallet (HVE/BSC): `{wallet}`\n"
        f"💰 Proyección Máx Diaria ({country}): **${max_daily:.2f} USD**\n\n"
        f"**Ganancias Externas (Vías de Ingreso):**\n{plataform_summary}\n"
        f"\n**Métricas Clave (Panel de Procesos):**\n"
        f"• HVE Semanal Estimado: {weekly_hve:.2f} HVE\n"
        f"• Tokens por Viralidad: {virality_tokens:.2f} HVE\n"
        f"{country_setting_msg}"
        "🚀 Usa /proyeccion para ver tu potencial de optimización."
    )
    
    keyboard = [
        ["5 Vías de Ingreso", "Mis Estadísticas"],
        ["Reto Viral", "Marketplace GOLD"],
        ["Mi Código de Referido", "GOLD Premium"], 
        ["/proyeccion", "/cashout", "/balance"]
    ]
    
    if is_admin:
        keyboard.append(["🛠️ Panel Admin"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    (F1) Permite al usuario configurar su país para obtener proyecciones más precisas.
    Uso: /set_country <nombre_país>
    """
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Uso: `/set_country <nombre_país>` (Ej: `/set_country Mexico`)\n"
            "Esto te permite obtener proyecciones de ganancias más precisas basadas en el costo de vida.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
        
    new_country = context.args[0].strip()
    
    if conn is None:
        await update.message.reply_text("❌ Error de conexión con la DB.")
        return

    try:
        # Verificar si el país (o su simulación) existe en la tabla económica
        with conn.cursor() as cur:
            # Intentamos buscar el país en la data mock
            cur.execute(
                "SELECT country FROM economic_data WHERE country ILIKE %s;",
                (new_country,)
            )
            data = cur.fetchone()
            
            country_to_save = data[0] if data else new_country # Guarda la versión capitalizada si existe, sino guarda la entrada del usuario.
            
            # Actualizar el país del usuario
            cur.execute(
                "UPDATE users SET country = %s WHERE id = %s RETURNING country;",
                (country_to_save, user_id)
            )
            
            if cur.rowcount > 0:
                conn.commit()
                if not data:
                    # Si no está en nuestra data simulada, usamos el valor Global como fallback.
                    await update.message.reply_text(
                        f"✅ País configurado como **{country_to_save}**.\n"
                        f"⚠️ Nota: No tenemos datos específicos para **{country_to_save}**, se está utilizando la proyección **Global** por defecto.", 
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        f"✅ País configurado exitosamente a **{country_to_save}**.\n"
                        f"Tu proyección de ganancias ha sido actualizada. Usa /proyeccion para verla.", 
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text("❌ Error: Usuario no encontrado.")
                
    except Exception as e:
        logger.error(f"Error en /set_country: {e}")
        conn.rollback()
        await update.message.reply_text("❌ Error interno de DB al actualizar el país.")
    finally:
        put_db_conn(conn)


async def upgrade_gold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /upgrade_gold. Implementa el Pilar 3: Suscripciones.
    Permite al usuario pasar de FREE a GOLD.
    """
    user_id = update.effective_user.id
    conn = get_db_conn()
    
    if conn is None:
        await update.message.reply_text("❌ Error de conexión con la DB.")
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tokens_hve, status FROM users WHERE id = %s;",
                (user_id,)
            )
            data = cur.fetchone()
            
            if not data:
                await update.message.reply_text("❌ Usuario no encontrado.")
                return

            current_hve, current_status = data

            if current_status == 'GOLD':
                await update.message.reply_text("🏆 ¡Ya eres un miembro **GOLD Premium**! Tienes activo el multiplicador de ganancias.", parse_mode=ParseMode.MARKDOWN)
                return

            if current_hve < GOLD_SUBSCRIPTION_COST:
                await update.message.reply_text(
                    f"❌ Saldo insuficiente. Necesitas **{GOLD_SUBSCRIPTION_COST} HVE** para la suscripción GOLD. Tu saldo actual es de **{current_hve} HVE**.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Realizar el Upgrade
            cur.execute(
                "UPDATE users SET tokens_hve = tokens_hve - %s, status = 'GOLD' WHERE id = %s;",
                (GOLD_SUBSCRIPTION_COST, user_id)
            )
            conn.commit()

            new_balance = current_hve - GOLD_SUBSCRIPTION_COST
            
            response = (
                f"🌟 **¡FELICIDADES! Eres GOLD Premium** 🌟\n\n"
                f"Se han descontado **{GOLD_SUBSCRIPTION_COST} HVE** de tu saldo.\n"
                f"Tu nuevo saldo es: **{new_balance} HVE**.\n\n"
                f"✅ **Multiplicador {GOLD_MULTIPLIER}X ACTIVADO.** Todas tus próximas ganancias netas por trabajo serán duplicadas."
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error en /upgrade_gold: {e}")
        conn.rollback()
        await update.message.reply_text(f"❌ Error interno de DB: {e}")
    finally:
        put_db_conn(conn)


async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando de Admin: /add_points <user_id> <platform_name> <amount>
    Simula la adición de puntos de una plataforma externa, aplica la comisión y el multiplicador GOLD.
    """
    user_id_admin = str(update.effective_user.id)
    if user_id_admin != ADMIN_USER_ID:
        await update.message.reply_text("❌ Acceso denegado. Solo para administradores.")
        return

    if len(context.args) != 3:
        await update.message.reply_text(
            "Uso: `/add_points <user_id> <platform_name> <amount>`\n"
            "Plataformas válidas: Clickworker, Wise (Referidos)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        target_id = int(context.args[0])
        platform_name = context.args[1]
        amount = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Error en el formato de User ID o Monto (debe ser numérico).")
        return

    if platform_name not in PLATFORM_CONFIG:
        await update.message.reply_text(
            f"❌ Plataforma '{platform_name}' no válida. Usa Clickworker o Wise (Referidos)."
        )
        return

    config = PLATFORM_CONFIG[platform_name]
    conn = get_db_conn()
    if conn is None:
        await update.message.reply_text("❌ Error de conexión con la DB.")
        return

    try:
        with conn.cursor() as cur:
            # 1. Obtener datos del usuario (incluyendo el status)
            cur.execute(
                "SELECT platform_data, status FROM users WHERE id = %s;",
                (target_id,)
            )
            data = cur.fetchone()
            if not data:
                await update.message.reply_text(f"❌ Usuario con ID {target_id} no encontrado.")
                return

            platform_data_db, user_status = data
            platform_data_db = platform_data_db if platform_data_db else {}
            
            # 2. Calcular Conversión a HVE y Comisión
            
            if config["conversion_rate_to_hve"] <= 0:
                 await update.message.reply_text(f"❌ Error de configuración: La tasa de conversión de {platform_name} es cero o negativa.")
                 return

            if config["conversion_rate_to_hve"] >= 1:
                hve_total = amount / config["conversion_rate_to_hve"]
            else:
                hve_total = amount / config["conversion_rate_to_hve"]
            
            # Aplicar la Comisión de The Hive Real
            commission = hve_total * HIVE_COMMISSION_RATE
            hve_neto_pre_multiplicador = hve_total - commission
            
            # 3. Aplicar Multiplicador GOLD (Pilar 3)
            multiplier = GOLD_MULTIPLIER if user_status == 'GOLD' else 1.0
            hve_final_para_usuario = hve_neto_pre_multiplicador * multiplier
            
            # 4. Actualizar datos de la plataforma y saldo
            if platform_name not in platform_data_db:
                platform_data_db[platform_name] = {"tokens": 0.0, "hve_conversion": 0.0}
            
            platform_data_db[platform_name]["tokens"] += amount
            platform_data_db[platform_name]["hve_conversion"] += hve_total # Conversion bruta para tracking
            
            cur.execute(
                "UPDATE users SET tokens_hve = tokens_hve + %s WHERE id = %s;",
                (int(hve_final_para_usuario), target_id)
            )
            conn.commit()

            # 5. Respuesta de confirmación
            multiplier_text = f"x{multiplier:.1f} (GOLD)" if user_status == 'GOLD' else "x1.0 (FREE)"
            response = (
                f"✅ **LIQUIDACIÓN Y COMISIÓN PROCESADA** (ID: {target_id})\n\n"
                f"Plataforma: **{platform_name}** | Estado: **{user_status}**\n"
                f"Puntos Añadidos: **{amount:.2f} {config['currency']}**\n\n"
                f"Generación Total HVE: {hve_total:.2f} HVE\n"
                f"Comisión The Hive Real ({int(HIVE_COMMISSION_RATE*100)}%): {commission:.2f} HVE\n"
                f"HVE Neto (Pre-Multiplicador): {hve_neto_pre_multiplicador:.2f} HVE\n"
                f"**Multiplicador Aplicado:** **{multiplier_text}**\n"
                f"HVE Final para el Usuario: **{hve_final_para_usuario:.2f} HVE**\n\n"
                f"El saldo de HVE del usuario ha sido actualizado."
            )
            await context.bot.send_message(
                chat_id=target_id, 
                text=f"💰 **¡Ganancia Acreditada!** Has recibido **{hve_final_para_usuario:.2f} HVE** de {platform_name}.",
                parse_mode=ParseMode.MARKDOWN
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error en /add_points: {e}")
        conn.rollback()
        await update.message.reply_text(f"❌ Error interno de DB: {e}")
    finally:
        put_db_conn(conn)


async def referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para generar el código de referido personal."""
    user_id = update.effective_user.id
    
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    response = (
        "🔗 **¡MULTIPLICA TUS GANANCIAS CON REFERIDOS!**\n\n"
        "Comparte este enlace único con tus amigos. Cuando se unan, tú ganas **5 HVE** al instante.\n\n"
        f"Tu Código de Referido Personal:\n"
        f"`{referral_link}`\n\n"
        "¡Mientras más amigos traigas a *The Hive Real*, más rápido crecen tus HVE!"
    )
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


async def proyeccion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    (F1) Handler de /proyeccion. Ahora usa datos económicos geo-localizados.
    """
    user_id = update.effective_user.id
    conn = get_db_conn()
    projection_text = "❌ Error: Conexión DB fallida."
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tokens_hve, effort_hours, metrics_data, status, country FROM users WHERE id = %s;",
                    (user_id,)
                )
                data = cur.fetchone()
                
                if data:
                    hve_tokens, effort_hours, metrics_data, user_status, country = data
                    weekly_hve = metrics_data.get('weekly_hve_earned', 0.00)
                    
                    # Obtener datos de proyección por país
                    min_wage, cost_living = get_econ_data(country, conn)
                    
                    multiplier = GOLD_MULTIPLIER if user_status == 'GOLD' else 1.0
                    
                    # Cálculo de la proyección diaria máxima en USD
                    max_daily_usd = calc_max_earnings(min_wage, effort_hours if effort_hours > 0 else 4, cost_living)
                    
                    optimized_hours = effort_hours * 1.1 if effort_hours > 0 else 4.4
                    optimized_hve = weekly_hve * 1.1 * multiplier if weekly_hve > 0 else 50.00 * 1.1 * multiplier
                    
                    status_emoji = "⭐ GOLD" if user_status == 'GOLD' else "🆓 FREE"
                    multiplier_text = f" (x{multiplier:.1f} ACTIVO)"
                    
                    # Mensaje de configuración de país si es 'Global'
                    country_setting_msg = ""
                    if country == 'Global':
                         country_setting_msg = "\n\n⚠️ **¡Usa /set_country!** Tu proyección se basa en datos Globales por defecto."

                    
                    projection_text = (
                        f"📈 **PANEL DE PROCESOS Y OPTIMIZACIÓN**\n"
                        f"**Estado:** {status_emoji}{multiplier_text}\n"
                        f"**País:** {country}\n\n"
                        f"**PROYECCIÓN MÁXIMA DIARIA:** **${max_daily_usd:.2f} USD**\n"
                        f"(Basado en Salario Mínimo de ${min_wage:.2f} USD/hr en {country})\n\n"
                        "Tu desempeño actual y potencial:\n"
                        f"• **Horas de Esfuerzo Actual:** {effort_hours:.2f}h\n"
                        f"• **HVE Semanal (Actual):** {weekly_hve:.2f} HVE\n\n"
                        "--- **PROYECCIÓN DE OPTIMIZACIÓN (10% de Mejora)** ---\n"
                        f"Si optimizas tus tiempos un 10%, lograrías:\n"
                        f"• **Horas de Esfuerzo Proyectadas:** {optimized_hours:.2f}h\n"
                        f"• **HVE Semanal Proyectado:** **{optimized_hve:.2f} HVE**\n"
                        f"{country_setting_msg}"
                    )
                else:
                    projection_text = "Usuario no encontrado. Usa /start primero."
        except Exception as e:
            logger.error(f"Error en /proyeccion: {e}")
            projection_text = "Error interno al consultar datos de proyección."
        finally:
            put_db_conn(conn)
            
    await update.message.reply_text(projection_text, parse_mode=ParseMode.MARKDOWN)

async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /cashout (Pilar 5 - Liquidación Diaria). PENDIENTE DE IMPLEMENTACIÓN DE LÓGICA."""
    response = (
        "💸 **LIQUIDACIÓN DIARIA SIN FRICCIÓN (Pilar 5 PENDIENTE)**\n\n"
        "Esta es la función principal. **Próximo a implementar.**\n"
        "• La función enviará tus tokens HVE a tu wallet BSC y reseteará tu saldo a cero."
    )
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /balance, ahora muestra HVE y tokens de plataformas."""
    user_id = update.effective_user.id
    conn = get_db_conn()
    response = "❌ Error: Conexión DB fallida."
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT wallet_address, tokens_hve, platform_data, metrics_data, status, country FROM users WHERE id = %s;",
                    (user_id,)
                )
                data = cur.fetchone()
                
                if data and data[0]:
                    wallet_address, hve_tokens, platform_data, metrics_data, user_status, country = data
                    eth_balance_str = get_eth_balance(wallet_address)
                    platform_data = platform_data if platform_data else {}
                    metrics_data = metrics_data if metrics_data else {}
                    
                    platform_balances = format_platform_balances(platform_data)
                    
                    virality_tokens = metrics_data.get('virality_tokens', 0.00)
                    
                    status_emoji = "⭐ GOLD" if user_status == 'GOLD' else "🆓 FREE"
                    multiplier_info = f" (Multiplicador Activo: {GOLD_MULTIPLIER}X)" if user_status == 'GOLD' else ""

                    response = (
                        f"💳 **SALDOS Y RECOMPENSAS**\n"
                        f"**Estado:** {status_emoji}{multiplier_info}\n"
                        f"**País:** {country}\n"
                        f"Dirección: `{wallet_address}`\n\n"
                        f"**1. Saldo Central (HVE/BSC)**\n"
                        f"  - **BNB/ETH (Gas):** {eth_balance_str}\n"
                        f"  - **HVE Tokens:** **{hve_tokens} HVE**\n\n"
                        f"**2. Ganancias en Plataformas**\n"
                        f"{platform_balances}\n"
                        f"• **Recompensa por Viralidad:** {virality_tokens:.2f} HVE (Pendiente de Reclamo)\n\n"
                        f"Usa **/claim_viral** para reclamar la recompensa de Viralidad. Usa **/cashout** para liquidar el saldo principal."
                    )
                else:
                    response = "Tu billetera no está registrada. Usa /start primero."
        except Exception as e:
            logger.error(f"Error en /balance: {e}")
            response = "Error interno al consultar datos."
        finally:
            put_db_conn(conn)
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para mensajes de texto."""
    text = update.message.text
    
    if text == "5 Vías de Ingreso":
        response = (
            "🚀 **LAS 5 VÍAS DE MONETIZACIÓN DE THE HIVE REAL**\n\n"
            "1. **Comisiones de Plataformas (Trabajo):** Fee por liquidación de ganancias externas (Ej: Clickworker, Wise).\n"
            "2. **Monetización de Datos Legales:** Ingresos por venta de datos anonimizados (el usuario recibe un bono de privacidad).\n"
            "3. **Virality & Contenido (Video):** Fee aplicado a los HVE tokens ganados por la creación de videos incentivados.\n"
            "4. **Suscripciones GOLD y NFTs:** Ingresos por membresías Premium y venta de colecciones de NFTs.\n"
            "5. **Tokenomics (HVE Mining):** El valor intrínseco y la circulación de nuestro token de utilidad (HVE)."
        )
    elif text == "Mis Estadísticas":
        response = "📊 **MIS ESTADÍSTICAS (PANEL DE PROCESOS)**\n\nPresiona **/proyeccion** para ver tu desempeño y tu potencial de optimización semanal."
    
    elif text == "Reto Viral":
        response = (
            "🎥 **RETO DE VIRALIDAD: GANA HVE CREANDO CONTENIDO**\n\n"
            "Genera y comparte videos sobre tu experiencia. Por cada hito de viralidad, el bot te recompensa con HVE tokens. Usa **/claim_viral** para solicitar la liquidación de este bono."
        )
    elif text == "Marketplace GOLD":
        response = "🏪 Accede al marketplace de activos digitales y cursos premium. **Pagos solo con HVE Tokens.**"
    elif text == "GOLD Premium":
        response = f"💎 **GOLD PREMIUM: Multiplicador {GOLD_MULTIPLIER}X (Pilar 3 ACTIVO)**\n\nPresiona **/upgrade_gold** para comprar la suscripción por **{GOLD_SUBSCRIPTION_COST} HVE** y duplicar tus ganancias netas."
    elif text == "Privacidad y Datos":
        response = "🔒 **PRIVACIDAD GARANTIZADA**\n\nUsamos tus datos de actividad solo de forma anonimizada y agregada para nuestro pilar de monetización. **Recibes un bono de HVE token mensual** por contribuir a la red."
    elif text == "Mi Código de Referido":
        await referral_code(update, context)
        return
    elif text == "🛠️ Panel Admin" and str(update.effective_user.id) == ADMIN_USER_ID:
         response = (
            "🛠️ **PANEL ADMIN**\n\n"
            "Comandos disponibles:\n"
            "• `/add_points <user_id> <platform> <amount>`: Simula liquidación y comisión + Multiplicador GOLD.\n"
            "• `/view_user <id>`: (PENDIENTE) Muestra datos completos del usuario."
        )
    else:
        response = f"Mensaje recibido: **{text}**. Presiona /start para ver las opciones principales."
        
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

# --- Configuración Quart (Web Server) ---

@app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
async def webhook_handler():
    """Procesa updates de Telegram vía webhook."""
    if request.method == "POST":
        try:
            json_data = await request.get_json()
            update = Update.de_json(json_data, application.bot)
            await application.process_update(update)
        except Exception as e:
            logger.error(f"❌ Error procesando update: {e}")
    return "ok", HTTPStatus.OK

@app.route('/health', methods=['GET'])
async def health_check():
    """Endpoint de health check."""
    return {"status": "ok", "service": "telegram-bot"}, HTTPStatus.OK

def setup_web3():
    """Simulación de inicialización de Web3, no requerida para la lógica actual de HVE."""
    pass

async def startup_bot():
    """Inicializa bot, DB, Web3 y configura webhook."""
    global application
    
    db_ok = init_db()
    setup_web3()
    
    if not TELEGRAM_TOKEN or not db_ok:
        logger.error("❌ El bot no puede iniciar. Revisa TELEGRAM_TOKEN o DB.")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("proyeccion", proyeccion))
    application.add_handler(CommandHandler("cashout", cashout))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("upgrade_gold", upgrade_gold))
    application.add_handler(CommandHandler("set_country", set_country)) # NUEVO COMANDO
    
    # Comando de Admin para inyectar ganancias
    application.add_handler(CommandHandler("add_points", add_points))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Mi Código de Referido$'), referral_code))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await application.initialize()
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}"
    
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ WebHook configurado: {webhook_url}")
        
        await application.start()
        logger.info("✅ Bot iniciado correctamente en modo webhook.")
        
    except Exception as e:
        logger.error(f"❌ ERROR CONFIGURANDO WEBHOOK: {e}")
        raise

async def shutdown_bot():
    """Cierra conexiones al detener el servicio."""
    global application
    if application:
        await application.stop()
        await application.shutdown()
    logger.info("🛑 Bot detenido correctamente.")

# Registrar funciones de inicio y cierre
app.before_serving(startup_bot)
app.after_serving(shutdown_bot)

if __name__ == "__main__":
    # Para desarrollo local
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
