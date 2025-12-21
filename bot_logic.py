import logging
import asyncio
import random
import time
import math
import os
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from loguru import logger
import database as db 
from email_validator import validate_email

# ==============================================================================
# 🐝 THE ONE HIVE: V10.0 (GLOBAL EMPIRE - REDIS EDITION)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CRYPTO_WALLET_USDT = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# --- IDENTIDAD VISUAL ---
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA (BITCOIN STRATEGY) ---
CONST = {
    "COSTO_POLEN": 10,        
    "RECOMPENSA_BASE": 0.05,
    "DECAY_OXIGENO": 4.0,     
    "COSTO_ENJAMBRE": 100,    
    "COSTO_RECARGA": 50,      
    "BONO_REFERIDO": 500,
    "PRECIO_ACELERADOR": 9.99,
    "TRIGGER_EMAIL_HONEY": 50
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA":      {"nivel": 0, "meta_hive": 0,       "max_energia": 200,  "bonus_tap": 1.0, "icono": "🐛", "acceso": 0},
    "OBRERO":     {"nivel": 1, "meta_hive": 1000,    "max_energia": 400,  "bonus_tap": 1.1, "icono": "🐝", "acceso": 1},
    "EXPLORADOR": {"nivel": 2, "meta_hive": 5000,    "max_energia": 800,  "bonus_tap": 1.2, "icono": "🔭", "acceso": 2},
    "GUARDIAN":   {"nivel": 3, "meta_hive": 20000,   "max_energia": 1500, "bonus_tap": 1.5, "icono": "🛡️", "acceso": 3},
    "REINA":      {"nivel": 4, "meta_hive": 100000,  "max_energia": 5000, "bonus_tap": 3.0, "icono": "👑", "acceso": 3}
}

# ==============================================================================
# 🌐 MOTOR DE TRADUCCIÓN (I18N ENGINE)
# ==============================================================================

TEXTS = {
    "es": {
        "intro_caption": "Bienvenido a The One Hive.\n\nNo es un juego. No es un airdrop.\nEs un sistema activo de extracción de valor.\n\nExplorá. El sistema se adapta.",
        "btn_enter": "👉 Entrar a la Colmena",
        "intro_step2": "La colmena no crece de golpe.\nCrece por constancia.\n\nAlgunos entran temprano.\nOtros llegan cuando ya está llena.",
        "btn_status": "👉 Ver mi estado",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NODO NO PROTEGIDO",
        "status_safe": "✅ NODO SEGURO",
        "lbl_energy": "⚡ Energía",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Feed:**",
        "footer_msg": "📝 _La emisión es limitada. El acceso es escaso._",
        "btn_mine": "⚡ MINAR (TAP)",
        "btn_tasks": "🟢 PANALES",
        "btn_rank": "🧬 EVOLUCIÓN",
        "btn_squad": "🐝 COLMENA",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ ESTABILIZAR ($)",
        "viral_1": "Esto no es un airdrop. Están midiendo influencia real. Entré antes del ajuste.\n\n{link}",
        "viral_2": "No debería compartir esto. El sistema busca nodos orgánicos. Asegura tu posición.\n\n{link}",
        "sys_event_1": "⚠️ Parámetro ajustado",
        "sys_event_2": "⏳ Ventana alfa activa",
        "sys_event_3": "🔒 Acceso reducido",
        "feed_action_1": "validó nodo",
        "feed_action_2": "sintetizó bloque",
        "lock_msg": "🔒 ACCESO DENEGADO. Nivel {lvl} requerido.",
        "protect_title": "⚠️ **ACCIÓN PROTEGIDA: {reason}**",
        "protect_body": "El sistema requiere validación para proteger tu progreso.\nCopia tu llave:",
        "email_prompt": "✅ Ingresa tu **EMAIL**:",
        "email_success": "✅ **NODO BLINDADO**",
        "shop_title": "🛡️ **ESTABILIZACIÓN (PREMIUM)**",
        "shop_body": "Protege tu nodo contra degradación y gana prioridad.",
        "btn_buy_prem": "🛡️ ESTABILIZAR NODO (${price})",
        "btn_buy_energy": "🔋 RECARGA ({cost} HIVE)",
        "pay_txt": "🛡️ **ACTIVAR**\n\nEnvía ${price} USDT (TRC20) a:\n`{wallet}`",
        "team_title": "👥 **EXPANSIÓN**",
        "team_body": "1 Ref = {bonus} Pts.\n\n🔗 `{link}`",
        "tasks_title": "📡 **ZONAS DE RECOLECCIÓN**",
        "tasks_body": "Selecciona el Panal según tu rango:\n\n🟢 **PANAL VERDE:** Nivel 0+\n🟡 **PANAL DORADO:** Explorador\n🔴 **PANAL ROJO:** Guardián",
        "btn_back": "🔙 VOLVER",
        "green_hive": "PANAL VERDE",
        "gold_hive": "PANAL DORADO",
        "red_hive": "PANAL ROJO",
        "squad_none_title": "⚠️ NODO AISLADO",
        "squad_none_body": "Un nodo aislado mina lento.\nForma una estructura para sobrevivir.",
        "btn_create_squad": "➕ FORMAR ({cost} HIVE)",
        "squad_active": "🐝 **ENJAMBRE ACTIVO**\n👥 Miembros: {members}\n🔥 Sinergia: ACTIVA",
        "no_balance": "❌ HIVE Insuficiente"
    },
    "en": {
        "intro_caption": "Welcome to The One Hive.\n\nNot a game. Not an airdrop.\nIt's an active value extraction system.\n\nExplore. The system adapts.",
        "btn_enter": "👉 Enter the Hive",
        "intro_step2": "The Hive grows by consistency, not spikes.\n\nSome enter early.\nOthers arrive when it's full.",
        "btn_status": "👉 Check Status",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ UNSECURED NODE",
        "status_safe": "✅ SECURE NODE",
        "lbl_energy": "⚡ Energy",
        "lbl_honey": "🍯 Nectar",
        "lbl_feed": "📊 **Live Feed:**",
        "footer_msg": "📝 _Emission is limited. Access is scarce._",
        "btn_mine": "⚡ MINE (TAP)",
        "btn_tasks": "🟢 HIVES",
        "btn_rank": "🧬 EVOLUTION",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 EXPAND",
        "btn_shop": "🛡️ STABILIZE ($)",
        "viral_1": "This is not an airdrop. They measure real influence. I got in before the adjustment.\n\n{link}",
        "viral_2": "I shouldn't share this. The system seeks organic nodes. Secure your spot.\n\n{link}",
        "sys_event_1": "⚠️ Parameter adjusted",
        "sys_event_2": "⏳ Alpha window active",
        "sys_event_3": "🔒 Access reduced",
        "feed_action_1": "validated node",
        "feed_action_2": "synthesized block",
        "lock_msg": "🔒 ACCESS DENIED. Level {lvl} required.",
        "protect_title": "⚠️ **PROTECTED ACTION: {reason}**",
        "protect_body": "System requires validation to secure your progress.\nCopy your key:",
        "email_prompt": "✅ Enter your **EMAIL**:",
        "email_success": "✅ **NODE ARMORED**",
        "shop_title": "🛡️ **STABILIZATION (PREMIUM)**",
        "shop_body": "Protect your node against degradation and gain priority.",
        "btn_buy_prem": "🛡️ STABILIZE NODE (${price})",
        "btn_buy_energy": "🔋 RECHARGE ({cost} HIVE)",
        "pay_txt": "🛡️ **ACTIVATE**\n\nSend ${price} USDT (TRC20) to:\n`{wallet}`",
        "team_title": "👥 **EXPANSION**",
        "team_body": "1 Ref = {bonus} Pts.\n\n🔗 `{link}`",
        "tasks_title": "📡 **COLLECTION ZONES**",
        "tasks_body": "Select Hive by rank:\n\n🟢 **GREEN HIVE:** Level 0+\n🟡 **GOLD HIVE:** Explorer\n🔴 **RED HIVE:** Guardian",
        "btn_back": "🔙 BACK",
        "green_hive": "GREEN HIVE",
        "gold_hive": "GOLD HIVE",
        "red_hive": "RED HIVE",
        "squad_none_title": "⚠️ ISOLATED NODE",
        "squad_none_body": "An isolated node mines slowly.\nForm a structure to survive.",
        "btn_create_squad": "➕ FORM ({cost} HIVE)",
        "squad_active": "🐝 **ACTIVE SWARM**\n👥 Members: {members}\n🔥 Synergy: ACTIVE",
        "no_balance": "❌ Insufficient HIVE"
    },
    "ru": {
        "intro_caption": "Добро пожаловать в The One Hive.\n\nЭто не игра. Это не аирдроп.\nЭто активная система извлечения ценности.\n\nИсследуйте.",
        "btn_enter": "👉 Войти в Улей",
        "intro_step2": "Улей растет благодаря постоянству.\n\nКто-то заходит рано.\nДругие приходят, когда уже поздно.",
        "btn_status": "👉 Мой статус",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ УЗЕЛ НЕ ЗАЩИЩЕН",
        "status_safe": "✅ УЗЕЛ ЗАЩИЩЕН",
        "lbl_energy": "⚡ Энергия",
        "lbl_honey": "🍯 Нектар",
        "lbl_feed": "📊 **Лента:**",
        "footer_msg": "📝 _Эмиссия ограничена. Доступ редок._",
        "btn_mine": "⚡ МАЙНИТЬ (TAP)",
        "btn_tasks": "🟢 ЗАДАНИЯ",
        "btn_rank": "🧬 ЭВОЛЮЦИЯ",
        "btn_squad": "🐝 ОТРЯД",
        "btn_team": "👥 РАСШИРИТЬ",
        "btn_shop": "🛡️ СТАБИЛИЗАЦИЯ ($)",
        "viral_1": "Это не аирдроп. Они измеряют реальное влияние. Я зашел до перерасчета.\n\n{link}",
        "viral_2": "Я не должен этим делиться. Система ищет органические узлы.\n\n{link}",
        "sys_event_1": "⚠️ Параметр изменен",
        "sys_event_2": "⏳ Альфа-окно активно",
        "sys_event_3": "🔒 Доступ ограничен",
        "feed_action_1": "подтвердил узел",
        "feed_action_2": "синтезировал блок",
        "lock_msg": "🔒 ДОСТУП ЗАПРЕЩЕН. Требуется уровень {lvl}.",
        "protect_title": "⚠️ **ЗАЩИЩЕННОЕ ДЕЙСТВИЕ: {reason}**",
        "protect_body": "Система требует валидации для сохранения прогресса.\nСкопируйте ключ:",
        "email_prompt": "✅ Введите ваш **EMAIL**:",
        "email_success": "✅ **УЗЕЛ БРОНИРОВАН**",
        "shop_title": "🛡️ **СТАБИЛИЗАЦИЯ (PREMIUM)**",
        "shop_body": "Защитите узел от деградации и получите приоритет.",
        "btn_buy_prem": "🛡️ СТАБИЛИЗИРОВАТЬ (${price})",
        "btn_buy_energy": "🔋 ЗАРЯДКА ({cost} HIVE)",
        "pay_txt": "🛡️ **АКТИВАЦИЯ**\n\nОтправьте ${price} USDT (TRC20) на:\n`{wallet}`",
        "team_title": "👥 **РАСШИРЕНИЕ**",
        "team_body": "1 Реф = {bonus} Очков.\n\n🔗 `{link}`",
        "tasks_title": "📡 **ЗОНЫ СБОРА**",
        "tasks_body": "Выберите Улей по рангу:\n\n🟢 **ЗЕЛЕНЫЙ:** Уровень 0+\n🟡 **ЗОЛОТОЙ:** Исследователь\n🔴 **КРАСНЫЙ:** Страж",
        "btn_back": "🔙 НАЗАД",
        "green_hive": "ЗЕЛЕНЫЙ УЛЕЙ",
        "gold_hive": "ЗОЛОТОЙ УЛЕЙ",
        "red_hive": "КРАСНЫЙ УЛЕЙ",
        "squad_none_title": "⚠️ ИЗОЛИРОВАННЫЙ УЗЕЛ",
        "squad_none_body": "Одиночный узел майнит медленно.\nСоздайте структуру.",
        "btn_create_squad": "➕ СОЗДАТЬ ({cost} HIVE)",
        "squad_active": "🐝 **АКТИВНЫЙ ОТРЯД**\n👥 Участников: {members}\n🔥 Синергия: АКТИВНА",
        "no_balance": "❌ Недостаточно HIVE"
    },
    "zh": {
        "intro_caption": "欢迎来到 The One Hive。\n\n这不是游戏。这不是空投。\n这是一个主动价值提取系统。\n\n探索。系统会适应。",
        "btn_enter": "👉 进入蜂巢",
        "intro_step2": "蜂巢靠持续性成长。\n\n有些人很早就进来了。\n其他人来晚了。",
        "btn_status": "👉 查看状态",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ 节点未保护",
        "status_safe": "✅ 节点安全",
        "lbl_energy": "⚡ 能量",
        "lbl_honey": "🍯 花蜜",
        "lbl_feed": "📊 **实时动态:**",
        "footer_msg": "📝 _排放有限。机会稀缺。_",
        "btn_mine": "⚡ 挖掘 (TAP)",
        "btn_tasks": "🟢 任务",
        "btn_rank": "🧬 进化",
        "btn_squad": "🐝 小队",
        "btn_team": "👥 扩张",
        "btn_shop": "🛡️ 稳定 ($)",
        "viral_1": "这不是空投。他们在衡量真实影响力。我在调整前进来的。\n\n{link}",
        "viral_2": "我不该分享这个。系统寻找有机节点。确保你的位置。\n\n{link}",
        "sys_event_1": "⚠️ 参数已调整",
        "sys_event_2": "⏳ Alpha 窗口激活",
        "sys_event_3": "🔒 访问减少",
        "feed_action_1": "验证节点",
        "feed_action_2": "合成区块",
        "lock_msg": "🔒 访问被拒绝。需要等级 {lvl}。",
        "protect_title": "⚠️ **受保护操作: {reason}**",
        "protect_body": "系统需要验证以保护您的进度。\n复制您的密钥:",
        "email_prompt": "✅ 输入您的 **EMAIL**:",
        "email_success": "✅ **节点已加固**",
        "shop_title": "🛡️ **稳定化 (PREMIUM)**",
        "shop_body": "防止节点退化并获得优先权。",
        "btn_buy_prem": "🛡️ 稳定节点 (${price})",
        "btn_buy_energy": "🔋 充电 ({cost} HIVE)",
        "pay_txt": "🛡️ **激活**\n\n发送 ${price} USDT (TRC20) 到:\n`{wallet}`",
        "team_title": "👥 **扩张**",
        "team_body": "1 推荐 = {bonus} 分。\n\n🔗 `{link}`",
        "tasks_title": "📡 **采集区**",
        "tasks_body": "按等级选择:\n\n🟢 **绿区:** 等级 0+\n🟡 **金区:** 探索者\n🔴 **红区:** 守卫者",
        "btn_back": "🔙 返回",
        "green_hive": "绿色蜂巢",
        "gold_hive": "金色蜂巢",
        "red_hive": "红色蜂巢",
        "squad_none_title": "⚠️ 孤立节点",
        "squad_none_body": "孤立节点挖掘缓慢。\n形成一个结构以生存。",
        "btn_create_squad": "➕ 组建 ({cost} HIVE)",
        "squad_active": "🐝 **活跃小队**\n👥 成员: {members}\n🔥 协同: 活跃",
        "no_balance": "❌ HIVE 不足"
    },
    "pt": {
        "intro_caption": "Bem-vindo ao The One Hive.\n\nNão é um jogo. Não é airdrop.\nÉ um sistema de extração de valor ativo.\n\nExplore. O sistema se adapta.",
        "btn_enter": "👉 Entrar na Colmeia",
        "intro_step2": "A colmeia não cresce de repente.\nCresce pela constância.\n\nAlguns entram cedo.\nOutros chegam quando já está cheia.",
        "btn_status": "👉 Ver meu estado",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NÓ NÃO PROTEGIDO",
        "status_safe": "✅ NÓ SEGURO",
        "lbl_energy": "⚡ Energia",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Feed:**",
        "footer_msg": "📝 _A emissão é limitada. O acesso é escasso._",
        "btn_mine": "⚡ MINERAR (TAP)",
        "btn_tasks": "🟢 FAVOS",
        "btn_rank": "🧬 EVOLUÇÃO",
        "btn_squad": "🐝 COLMEIA",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ ESTABILIZAR ($)",
        "viral_1": "Isso não é airdrop. Estão medindo influência real. Entrei antes do ajuste.\n\n{link}",
        "viral_2": "Não deveria compartilhar. O sistema busca nós orgânicos. Garanta sua vaga.\n\n{link}",
        "sys_event_1": "⚠️ Parâmetro ajustado",
        "sys_event_2": "⏳ Janela Alfa ativa",
        "sys_event_3": "🔒 Acesso reduzido",
        "feed_action_1": "validou nó",
        "feed_action_2": "sintetizou bloco",
        "lock_msg": "🔒 ACESSO NEGADO. Nível {lvl} necessário.",
        "protect_title": "⚠️ **AÇÃO PROTEGIDA: {reason}**",
        "protect_body": "O sistema requer validação para proteger seu progresso.\nCopie sua chave:",
        "email_prompt": "✅ Digite seu **EMAIL**:",
        "email_success": "✅ **NÓ BLINDADO**",
        "shop_title": "🛡️ **ESTABILIZAÇÃO (PREMIUM)**",
        "shop_body": "Proteja seu nó contra degradação e ganhe prioridade.",
        "btn_buy_prem": "🛡️ ESTABILIZAR NÓ (${price})",
        "btn_buy_energy": "🔋 RECARGA ({cost} HIVE)",
        "pay_txt": "🛡️ **ATIVAR**\n\nEnvie ${price} USDT (TRC20) para:\n`{wallet}`",
        "team_title": "👥 **EXPANSÃO**",
        "team_body": "1 Ref = {bonus} Pts.\n\n🔗 `{link}`",
        "tasks_title": "📡 **ZONAS DE COLETA**",
        "tasks_body": "Selecione o Favo:\n\n🟢 **VERDE:** Nível 0+\n🟡 **DOURADO:** Explorador\n🔴 **VERMELHO:** Guardião",
        "btn_back": "🔙 VOLTAR",
        "green_hive": "FAVO VERDE",
        "gold_hive": "FAVO DOURADO",
        "red_hive": "FAVO VERMELHO",
        "squad_none_title": "⚠️ NÓ ISOLADO",
        "squad_none_body": "Um nó isolado minera lentamente.\nForme uma estrutura.",
        "btn_create_squad": "➕ FORMAR ({cost} HIVE)",
        "squad_active": "🐝 **COLMEIA ATIVA**\n👥 Membros: {members}\n🔥 Sinergia: ATIVA",
        "no_balance": "❌ Saldo Insuficiente"
    }
}

def get_text(lang_code: str, key: str, **kwargs) -> str:
    if lang_code and len(lang_code) > 2:
        lang_code = lang_code[:2]
    lang_dict = TEXTS.get(lang_code, TEXTS["en"])
    text = lang_dict.get(key, TEXTS["en"].get(key, f"MISSING_{key}"))
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

# --- PANALES ACTIVOS (BASE DE DATOS COMPLETA) ---
FORRAJEO_DB = {
    "PANAL_VERDE": [ 
        {"name": "⚡ ADS PRIORITY", "url": "https://t.me/AnuncianteDeTurno"}, 
        {"name": "📺 Timebucks", "url": os.getenv("LINK_TIMEBUCKS", "https://timebucks.com/?refID=227501472")},
        {"name": "💰 ADBTC", "url": "https://r.adbtc.top/3284589"},
        {"name": "🎲 FreeBitcoin", "url": "https://freebitco.in/?r=55837744"},
        {"name": "🔥 CoinPayU", "url": "https://www.coinpayu.com/?r=PandoraHive"},
        {"name": "💸 FreeCash", "url": "https://freecash.com/r/XYN98"},
        {"name": "🌀 FaucetPay", "url": "https://faucetpay.io/?r=12345"},
        {"name": "💎 Cointiply", "url": "http://cointiply.com/r/12345"},
        {"name": "🕹️ Gamee", "url": "https://www.gamee.com/"},
        {"name": "📱 LootUp", "url": "https://lootup.me/"},
        {"name": "🛍️ Swagbucks", "url": "https://www.swagbucks.com/"},
        {"name": "📥 InboxDollars", "url": "https://www.inboxdollars.com/"},
        {"name": "🦅 StormGain", "url": "https://app.stormgain.com/"},
        {"name": "🔹 RollerCoin", "url": "https://rollercoin.com/"}
    ],
    "PANAL_DORADO": [ 
        {"name": "🐝 Honeygain", "url": "https://join.honeygain.com/ALEJOE9F32"},
        {"name": "📦 PacketStream", "url": "https://packetstream.io/?psr=7hQT"},
        {"name": "📶 EarnApp", "url": "https://earnapp.com/i/pandora"},
        {"name": "🌱 SproutGigs", "url": "https://sproutgigs.com/?a=83fb1bf9"},
        {"name": "♟️ Pawns.app", "url": "https://pawns.app/?r=18399810"}
    ],
    "PANAL_ROJO": [ 
        {"name": "🔥 ByBit (+20 USDT)", "url": "https://www.bybit.com/invite?ref=BBJWAX4"},
        {"name": "💳 Revolut (VIP)", "url": "https://revolut.com/referral/?referral-code=alejandroperdbhx"},
        {"name": "🔶 Binance", "url": "https://accounts.binance.com/register?ref=PANDORA"},
        {"name": "🏦 Nexo", "url": "https://nexo.com/ref/rbkekqnarx?src=android-link"},
        {"name": "🆗 OKX", "url": "https://www.okx.com/join/PANDORA"}
    ]
}

# ==============================================================================
# UTILIDADES & NARRATIVA
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def calculate_evolution_progress(hive: float, referrals: int, lang: str) -> str:
    poder = hive + (referrals * CONST["BONO_REFERIDO"])
    niveles = list(RANGOS_CONFIG.values())
    siguiente = None
    for nivel in niveles:
        if nivel["meta_hive"] > poder:
            siguiente = nivel
            break
    if siguiente:
        falta = siguiente["meta_hive"] - poder
        return f"-{falta:,.0f} pts" 
    return "MAX"

def generate_live_feed(lang: str) -> str:
    eventos = [
        get_text(lang, "sys_event_1"), get_text(lang, "sys_event_2"), 
        get_text(lang, "sys_event_3")
    ]
    if random.random() < 0.25:
        return f"SYSTEM: {random.choice(eventos)}"
    
    acciones = [get_text(lang, "feed_action_1"), get_text(lang, "feed_action_2")]
    return f"• ID-{random.randint(100,999)} {random.choice(acciones)} ({random.randint(1,9)}m)"

async def smart_edit(update: Update, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    except BadRequest as e:
        try:
            await update.callback_query.message.delete()
        except: pass
        try:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        except Exception as e2:
            logger.error(f"Error SmartEdit Rescue: {e2}")

# ==============================================================================
# BIO ENGINE
# ==============================================================================

class BioEngine:
    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        elapsed = now - node.get("last_regen", now)
        
        balance = node.get("honey", 0)
        # Adaptación para Redis (lista de referidos puede ser nula)
        refs_list = node.get("referrals") or []
        refs = len(refs_list)
        poder_total = balance + (refs * CONST["BONO_REFERIDO"])
        
        rango = "LARVA"
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder_total >= data["meta_hive"]:
                rango = nombre
                stats = data
        
        node["caste"] = rango 
        node["max_polen"] = stats["max_energia"]
        
        if elapsed > 0:
            regen = elapsed * 0.8 
            node["polen"] = min(node["max_polen"], node["polen"] + int(regen))
            
        node["last_regen"] = now
        return node

class SecurityEngine:
    @staticmethod
    def generate_access_code() -> str:
        return f"HIVE-{random.randint(1000, 9999)}"

async def request_email_protection(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    user = update.effective_user
    lang = user.language_code
    
    code = SecurityEngine.generate_access_code()
    context.user_data['captcha'] = code
    context.user_data['step'] = 'captcha_wait'
    context.user_data['pending_action'] = reason
    
    txt = (
        f"{get_text(lang, 'protect_title', reason=reason)}\n\n"
        f"{get_text(lang, 'protect_body')}\n"
        f"`{code}`"
    )
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

# ==============================================================================
# FLUJOS PRINCIPALES
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    ref_id = int(args[0]) if args and args[0].isdigit() else None
    
    # Crear nodo en Redis
    try: await db.db.create_node(user.id, user.first_name, user.username, ref_id)
    except: pass
    
    txt = get_text(lang, "intro_caption")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_enter"), callback_data="intro_step_2")]]
    
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def intro_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user = q.from_user
    lang = user.language_code
    
    await q.answer("...")
    try: await context.bot.send_chat_action(chat_id=q.message.chat_id, action=ChatAction.TYPING)
    except: pass
    await asyncio.sleep(1.5)
    try: await q.message.delete()
    except: pass

    txt = get_text(lang, "intro_step2")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_status"), callback_data="go_dash")]]
    await q.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    lang = user.language_code
    uid = user.id
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ OK", callback_data="accept_terms")]]
            await update.message.reply_text("✅ OK", reply_markup=InlineKeyboardMarkup(kb))
        else: await update.message.reply_text("❌ X")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.db.update_email(uid, email)
            context.user_data['step'] = None
            
            # Obtener y actualizar bono
            node = await db.db.get_node(uid)
            if node:
                node['honey'] += 15.0 
                await db.db.save_node(uid, node)
            
            kb = [[InlineKeyboardButton("🟢 ->", callback_data="go_dash")]]
            await update.message.reply_text(get_text(lang, "email_success"), reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text("⚠️ Email Error")
        return

    try:
        node = await db.db.get_node(uid)
        if node: await show_dashboard(update, context)
    except: pass

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.callback_query: 
            uid = update.callback_query.from_user.id
            lang = update.callback_query.from_user.language_code
            user = update.callback_query.from_user
        else: 
            uid = update.effective_user.id
            lang = update.effective_user.language_code
            user = update.effective_user
        
        # Asegurar existencia en Redis
        try: await db.db.create_node(uid, user.first_name, user.username)
        except: pass
        
        node = await db.db.get_node(uid)
        if not node: return # Safety check

        node = BioEngine.calculate_state(node)
        await db.db.save_node(uid, node)
        
        rango = node['caste']
        info = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])
        status_msg = get_text(lang, "status_unsafe") if not node.get("email") else get_text(lang, "status_safe")
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        header = get_text(lang, "dash_header")
        lbl_e = get_text(lang, "lbl_energy")
        lbl_h = get_text(lang, "lbl_honey")
        lbl_f = get_text(lang, "lbl_feed")
        footer = get_text(lang, "footer_msg")
        live = generate_live_feed(lang)
        
        txt = (
            f"{header} | {info['icono']} **{rango}**\n"
            f"────────────────\n"
            f"{status_msg}\n\n"
            f"{lbl_e}: `{bar}`\n"
            f"{lbl_h}: `{node['honey']:.4f}`\n\n"
            f"{lbl_f}\n{live}\n\n"
            f"{footer}\n"
            f"────────────────"
        )
        
        kb = [
            [InlineKeyboardButton(get_text(lang, "btn_mine"), callback_data="forage")],
            [InlineKeyboardButton(get_text(lang, "btn_tasks"), callback_data="tasks"), InlineKeyboardButton(get_text(lang, "btn_rank"), callback_data="rank_info")],
            [InlineKeyboardButton(get_text(lang, "btn_squad"), callback_data="squad"), InlineKeyboardButton(get_text(lang, "btn_team"), callback_data="team")],
            [InlineKeyboardButton(get_text(lang, "btn_shop"), callback_data="shop")]
        ]
        await smart_edit(update, txt, InlineKeyboardMarkup(kb))
    except Exception as e: logger.error(f"Dash Error: {e}")

# ==============================================================================
# SUB-MENÚS MULTI-IDIOMA
# ==============================================================================

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    kb = [
        [InlineKeyboardButton(f"🟢 {get_text(lang, 'green_hive')}", callback_data="v_t1")],
        [InlineKeyboardButton(f"🟡 {get_text(lang, 'gold_hive')} 🔒", callback_data="v_t2")],
        [InlineKeyboardButton(f"🔴 {get_text(lang, 'red_hive')} 🔒", callback_data="v_t3")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    txt = f"{get_text(lang, 'tasks_title')}\n\n{get_text(lang, 'tasks_body')}"
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def view_tier_generic(update: Update, key: str, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.db.get_node(uid)
    
    if (key == "v_t2" or key == "v_t3") and not node.get("email"):
        await request_email_protection(update, context, "TIER ACCESS")
        return

    rol = node.get("caste", "LARVA")
    lvl = RANGOS_CONFIG.get(rol, RANGOS_CONFIG["LARVA"])["acceso"]
    
    db_key = "PANAL_VERDE"; req_lvl = 0; dict_key = "green_hive"
    if key == "v_t2": db_key = "PANAL_DORADO"; req_lvl = 2; dict_key = "gold_hive"
    if key == "v_t3": db_key = "PANAL_ROJO"; req_lvl = 3; dict_key = "red_hive"
    
    if lvl < req_lvl:
        msg = get_text(lang, "lock_msg", lvl=req_lvl)
        await q.answer(msg, show_alert=True)
        return
        
    links = FORRAJEO_DB.get(db_key, [])
    kb = []
    for item in links:
        kb.append([InlineKeyboardButton(f"{item['name']}", url=item["url"])])
    
    kb.append([InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="tasks")])
    
    title = get_text(lang, dict_key)
    await smart_edit(update, f"📍 **{title}**", InlineKeyboardMarkup(kb))

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.db.get_node(uid)
        
        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Low Energy", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        yield_amt = CONST['RECOMPENSA_BASE'] * RANGOS_CONFIG[node['caste']]['bonus_tap']
        node['honey'] += yield_amt
        
        await db.db.save_node(uid, node)
        await q.answer(f"✅ +{yield_amt:.4f}")
        if random.random() < 0.2: await show_dashboard(update, context)
    except Exception: pass

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_dashboard(update, context) 

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.db.get_node(uid)
    
    if node.get("enjambre_id"): # En Redis, este campo puede ser string o None
        # Necesitamos cargar la célula
        cell_id = node.get("enjambre_id")
        # NOTA: get_cell en tu DB espera cell_id string
        cell = await db.db.get_cell(cell_id) if cell_id else None
        
        if cell:
            members_count = len(cell.get('members', []))
            txt = get_text(lang, "squad_active", members=members_count)
            kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
            await smart_edit(update, txt, InlineKeyboardMarkup(kb))
            return

    # Si no tiene squad:
    txt = f"{get_text(lang, 'squad_none_title')}\n\n{get_text(lang, 'squad_none_body')}"
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_create_squad", cost=CONST['COSTO_ENJAMBRE']), callback_data="mk_cell")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.db.get_node(uid)
    
    if not node.get("email"):
        await request_email_protection(update, context, "SQUAD")
        return
        
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        
        # Crear en Redis
        cell_name = f"Cluster-{random.randint(100,999)}"
        cell_id = await db.db.create_cell(uid, cell_name)
        
        if cell_id:
            node['enjambre_id'] = cell_id
            await db.db.save_node(uid, node)
            await q.answer("✅"); await squad_menu(update, context)
        else:
            await q.answer("❌ Error DB", show_alert=True)
            
    else: 
        await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.db.get_node(uid)
    if not node.get("email"):
        await request_email_protection(update, context, "SHOP")
        return
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_buy_prem", price=CONST['PRECIO_ACELERADOR']), callback_data="buy_premium")],
        [InlineKeyboardButton(get_text(lang, "btn_buy_energy", cost=CONST['COSTO_RECARGA']), callback_data="buy_energy")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    txt = f"{get_text(lang, 'shop_title')}\n\n{get_text(lang, 'shop_body')}"
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.db.save_node(uid, node)
        await q.answer("⚡ OK"); await show_dashboard(update, context)
    else: await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    txt = get_text(lang, "pay_txt", price=CONST['PRECIO_ACELERADOR'], wallet=CRYPTO_WALLET_USDT)
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.db.get_node(uid)
    if not node.get("email"):
        await request_email_protection(update, context, "INVITE")
        return
    
    link = f"https://t.me/{context.bot.username}?start={uid}"
    
    viral_key = random.choice(["viral_1", "viral_2"])
    share_txt = get_text(lang, viral_key, link=link)
    share_url = f"https://t.me/share/url?url={share_txt}"
    
    txt = get_text(lang, "team_body", bonus=CONST['BONO_REFERIDO'], link=link)
    title = get_text(lang, "team_title")
    
    kb = [[InlineKeyboardButton("📤 SHARE", url=share_url)], [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, f"{title}\n\n{txt}", InlineKeyboardMarkup(kb))

# ==============================================================================
# ROUTER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    lang = q.from_user.language_code
    
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await smart_edit(update, get_text(lang, "email_prompt"), InlineKeyboardMarkup([]))
        return

    actions = {
        "intro_step_2": intro_step_2,
        "go_dash": show_dashboard, "forage": forage_action, "tasks": tasks_menu,
        "rank_info": rank_info_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "v_t1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "v_t2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "v_t3", c),
        "squad": squad_menu, "mk_cell": create_squad_logic,
        "shop": shop_menu, "buy_energy": buy_energy, "buy_premium": buy_premium, 
        "team": team_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("V10.0 Redis Global")
async def broadcast_cmd(u, c): pass
