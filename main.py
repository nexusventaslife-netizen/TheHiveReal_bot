import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import bot_logic
import database as db
import os

# Configuración de Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_handlers(app):
    """Configura todos los handlers de comandos, texto y callbacks."""
    # Comandos
    app.add_handler(CommandHandler("start", bot_logic.start))
    app.add_handler(CommandHandler("help", bot_logic.help_command))
    app.add_handler(CommandHandler("invite", bot_logic.invite_command))
    app.add_handler(CommandHandler("reset", bot_logic.reset_command))
    app.add_handler(CommandHandler("broadcast", bot_logic.broadcast_command))

    # Handlers de Mensajes de Texto (para captcha, email y comandos admin)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_logic.general_text_handler))

    # Handlers de Botones (Callbacks)
    app.add_handler(CallbackQueryHandler(bot_logic.button_handler))

def main():
    """Inicia el bot."""
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN no configurado. Asegúrate de definirlo en las variables de entorno.")
        return

    # Inicializar la base de datos (conecta Redis)
    # Ejecutamos init_db de forma síncrona/esperamos en el bloque principal si el entorno lo permite
    # o usamos asyncio.run() para rodear todo si es necesario.
    import asyncio
    asyncio.run(db.init_db())
    
    # Crear la aplicación y conectar el token
    application = Application.builder().token(BOT_TOKEN).build()

    # Configurar handlers
    setup_handlers(application)
    
    # Iniciar el bot (modo polling - ideal para desarrollo)
    logger.info("🚀 Bot iniciado. Esperando mensajes...")
    application.run_polling(poll_interval=1.0)

if __name__ == '__main__':
    main()
