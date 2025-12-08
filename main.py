import os
import hashlib
import logging
from fastapi import FastAPI, Request, BackgroundTasks
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update

from database import init_db, process_secure_postback
from bot_logic import start_command, menu_handler, check_gate_callback, mine_tap_callback, withdraw_callback

# CONFIGURACIÓN SEGURA
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
CPA_SECRET_KEY = os.environ.get("CPA_SECRET", "mi_secreto_super_seguro_123") # CRÍTICO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Hive.Main")

app = FastAPI()
telegram_app = None

@app.on_event("startup")
async def startup():
    global telegram_app
    await init_db(DATABASE_URL)
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # HANDLERS
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CallbackQueryHandler(check_gate_callback, pattern="check_gate"))
    telegram_app.add_handler(CallbackQueryHandler(mine_tap_callback, pattern="mine_tap"))
    telegram_app.add_handler(CallbackQueryHandler(withdraw_callback, pattern="try_withdraw"))
    telegram_app.add_handler(MessageHandler(filters.TEXT, menu_handler))
    
    await telegram_app.initialize()
    await telegram_app.start()
    
    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

@app.post("/webhook")
async def webhook(request: Request):
    """Entrada de alta velocidad para Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}

# --- ENDPOINT SEGURO DE POSTBACK (AUDITORÍA RED TEAM SOLUCIONADA) ---
@app.get("/postback/secure")
async def secure_postback(uid: int, amount: float, network: str, sig: str):
    """
    Recibe pagos de OfferToro/CPAGrip.
    Verifica firma MD5 para evitar inyección de saldo falso.
    """
    # 1. Recrear firma localmente: md5(uid + amount + SECRET)
    base_str = f"{uid}{amount}{CPA_SECRET_KEY}"
    local_sig = hashlib.md5(base_str.encode()).hexdigest()
    
    # 2. Verificar
    if local_sig != sig:
        logger.warning(f"🚨 HACK ATTEMPT: User {uid} tried fake postback.")
        return {"error": "Invalid Signature"}
    
    # 3. Procesar Dinero (Con Hold de 7 días si es necesario)
    result = await process_secure_postback(uid, amount, network)
    
    # 4. Notificar al usuario (Background Task idealmente)
    try:
        msg = f"💰 **PAGO RECIBIDO: ${amount}**\n"
        if result['status'] == 'ON_HOLD':
            msg += "⚠️ **EN REVISIÓN:** Este pago es alto, estará disponible en 7 días."
        else:
            msg += f"✅ **ACREDITADO:** ${result['user_share']:.2f} añadidos a tu saldo."
        
        await telegram_app.bot.send_message(chat_id=uid, text=msg)
    except: pass
    
    return {"status": "OK", "details": result}
