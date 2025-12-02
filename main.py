# -*- coding: utf-8 -*-
# TheOneHive Telegram Bot - Sistema de Ganancia Hiper-Escalable y Cero Fricción
# Diseñado para generar ingresos por 7 vías: Afiliación, Suscripción, Marketplace, y Datos.

# IMPORTACIONES NECESARIAS
import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Importaciones de Firebase
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone

# --- CONFIGURACIÓN CRÍTICA DEL BOT ---

# Nivel de logging para ver errores y actividad
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Cargar variables de entorno (CRÍTICAS PARA EL DINERO Y SEGURIDAD)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")  # Tu ID numérico de Telegram
ADMIN_CONTACT_URL = os.environ.get("ADMIN_CONTACT_URL") # Tu URL de contacto para pagos
MARKETPLACE_LINK = os.environ.get("MARKETPLACE_LINK") # Tu enlace de afiliado al Marketplace

# Enlaces de Afiliación (CRÍTICAS PARA EL MOTOR DE INGRESO)
HONEYGAIN_CODE = os.environ.get("HONEYGAIN_CODE", "DEFAULT_HG_CODE")
PAWNS_CODE = os.environ.get("PAWNS_CODE", "DEFAULT_PAWNS_CODE")
HIVE_MICRO_LINK = os.environ.get("HIVE_MICRO_LINK", "http://default-hive-micro.com")
PEER2PROFIT_LINK = os.environ.get("PEER2PROFIT_LINK", "http://default-peer2profit.com")
COINBASE_EARN_LINK = os.environ.get("COINBASE_EARN_LINK", "http://default-coinbase-earn.com")

# Precio de la Suscripción GOLD
PREMIUM_PRICE = "15.00 USD/mes"

# Inicializar Firebase
if FIREBASE_CREDENTIALS:
    try:
        # La clave de servicio debe estar en formato JSON de una sola línea
        cred_json = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase inicializado correctamente.")
    except Exception as e:
        logger.error(f"Error al inicializar Firebase: {e}")
        db = None
else:
    logger.error("FIREBASE_CREDENTIALS no está configurada. El bot no podrá guardar datos.")
    db = None

# --- CONSTANTES Y UTILIDADES ---

# Tasa Base de Ganancia y Multiplicadores
BASE_CLICKS_VALUE = 0.05  # Valor base proyectado en USD por "clic" de actividad
GOLD_MULTIPLIER = 3.0    # El potencial de ganancias del usuario GOLD (3x el FREE)
FREE_MULTIPLIER = 1.2    # Multiplicador base para usuarios FREE

# Colección de Usuarios
USERS_COLLECTION = 'theonehive_users'

# --- MODELO DE DATOS DE USUARIO EN FIRESTORE ---
# user_data = {
#     'user_id': int,
#     'username': str,
#     'is_premium': bool,
#     'tokens_hve': int,
#     'total_clicks': int,
#     'daily_clicks': int,
#     'last_check_in': datetime,
#     'check_in_streak': int,
#     'consents_to_ads': bool,  # Vía de Ingreso 4: Monetización de Datos
#     'referred_by': int,       # Vía de Ingreso 5: Ganancia por Referido
# }

# Función para obtener la hora actual de UTC-3 (Punta del Este)
def get_now():
    utc_minus_3 = timezone(timedelta(hours=-3))
    return datetime.now(utc_minus_3)

# Función para obtener o crear el perfil del usuario
async def get_or_create_user(user_id, username, ref_id=None):
    if not db:
        return None
    user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
    doc = user_ref.get()

    if doc.exists:
        user_data = doc.to_dict()
        # Verificar y resetear daily_clicks y racha si el día cambió
        last_check_in = user_data.get('last_check_in')
        if last_check_in and (get_now() - last_check_in).days >= 1:
            user_data['daily_clicks'] = 0
            user_data['last_check_in'] = get_now()
            user_ref.set(user_data, merge=True)
        return user_data
    else:
        # Crear nuevo usuario
        new_data = {
            'user_id': user_id,
            'username': username,
            'is_premium': False,
            'tokens_hve': 5,
            'total_clicks': 0,
            'daily_clicks': 0,
            'last_check_in': get_now(),
            'check_in_streak': 0,
            'consents_to_ads': False,
            'referred_by': ref_id, # Si viene de un referido (Vía 5)
        }
        user_ref.set(new_data)

        # Si hay un referente, darle un bono (Vía 5)
        if ref_id and str(ref_id) != str(user_id):
            ref_ref = db.collection(USERS_COLLECTION).document(str(ref_id))
            ref_data = ref_ref.get().to_dict()
            if ref_data:
                ref_ref.update({
                    'tokens_hve': ref_data.get('tokens_hve', 0) + 50,
                    'referred_count': ref_data.get('referred_count', 0) + 1
                })
                # No se notifica al referente para simplificar, el bono aparece en stats
        return new_data

# Función para registrar actividad del usuario
async def register_click(user_id, user_data, is_check_in=False):
    if not db:
        return

    tokens_earned = 1
    # Multiplicador del token para GOLD (Vía 2)
    if user_data.get('is_premium'):
        tokens_earned *= 2

    # Lógica de Racha Diaria (Vía 5: Adicción)
    current_time = get_now()
    last_check_in = user_data.get('last_check_in')

    streak = user_data.get('check_in_streak', 0)

    # Si es el primer click del día O es un check-in
    if is_check_in or (current_time - last_check_in).days >= 1:
        # Si el usuario NO perdió la racha, la incrementa
        if (current_time - last_check_in).days == 1:
            streak += 1
            tokens_earned += streak * 5  # Bono por Racha
            message = f"✅ ¡Racha de {streak} días! Ganaste un bono de {streak * 5} HVE Tokens."
        # Si la racha se rompió, la resetea
        elif (current_time - last_check_in).days > 1:
            streak = 1
            message = "⚠️ ¡Racha reiniciada! Empieza tu racha de nuevo."
        else: # Primer click del día, pero hoy mismo
             message = ""

        # Actualizar datos de check-in
        user_data['daily_clicks'] = 1
        user_data['last_check_in'] = current_time
        user_data['check_in_streak'] = streak

    # Actualizar solo si es un click normal (no check-in repetido)
    elif not is_check_in:
        user_data['daily_clicks'] += 1
        message = ""


    # Actualizar datos generales
    user_data['total_clicks'] = user_data.get('total_clicks', 0) + 1
    user_data['tokens_hve'] = user_data.get('tokens_hve', 0) + tokens_earned

    db.collection(USERS_COLLECTION).document(str(user_id)).set(user_data)

    return tokens_earned, message

# --- COMANDOS PRINCIPALES ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ref_id = context.args[0] if context.args else None # Vía 5: Referido
    user_data = await get_or_create_user(user.id, user.username, ref_id)

    if not user_data:
        await update.message.reply_text("Error al conectar con la base de datos. Por favor, inténtalo más tarde.")
        return

    # Teclado con el menú principal (Vía 2: Premium, Vía 3: Marketplace, Vía 6: Viral)
    keyboard = [
        [InlineKeyboardButton("🔗 5 Vías de Ingreso", callback_data='links')],
        [InlineKeyboardButton("📈 Mis Estadísticas (APD V2)", callback_data='stats')],
        [InlineKeyboardButton("🚀 Reto Viral (Gana HVE Tokens)", callback_data='video_viral')],
        [InlineKeyboardButton("🛒 Marketplace GOLD (Cursos/Libros)", callback_data='marketplace')],
        [InlineKeyboardButton("👑 GOLD Premium ($15 USD)", callback_data='premium')],
        [InlineKeyboardButton("🔒 Privacidad y Datos (Bono HVE)", callback_data='privacidad')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        f"👋 **¡Hola, {user.first_name}! Bienvenido a TheOneHive.**\n\n"
        "Somos el 'Booster' global para que ganes ingresos pasivos y activos. "
        "Tu misión es simple: maximiza tu actividad y sube tu Racha Diaria.\n\n"
        "**Tu Status Actual:** {'👑 GOLD' if user_data.get('is_premium') else '🆓 FREE'}\n"
        "**Tokens HVE:** {user_data.get('tokens_hve', 0)}\n\n"
        "Selecciona una opción abajo para empezar a generar ingresos.",
        reply_markup=reply_markup
    )

async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Vía de Ingreso 1: Afiliación a las 5 plataformas
    user = update.effective_user
    user_data = await get_or_create_user(user.id, user.username)

    tokens_earned, check_in_message = await register_click(user.id, user_data, is_check_in=True)

    message = (
        f"{check_in_message}\n"
        "🔗 **PASO 1: REGISTRA TUS 5 VÍAS DE INGRESO**\n\n"
        "Cada registro te da una fuente de ingreso residual de por vida.\n\n"
        "**1. Ingreso Pasivo (Datos):** \n"
        f"   - **Honeygain:** Código: `{HONEYGAIN_CODE}`\n"
        f"   - **Pawns App:** Código: `{PAWNS_CODE}`\n"
        f"   - **Peer2Profit:** Enlace: [Regístrate Aquí]({PEER2PROFIT_LINK})\n\n"
        "**2. Ingreso Activo (Tareas/Crypto):**\n"
        f"   - **Hive Micro:** Enlace: [Regístrate Aquí]({HIVE_MICRO_LINK})\n"
        f"   - **Coinbase Earn:** Enlace: [Regístrate Aquí]({COINBASE_EARN_LINK})\n\n"
        "**¡Importante!** Debes registrarte en cada una de ellas para activar tu potencial completo. Cada click aquí suma a tu Racha Diaria."
    )
    await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver al Menú", callback_data='start_menu')]]))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Vía 3: Algoritmo de Proyección Dinámica (APD V2) y Vía 7: Adicción
    user = update.effective_user
    user_data = await get_or_create_user(user.id, user.username)

    is_premium = user_data.get('is_premium', False)
    daily_clicks = user_data.get('daily_clicks', 0)
    streak = user_data.get('check_in_streak', 0)
    
    # 1. Tasa de Proyección APD
    # Usuario GOLD usa un multiplicador mayor (3.0x) para justificar el precio
    # Usuario FREE usa un multiplicador base (1.2x)
    multiplier = GOLD_MULTIPLIER if is_premium else FREE_MULTIPLIER
    
    # Ganancia Proyectada: Clicks * Valor Base * Multiplicador
    projected_today = daily_clicks * BASE_CLICKS_VALUE * multiplier
    projected_month = projected_today * 30

    # 2. Proyección de Optimización (Gancho)
    # Si el usuario es más rápido/trabaja más (ej: 50% más clicks)
    optimized_clicks = daily_clicks * 1.5
    optimized_multiplier = 2.5 if is_premium else 1.5 # GOLD tiene un mejor potencial de mejora
    
    potential_increase = (optimized_clicks * BASE_CLICKS_VALUE * optimized_multiplier) - projected_today

    status_str = '👑 GOLD' if is_premium else '🆓 FREE'
    
    # Base de referidos (Vía 5)
    referred_count = user_data.get('referred_count', 0)
    
    message = (
        f"📈 **TU PANEL DE RENDIMIENTO**\n"
        f"-------------------------------\n"
        f"**Status:** {status_str}\n"
        f"**Racha Diaria (Streak):** {streak} días\n"
        f"**Clicks de Actividad Hoy:** {daily_clicks}\n"
        f"**Tokens HVE Balance:** {user_data.get('tokens_hve', 0)}\n\n"
        
        f"**💸 PROYECCIÓN DE GANANCIA (APD V2) 💸**\n"
        f"*(Basado en tu esfuerzo de hoy y tu tasa de conversión)*\n"
        f"**Ganancia Proyectada HOY:** **{projected_today:.2f} USD**\n"
        f"**Ganancia Proyectada MES:** **{projected_month:.2f} USD**\n\n"
        
        f"🚀 **POTENCIAL DE OPTIMIZACIÓN**\n"
        f"Si optimizas tu tiempo de respuesta y dedicas más horas, puedes proyectar una ganancia adicional de:\n"
        f"**+{potential_increase:.2f} USD por día**\n"
        f"*(¡Mejora tu velocidad de respuesta!)*\n\n"
        
        f"**🤝 Bucle Viral (Vía 5):**\n"
        f"Referidos ganados: {referred_count}\n"
        f"Tu enlace de invitación: `/start {user.id}`"
    )

    await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver al Menú", callback_data='start_menu')]]))


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Vía 2: Suscripción de Alto Margen ($15 USD)
    user = update.effective_user
    user_data = await get_or_create_user(user.id, user.username)
    
    status_str = '👑 GOLD' if user_data.get('is_premium', False) else '🆓 FREE'
    
    if user_data.get('is_premium'):
        message = (
            f"👑 **¡YA ERES GOLD!**\n\n"
            f"Disfrutas de:\n"
            f"✅ Acelerador HVE x2\n"
            f"✅ Acceso a 3 Vías de Ingreso Élite\n"
            f"✅ Análisis de Velocidad (HVA Insight)\n"
            f"✅ Soporte Prioritario VIP\n\n"
            f"**Tu clave de acceso:** {user.id}"
        )
    else:
        message = (
            f"👑 **MEJORA A GOLD PREMIUM**\n\n"
            f"**PRECIO:** **{PREMIUM_PRICE}**\n\n"
            f"¿Por qué pagar {PREMIUM_PRICE}? Porque el estatus GOLD es la única manera de acelerar tu potencial de ganancia y alcanzar el objetivo de ingresos dignos.\n\n"
            f"**BENEFICIOS EXCLUSIVOS:**\n"
            f"⚡ **Acelerador HVE x2:** Gana el doble de Tokens para canjes y bonos.\n"
            f"💎 **Acceso a 3 Vías de Élite:** Plataformas de micro-tareas y encuestas más estables y mejor remuneradas.\n"
            f"📈 **Potencial APD 2.5x:** Desbloquea el multiplicador de potencial de ganancia en tus estadísticas.\n"
            f"🆘 **Soporte Prioritario VIP:** Resuelve tus dudas rápidamente.\n\n"
            f"**PROCESO DE PAGO:**\n"
            f"1. Haz clic en el botón de contacto.\n"
            f"2. Paga la suscripción de {PREMIUM_PRICE} por el método acordado.\n"
            f"3. Te activaremos el acceso GOLD con tu ID: `{user.id}`."
        )
        
    keyboard = [[InlineKeyboardButton("📞 Contáctame para Pagar", url=ADMIN_CONTACT_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def marketplace_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Vía 3: Marketplace de Alto Margen
    await register_click(update.effective_user.id, await get_or_create_user(update.effective_user.id, update.effective_user.username))

    message = (
        "🛒 **MARKETPLACE DE OPTIMIZACIÓN**\n\n"
        "Si quieres alcanzar el Potencial Máximo que ves en tus estadísticas, ¡necesitas optimizar tu trabajo!\n\n"
        "Aquí encontrarás los mejores cursos y libros sobre:\n"
        "📚 Cursos de Freelancing de Alto Valor.\n"
        "⏱️ Técnicas de respuesta rápida para Encuestas.\n"
        "💰 Estrategias avanzadas de Ingreso Pasivo.\n\n"
        "**¡Gana más invirtiendo en conocimiento!**"
    )
    keyboard = [
        [InlineKeyboardButton("🔗 Acceder al Marketplace (Comisiones para mí)", url=MARKETPLACE_LINK)],
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data='start_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def video_viral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Vía 6: Bucle Viral Obligatorio (UGC)
    await register_click(update.effective_user.id, await get_or_create_user(update.effective_user.id, update.effective_user.username))
    
    message = (
        "🚀 **RETO VIRAL (GANANCIA GRATUITA DE TOKENS)**\n\n"
        "Queremos ser la plataforma más grande. Ayúdanos a crecer y gana HVE Tokens extra!\n\n"
        "**¿CÓMO FUNCIONA?**\n"
        "1. Crea un video en TikTok, Instagram Reels o YouTube Shorts mostrando tu **Racha Diaria** o tu **Proyección de Ganancia** en el bot.\n"
        "2. Usa el hashtag **#TheOneHiveApp**.\n"
        "3. Envíanos el enlace por mensaje privado a [Contáctame Aquí]({ADMIN_CONTACT_URL}).\n\n"
        "**BONO:** Por cada video aprobado, ganas **100 HVE Tokens** (Vía de Ingreso 5). ¡Máximo tráfico gratuito para nosotros!"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data='start_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def privacidad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Vía 4: Monetización de Datos (Legal)
    user = update.effective_user
    user_data = await get_or_create_user(user.id, user.username)
    
    consent_status = "✅ ACEPTADO" if user_data.get('consents_to_ads') else "❌ NO ACEPTADO"

    message = (
        "🔒 **POLÍTICA DE PRIVACIDAD Y DATOS**\n\n"
        "Para mantener nuestro servicio gratuito, podemos compartir patrones de uso anónimos con terceros (NUNCA tu nombre, ID o datos personales).\n\n"
        "**Status Actual:** {consent_status}\n\n"
        "Si **Aceptas**, nos permites generar ingresos pasivos adicionales (Vía 4) y a cambio, obtienes un **BONO ÚNICO de 25 HVE Tokens**."
    )
    
    keyboard = []
    if not user_data.get('consents_to_ads'):
        keyboard.append([InlineKeyboardButton("✔️ Aceptar y Recibir Bono (25 HVE Tokens)", callback_data='consent_accept')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Menú", callback_data='start_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def consent_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_ref = db.collection(USERS_COLLECTION).document(str(user.id))
    user_data = user_ref.get().to_dict()

    if not user_data.get('consents_to_ads'):
        user_data['consents_to_ads'] = True
        user_data['tokens_hve'] = user_data.get('tokens_hve', 0) + 25
        user_ref.set(user_data, merge=True)
        
        await update.callback_query.answer("✅ ¡Bono de 25 HVE Tokens recibido!", show_alert=True)
        message = f"🔒 **¡GRACIAS!** Has aceptado. Tienes un bono de 25 HVE Tokens. Tu nuevo balance: {user_data['tokens_hve']}."
    else:
        message = "Ya habías aceptado el consentimiento de datos."
        
    keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data='start_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)


async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Comando de Administrador (Vía 2: Activación de Suscripción)
    user = update.effective_user
    
    # 1. Seguridad: Solo el administrador puede usar este comando
    if str(user.id) != str(ADMIN_USER_ID):
        await update.message.reply_text("⛔ Acceso denegado. Este comando es solo para administradores.")
        return

    # 2. Sintaxis: Espera el ID del usuario a actualizar
    if not context.args:
        await update.message.reply_text("Uso: /upgrade [ID_DEL_USUARIO]. Ejemplo: /upgrade 123456789")
        return

    target_user_id = context.args[0]
    
    # 3. Ejecución: Actualizar Firebase
    try:
        target_user_ref = db.collection(USERS_COLLECTION).document(target_user_id)
        target_user_ref.update({'is_premium': True})
        
        await update.message.reply_text(f"✅ Usuario {target_user_id} ha sido actualizado a PREMIUM GOLD. ¡Dinero en la cuenta!")
        
    except Exception as e:
        logger.error(f"Error al actualizar usuario: {e}")
        await update.message.reply_text(f"❌ Error al actualizar al usuario {target_user_id}. Verifica el ID y el estado de la base de datos.")


async def start_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Manejador para volver al menú principal
    await start_command(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Redirigir a los comandos según el callback_data
    if query.data == 'start_menu':
        await start_menu_callback(update, context)
    elif query.data == 'links':
        await links_command(update, context)
    elif query.data == 'stats':
        await stats_command(update, context)
    elif query.data == 'premium':
        await premium_command(update, context)
    elif query.data == 'marketplace':
        await marketplace_command(update, context)
    elif query.data == 'video_viral':
        await video_viral_command(update, context)
    elif query.data == 'privacidad':
        await privacidad_command(update, context)
    elif query.data == 'consent_accept':
        await consent_accept_callback(update, context)


def main():
    """Iniciar el bot."""
    if not TELEGRAM_TOKEN or not db:
        logger.error("No se puede iniciar el bot. Falta TELEGRAM_TOKEN o la conexión a Firebase falló.")
        return

    # Crear la aplicación y pasarle el token del bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Manejadores de Comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("upgrade", upgrade_command))

    # Manejadores de Botones (callback)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Iniciar el bot (polling)
    logger.info("Bot iniciado. Escuchando...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
