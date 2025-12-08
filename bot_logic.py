# ... tus otras funciones (start_command, process_email_input, etc.) ...
from telegram import Update
from telegram.ext import ContextTypes
from database import db_pool, redis_client

# Esta función reemplaza la que tenías, con los imports correctos dentro del archivo
async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """COMANDO DE DESARROLLO: Borra tu cuenta para probar el registro desde cero"""
    user = update.effective_user
    if not db_pool: 
        await update.message.reply_text("❌ Error: Base de datos no conectada.")
        return

    try:
        async with db_pool.acquire() as conn:
            # Borramos todo rastro tuyo
            await conn.execute("DELETE FROM users WHERE telegram_id=$1", user.id)
            await conn.execute("DELETE FROM leads_harvest WHERE telegram_id=$1", user.id)
            await conn.execute("DELETE FROM transactions WHERE user_id=$1", user.id)
            # Limpieza extra para las nuevas tablas
            await conn.execute("DELETE FROM ledger WHERE user_id=$1", user.id)
            
            # Limpiamos caché de Redis si existe
            if redis_client:
                await redis_client.delete(f"user:{user.id}")

        await update.message.reply_text(
            "🔄 **CUENTA DE FÁBRICA RESTAURADA**\n\n"
            "El sistema ya no te conoce.\n"
            "Escribe **/start** para simular ser un usuario nuevo (te pedirá Email y API)."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error al resetear: {e}")
