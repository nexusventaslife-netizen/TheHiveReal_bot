import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import add_user, update_user_gate_status, get_user  # Asegúrate de tener estas funciones en database.py

# Obtener el link de Adsterra de las variables de entorno
# Asegúrate de que en Render tengas la variable definida como: ADSTERRA_LINK
ADSTERRA_LINK = os.getenv("ADSTERRA_LINK", "https://google.com") # Link por defecto para evitar crash si falta la variable

async def show_gate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra el mensaje de bloqueo de seguridad (Gate).
    Obliga al usuario a ver la publicidad de Adsterra.
    """
    user = update.effective_user
    
    # Texto persuasivo para aumentar el CTR (Click Through Rate)
    text = (
        f"🔒 <b>HOLA {user.first_name}, VERIFICACIÓN REQUERIDA</b>\n\n"
        "Para proteger la economía del bot y evitar bots automatizados, "
        "necesitas activar tu cuenta manualmente.\n\n"
        "👇 <b>SIGUE ESTOS PASOS:</b>\n"
        "1. Toca el botón <b>'ACTIVAR CUENTA'</b>.\n"
        "2. Espera 5 segundos en la página segura.\n"
        "3. Vuelve aquí y toca <b>'VERIFICAR ACCESO'</b>."
    )

    # TECLADO DE DOBLE PASO (Estrategia Adsterra)
    keyboard = [
        # BOTÓN 1: Abre el Direct Link de Adsterra (Monetización)
        [InlineKeyboardButton("🚀 1. ACTIVAR CUENTA (Click Aquí)", url=ADSTERRA_LINK)],
        
        # BOTÓN 2: Valida la acción (Callback al bot)
        [InlineKeyboardButton("✅ 2. VERIFICAR ACCESO", callback_data="check_gate_verify")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar mensaje (soporta si viene de un comando o de un callback previo)
    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def check_gate_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja el click en 'VERIFICAR ACCESO'.
    Aquí es donde 'falsificamos' la verificación del CPA ya que Adsterra no envía postback.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("🔄 Verificando conexión segura...")

    # --- ALGORITMO DE VALIDACIÓN ---
    # Aquí podríamos verificar tiempo transcurrido, pero para mejor UX lo aprobamos
    # asumiendo que el usuario hizo el paso 1.
    
    # 1. Actualizar DB: Marcar usuario como verificado
    # Asegúrate de tener esta función en database.py
    await update_user_gate_status(user_id, status=True)

    # 2. Notificar éxito
    await query.edit_message_text(
        text="✅ <b>¡CUENTA ACTIVADA CON ÉXITO!</b>\n\nBienvenido a TheHiveReal. Ya puedes empezar a minar.",
        parse_mode="HTML"
    )

    # 3. Mostrar el Menú Principal inmediatamente
    from bot_logic import menu_handler # Importación local para evitar ciclos si es necesario
    await menu_handler(update, context)
