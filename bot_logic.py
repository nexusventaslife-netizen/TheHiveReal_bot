import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
# Asegúrate de importar tus funciones de DB existentes
from database import add_user, update_user_email, get_user, add_lead

# --- CONFIGURACIÓN DE MONETIZACIÓN (EL "ALGORITMO") ---
# Aquí defines tus fuentes de ingresos.
# WEIGHT: Probabilidad de que aparezca (suma total no necesita ser 100, es peso relativo).

MONETIZATION_SOURCES = [
    {
        "name": "high_ticket_crypto",
        "url": "https://accounts.binance.com/register?ref=TU_REF_ID", # Tu link de referido de Binance/ByBit
        "weight": 20, # 20% de probabilidad (Paga $5-$50 si convierten)
        "label": "VERIFICAR CUENTA (Opción Rápida)"
    },
    {
        "name": "adsterra_direct_link",
        "url": "https://tu-direct-link.com/...", # Tu Direct Link de Adsterra/Monetag (Aprueban YA)
        "weight": 70, # 70% de probabilidad (Paga centavos pero SIEMPRE funciona)
        "label": "ACTIVAR ACCESO AHORA"
    },
    {
        "name": "cpa_fallback",
        "url": "https://www.cpagrip.com/...", # Tu link antiguo por si acaso
        "weight": 10,
        "label": "VERIFICACIÓN SEGURA"
    }
]

def get_smart_monetization_link():
    """
    Algoritmo de selección ponderada.
    Elige un enlace basado en los pesos definidos para balancear
    ganancias altas (difíciles) vs ganancias bajas (seguras).
    """
    choices = [source for source in MONETIZATION_SOURCES]
    weights = [source['weight'] for source in choices]
    
    selected = random.choices(choices, weights=weights, k=1)[0]
    return selected

# --- TUS HANDLERS EXISTENTES MODIFICADOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Lógica de bienvenida...
    await update.message.reply_text(
        f"👋 Hola {user.first_name}! Bienvenido a TheHiveReal.\n\n"
        "🔒 Para proteger la economía del bot, necesitamos validar que eres humano.\n"
        "📧 Por favor, **envíame tu correo electrónico** para continuar."
    )
    # Establecer estado esperando email (si usas ConversationHandler) o simplemente esperar el mensaje
    context.user_data['waiting_for_email'] = True

async def process_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (Tu validación de email y guardado en DB aquí) ...
    
    email = update.message.text
    user_id = update.effective_user.id
    
    # Supongamos que guardaste el email exitosamente
    # await add_lead(user_id, email) 
    
    # AQUI ESTA EL CAMBIO CLAVE:
    offer = get_smart_monetization_link()
    
    keyboard = [
        [InlineKeyboardButton(f"🔓 {offer['label']}", url=offer['url'])],
        [InlineKeyboardButton("✅ YA COMPLETÉ EL PASO", callback_data="check_gate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Email registrado.\n\n"
        "🚨 **ÚLTIMO PASO DE SEGURIDAD** 🚨\n"
        "Nuestro sistema detecta tráfico inusual. Para activar tu billetera y empezar a minar, "
        "haz clic en el botón de abajo y sigue las instrucciones (puede ser ver un anuncio o registrarte).\n\n"
        "⚠️ *Si no completas este paso, el menú no se abrirá.*",
        reply_markup=reply_markup
    )

async def check_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Aquí puedes implementar una lógica de "falso tiempo de espera"
    # para obligar al usuario a estar en la página al menos 15 segundos.
    
    # Por ahora, simulamos éxito y pasamos al menú principal
    await menu_handler(update, context)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tu menú principal existente...
    pass
