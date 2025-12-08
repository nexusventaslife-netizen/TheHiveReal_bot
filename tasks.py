# tasks.py
# Tareas para arq (worker basado en Redis).
# Para ejecutar: `arq tasks.WorkerSettings` (ver README)

import hashlib
import json
import time
from typing import Any, Dict
from arq import retry
from datetime import datetime

# Nota: arq espera funciones async exportadas en el módulo, o una clase WorkerSettings que las liste.
# Ejemplos de tareas:

async def process_cpa_postback(ctx, oid: str, user_id: int, amount: float, ip: str = "0.0.0.0"):
    """
    Procesa CPA postback en background: actualiza balances, guarda ledger y user_data_harvest.
    ctx['db_pool'] esperada (si la inyectas) o crea una conexión.
    """
    db_pool = ctx.get('db_pool')
    tx_hash = hashlib.sha256(f"{user_id}{oid}{time.time()}".encode()).hexdigest()
    usd_share = amount * 0.30
    hive_share = amount * 100.0

    if db_pool:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE users SET balance_usd = balance_usd + $1, balance_hive = balance_hive + $2, is_verified = TRUE WHERE telegram_id = $3",
                    usd_share, hive_share, user_id
                )
                await conn.execute(
                    "INSERT INTO ledger (tx_hash, user_id, tx_type, amount_hive, amount_usd, metadata) VALUES ($1, $2, 'CPA_REVENUE', $3, $4, $5)",
                    tx_hash, user_id, hive_share, usd_share, f"Offer: {oid}"
                )
                await conn.execute(
                    "INSERT INTO user_data_harvest (user_id, data_type, payload) VALUES ($1, 'cpa_conversion', $2)",
                    user_id, json.dumps({"offer": oid, "val": amount, "ip": ip})
                )
    return {"ok": True, "tx": tx_hash}

async def mining_batch_update(ctx):
    """
    Ejemplo de batch process: incrementar balances en lotes.
    """
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
    """
    Tarea para enviar foto al admin por el bot — si tienes un contexto con bot token.
    El worker puede crear un telegram.Bot y enviar la foto.
    """
    # implementación mínima: devolver ok. Si quieres puedo añadir código para crear telegram.Bot y enviar.
    return {"ok": True}

async def process_viral_link_async(ctx, user_id: int, link: str):
    db_pool = ctx.get('db_pool')
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute("INSERT INTO viral_content (user_id, platform, url) VALUES ($1, 'WEB', $2)", user_id, link)
    return {"ok": True}

# WorkerSettings para arq (si ejecutas 'arq tasks.WorkerSettings' este será usado)
class WorkerSettings:
    functions = [
        "process_cpa_postback",
        "mining_batch_update",
        "send_admin_photo",
        "process_viral_link_async"
    ]
    # Puedes definir redis_settings, on_startup, on_shutdown aquí si lo deseas.
    # Al ejecutar arq, toma REDIS_URL desde environment.
