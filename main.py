# main.py - CÓDIGO SEGURO Y COMPLETO PARA RAILWAY
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
import logging
import sqlite3

# 1. CONFIGURACIÓN DE SEGURIDAD (¡SE LEE DESDE RAILWAY!)
# El bot lee TUS 4 valores secretos desde Railway, no desde el código.
TOKEN = os.environ.get('TELEGRAM_TOKEN') 
HG_CODE = os.environ.get('HONEYGAIN_CODE')
PA_CODE = os.environ.get('PAWNS_CODE')
SB_CODE = os.environ.get('SWAGBUCKS_CODE')

if not TOKEN or not HG_CODE or not PA_CODE or not SB_CODE:
    raise ValueError("ERROR FATAL: Una o más variables (TOKEN, códigos de APP) no se configuraron en Railway.")

# 2. CONFIGURACIÓN DE APPS
# Se construye el link de forma segura con los valores secretos.
APPS = {
    'honeygain': f'https://r.app/honeygain/{HG_CODE}',  
    'pawns': f'https://pawns.app/r/{PA_CODE}',  
    'swagbucks': f'https://www.swagbucks.com/?r={SB_CODE}'  
}

# Configuración de Logging
logging.basicConfig(level=logging.INFO)

# Base de datos (SQLite)
conn = sqlite3.connect('referrals.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, referrals INTEGER DEFAULT 0, points INTEGER DEFAULT 0, lang TEXT DEFAULT 'es')''')
conn.commit()

# Idiomas y Funciones... (el cuerpo del bot)
LANG = {
    'es': {'welcome': '¡Bienvenido al Referral Hive! Gana pasivo con apps. Usa /refer para tu link.',
           'choose': 'Elige app para referral link:',
           'your_link': 'Tu link referral al bot: {link}\nReferrals: {refs}\n¡Por cada referral, +1 punto!'}
}

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    cursor.execute('INSERT OR IGNORE INTO users (id, lang) VALUES (?, "es")', (user_id,))
    conn.commit()
    texts = LANG['es']
    keyboard = [[InlineKeyboardButton("Obtener Referrals", callback_data='get_refs')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(texts['welcome'], reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    texts = LANG['es']
    
    if query.data == 'get_refs':
        text = texts['choose']
        keyboard = [[InlineKeyboardButton(app.capitalize(), callback_data=app)] for app in APPS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    
    elif query.data in APPS:
        link = APPS[query.data]
        await query.edit_message_text(f'Aquí está tu link para {query.data}: {link}')

async def refer(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    cursor.execute('SELECT referrals FROM users WHERE id = ?', (user_id,))
    refs = cursor.fetchone()[0] if cursor.fetchone() else 0
    bot_link = f'https://t.me/{context.bot.username}?start={user_id}' 
    await update.message.reply_text(LANG['es']['your_link'].format(link=bot_link, refs=refs))

async def handle_start_with_ref(update: Update, context: CallbackContext) -> None:
    if context.args:
        try:
            ref_id = int(context.args[0])
            cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE id = ?', (ref_id,))
            conn.commit()
        except Exception:
            pass 
    await start(update, context)

# --- Función Principal ---

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    
    # Añade los Handlers
    app.add_handler(CommandHandler('start', handle_start_with_ref))
    app.add_handler(CommandHandler('refer', refer))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot iniciado. Conectando con Telegram...")
    app.run_polling() 

if __name__ == '__main__':
    main()
