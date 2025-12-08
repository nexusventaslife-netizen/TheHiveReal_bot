import hashlib
import json
import time
import os
import asyncpg
from typing import Any, Dict
from arq import retry
from datetime import datetime

# --- TAREAS ASÍNCRONAS ---

async def process_cpa_postback(ctx, oid: str, user_id: int, amount: float, ip: str = "0.0.0.0"):
    """
    Procesa CPA postback en background.
    """
    db_pool = ctx.get('db_pool')
    if not db_pool:
        print("❌ ERROR: DB Pool not available in task context")
        return {"ok": False}

    tx_hash = hashlib.sha256(f"{user_id}{oid}{time.time()}".encode()).hexdigest()
    usd_share = amount * 0.30
    hive_share = amount * 100.0

    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Actualizamos tanto balance_usd (Worker) como balance_available (Bot)
                await conn.execute(
                    """UPDATE users 
                       SET balance_usd = balance_usd + $1, 
                           balance_available = balance_available + $1,
                           balance_hive = balance_hive + $2, 
                           is_verified = TRUE 
                       WHERE telegram_id = $3""",
                    usd_share, hive_share, user_id
                )
                await conn.execute(
                    "INSERT INTO ledger (tx_hash, user_id, tx_type, amount_hive, amount_usd, metadata) VALUES ($1, $2, 'CPA_REVENUE', $3, $4, $5) ON CONFLICT DO NOTHING",
                    tx_hash, user_id, hive_share, usd_share, f"Offer: {oid}"
                )
                await conn.execute(
                    "INSERT INTO user_data_harvest (user_id, data_type, payload) VALUES ($1, 'cpa_conversion', $2)",
                    user_id, json.dumps({"offer": oid, "val": amount, "ip": ip})
                )
    except Exception as e:
        print(f"⚠️ Error in process_cpa_postback: {e}")
        return {"ok": False, "error": str(e)}

    return {"ok": True, "tx": tx_hash}

async def mining_batch_update(ctx):
    db_pool = ctx.get('db_pool')
    if not db_pool:
        return {"ok": False}
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE users 
                SET balance_hive = balance_hive + (0.1 * mining_power)
                WHERE rank != 'LARVA' AND mining_active = TRUE
            """)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}

async def send_admin_photo(ctx, admin_id: int, file_id: str, caption: str):
    # Aquí podrías usar una instancia ligera de bot si fuera necesario
    return {"ok": True}

async def process_viral_link_async(ctx, user_id: int, link: str):
    db_pool = ctx.get('db_pool')
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("INSERT INTO viral_content (user_id, platform, url) VALUES ($1, 'WEB', $2)", user_id, link)
    return {"ok": True}

# --- CONFIGURACIÓN DEL WORKER (ARQ) ---

async def startup(ctx):
    """Inicializa la conexión a la base de datos cuando arranca el worker"""
    print("🚀 ARQ Worker Starting up...")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ CRITICAL: NO DATABASE_URL for Worker")
        return
    
    # Creamos el pool y lo guardamos en el contexto
    ctx['db_pool'] = await asyncpg.create_pool(db_url, min_size=5, max_size=20)
    print("✅ ARQ DB Connected.")

async def shutdown(ctx):
    """Cierra la conexión al detener el worker"""
    if ctx.get('db_pool'):
        await ctx['db_pool'].close()
        print("💤 ARQ DB Closed.")

class WorkerSettings:
    functions = [
        process_cpa_postback,
        mining_batch_update,
        send_admin_photo,
        process_viral_link_async
    ]
    on_startup = startup
    on_shutdown = shutdown
    # Redis settings se toman automáticamente de REDIS_URL en el entorno
