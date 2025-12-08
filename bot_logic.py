# ... (Mantén tus imports y código anterior) ...
from database import db_pool # Asegúrate de tener este import arriba

async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """COMANDO DE DESARROLLO: Borra tu cuenta para probar el registro desde cero"""
    user = update.effective_user
    if not db_pool: 
        await update.message.reply_text("❌ Error: Base de datos no conectada.")
        return

    async with db_pool.acquire() as conn:
        # Borramos todo rastro tuyo
        await conn.execute("DELETE FROM users WHERE telegram_id=$1", user.id)
        await conn.execute("DELETE FROM leads_harvest WHERE telegram_id=$1", user.id)
        await conn.execute("DELETE FROM transactions WHERE user_id=$1", user.id)
        
        # Limpiamos caché de Redis si existe
        from database import redis_client
        if redis_client:
            await redis_client.delete(f"user:{user.id}")

    await update.message.reply_text(
        "🔄 **CUENTA DE FÁBRICA RESTAURADA**\n\n"
        "El sistema ya no te conoce.\n"
        "Escribe **/start** para simular ser un usuario nuevo (te pedirá Email y API)."
    )
