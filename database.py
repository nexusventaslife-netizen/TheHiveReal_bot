# ... (MANTÉN TODO LO QUE YA TIENES ARRIBA) ...

# --- AGREGA ESTA FUNCIÓN AL FINAL ---
async def update_email(user_id, email):
    """Guarda el email del usuario en la base de datos."""
    if not pool: return False
    try:
        async with pool.acquire() as conn:
            # Actualizamos el campo email del usuario
            await conn.execute("UPDATE users SET email = $1 WHERE user_id = $2", email, user_id)
            return True
    except Exception as e:
        logger.error(f"Error guardando email: {e}")
        return False

async def get_user(user_id):
    """Obtiene los datos del usuario para saber si ya tiene mail."""
    if not pool: return None
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    except Exception:
        return None
