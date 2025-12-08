# main.py
# Versión refactor con Redis (cache), arq (enqueue) y webhook para telegram.
# Integra fastapi-limiter para rate limiting (usa Redis).

import os
import logging
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

import asyncpg
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis
from arq import create_pool as arq_create_pool
from telegram import Update
from telegram.ext import Application

# Importar utilidades de cache y tareas
from cache import init_cache, cache_get_user, cache_set_user, cache_invalidate_user, cache_get_p2p_offers, cache_invalidate_p2p, key_for_user
import tasks  # tareas para arq (asegúrate de que tasks.py exista)

# Variables de entorno
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATA_BUYER_KEY = os.environ.get("DATA_BUYER_KEY", "hive_master_key_v1")

logger = logging.getLogger("Hive.Enterprise")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="TheOneHive Titan API - Redis Enabled", version="5.1.0")

# Globals
db_pool: Optional[asyncpg.Pool] = None
redis: Optional[Redis] = None
arq_pool = None
telegram_app: Optional[Application] = None

# --- Middleware de métricas simple
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    # push latency to redis list for simple metrics
    try:
        if redis:
            await redis.lpush("metrics:latency", f"{datetime.utcnow().isoformat()}|{process_time:.6f}")
            # limit list length
            await redis.ltrim("metrics:latency", 0, 999)
    except Exception:
        pass
    return response

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "OPERATIONAL", "load": "NORMAL", "timestamp": datetime.utcnow().isoformat()})

# --- Endpoint protegido y cacheado: export_leads (rate limited)
@app.get("/api/v1/export_leads")
async def export_leads_secure(key: str, min_rank: str = None, country: str = None, _=Depends(RateLimiter(times=5, seconds=60))):
    if key != DATA_BUYER_KEY:
        raise HTTPException(status_code=403, detail="ACCESS_DENIED")
    if not db_pool:
        raise HTTPException(status_code=503, detail="DB_UNAVAILABLE")
    # Intentar cache (por ejemplo con filtros)
    cache_key = f"export_leads:{min_rank or 'any'}:{country or 'any'}"
    try:
        raw = None
        if redis:
            raw = await redis.get(cache_key)
            if raw:
                return {"data": json.loads(raw), "cached": True}
        async with db_pool.acquire() as conn:
            query = "SELECT telegram_id, first_name, email, rank, country_code, balance_usd FROM users WHERE email IS NOT NULL"
            rows = await conn.fetch(query)
            data = [dict(r) for r in rows]
            if redis:
                await redis.set(cache_key, json.dumps(data), ex=30)  # TTL corto por seguridad
            return {"data": data}
    except Exception as e:
        logger.error(f"Data Export Error: {e}")
        raise HTTPException(500, "Internal Error")

# --- POSTBACK CPA HANDLER (enqueue job en vez de hacer todo inline)
@app.get("/postback/nectar")
async def nectar_postback_handler(oid: str, user_id: int, amount: float, signature: str, ip: str = "0.0.0.0", _=Depends(RateLimiter(times=20, seconds=60))):
    logger.info(f"CPA Postback queued: User={user_id}, Amount=${amount}")
    # Encolar job a arq
    if arq_pool:
        try:
            await arq_pool.enqueue_job("process_cpa_postback", oid, user_id, amount, ip)
            # invalidar cache de usuario para que la siguiente lectura venga de DB
            try:
                await cache_invalidate_user(user_id)
            except Exception:
                pass
            return "1"
        except Exception as e:
            logger.error(f"Failed enqueue job: {e}")
            raise HTTPException(500, "Enqueue Failed")
    # Fallback directo (si arq no disponible): intenta operación ligera
    raise HTTPException(503, "QUEUE_UNAVAILABLE")

# --------------------------------------------
# Helpers para el bot: rate-limit por usuario
# --------------------------------------------
def bot_rate_limit(limit: int = 30, window: int = 60):
    """
    Decorator para handlers: limita a `limit` acciones por `window` segundos.
    Usa Redis INCR con expiración.
    """
    def decorator(func):
        async def wrapper(update, context, *args, **kwargs):
            try:
                uid = update.effective_user.id
                key = f"ratelimit:bot:{uid}"
                if redis:
                    cur = await redis.incr(key)
                    if cur == 1:
                        await redis.expire(key, window)
                    if cur > limit:
                        # responder al usuario amablemente
                        try:
                            await update.message.reply_text("⚠️ Demasiadas solicitudes. Intenta de nuevo en un minuto.")
                        except Exception:
                            pass
                        return
            except Exception:
                # si falla redis, no bloquear al usuario
                pass
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

# -------------------------
# Telegram webhook endpoint
# -------------------------
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if not telegram_app:
        raise HTTPException(503, "BOT_UNINITIALIZED")
    body = await request.json()
    # Crear Update desde JSON y procesarlo
    try:
        update = Update.de_json(body, telegram_app.bot)
        # Procesar update en la app (no bloqueante)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
    return {"ok": True}

# -------------------------
# Startup / Shutdown hooks
# -------------------------
@app.on_event("startup")
async def startup():
    global db_pool, redis, arq_pool, telegram_app
    logger.info("🚀 STARTUP: Iniciando servicios (DB, Redis, Arq, Bot, RateLimiter)...")

    # DB pool
    if DATABASE_URL:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=50)
    else:
        logger.warning("DATABASE_URL no configurada. Modo stateless.")

    # Redis client
    if REDIS_URL:
        redis = Redis.from_url(REDIS_URL, decode_responses=True)
        await init_cache(redis)  # inicializa cache module
        # fastapi-limiter init
        try:
            await FastAPILimiter.init(redis)
        except Exception as e:
            logger.warning(f"fastapi-limiter init falla: {e}")
    else:
        logger.warning("REDIS_URL no configurada. Cache deshabilitado.")

    # arq pool (client) para encolar jobs
    if REDIS_URL:
        try:
            arq_pool = await arq_create_pool(REDIS_URL)
            # inyectar db_pool en ctx si es posible (depende de arq settings)
            if hasattr(arq_pool, "ctx"):
                arq_pool.ctx = arq_pool.ctx or {}
                arq_pool.ctx['db_pool'] = db_pool
        except Exception as e:
            logger.error(f"arq pool error: {e}")
            arq_pool = None

    # Inicializar telegram app -> usar webhooks
    if TELEGRAM_TOKEN:
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        # Aquí debes registrar tus handlers del bot (start_handler, handlers de callback, etc.)
        # Ejemplo: telegram_app.add_handler(CommandHandler("start", start_handler))
        await telegram_app.initialize()
        await telegram_app.start()
    else:
        logger.warning("TELEGRAM_TOKEN no configurado; bot deshabilitado.")

    # Lanzar tareas de minería periódicas en background -> encolar jobs periódicos
    async def schedule_mining():
        while True:
            try:
                if arq_pool:
                    await arq_pool.enqueue_job("mining_batch_update")
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"schedule_mining error: {e}")
                await asyncio.sleep(10)

    asyncio.create_task(schedule_mining())
    logger.info("✅ Startup completado.")

@app.on_event("shutdown")
async def shutdown():
    global db_pool, redis, arq_pool, telegram_app
    logger.info("🛑 SHUTDOWN: cerrando servicios...")
    try:
        if telegram_app:
            await telegram_app.stop()
            await telegram_app.shutdown()
    except Exception:
        pass
    if db_pool:
        await db_pool.close()
    if redis:
        await redis.close()
    if arq_pool:
        try:
            await arq_pool.close()
        except Exception:
            pass
