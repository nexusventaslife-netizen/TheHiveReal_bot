import logging
import asyncio
import random
import time
import math
import os
import ujson as json
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes, Application
from telegram.error import BadRequest
from loguru import logger
from email_validator import validate_email

# IMPORTAMOS TU BASE DE DATOS REDIS (NO BORRES DATABASE.PY)
from database import db 

# ==============================================================================
# 🐝 THE ONE HIVE: V13.1 (HSP MONOLITH - FULL GAMIFICATION)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ------------------------------------------------------------------------------
# 💰 ZONA DE DINERO (CONFIGURACIÓN A FUEGO)
# ------------------------------------------------------------------------------
# PEGA TU BILLETERA TRC20 AQUÍ ABAJO ENTRE LAS COMILLAS:
WALLET_TRC20_FIJA = os.getenv("WALLET_USDT", "TRC20_WALLET_PENDING")

# ENLACE PAYPAL (FIJO)
LINK_PAYPAL_HARDCODED = "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC"
# ------------------------------------------------------------------------------

# --- IDENTIDAD VISUAL ---
# IMAGEN ACTUALIZADA
IMG_GENESIS = "https://i.postimg.cc/hv2HXWkN/photo-2025-12-22-16-00-42.jpg"
IMG_DASHBOARD = "https://i.postimg.cc/hv2HXWkN/photo-2025-12-22-16-00-42.jpg"

# --- CONSTANTES DE ECONOMÍA (V13 HSP) ---
CONST = {
    "COSTO_POLEN": 10,        
    "RECOMPENSA_BASE": 0.05,
    "DECAY_OXIGENO": 4.0,     
    "COSTO_ENJAMBRE": 100,    
    "COSTO_RECARGA": 50,      
    "BONO_REFERIDO": 500,
    "PRECIO_ACELERADOR": 9.99, # PRECIO MENSUAL
    "TRIGGER_EMAIL_HONEY": 50,
    "VIRAL_FACTOR": 0.05,       # 5% extra por amigo
    # NUEVO HSP CONFIG
    "HSP_BASE": 1.0,
    "STREAK_BONUS": 1.1,        # +10% exponencial por racha
    "COMBO_DAILY_REWARD": 100.0,
    "TAP_RATE_LIMIT": 0.3       # Segundos entre taps
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA": {
        "nivel": 0, "meta_hive": 0, "max_energia": 200, "bonus_tap": 1.0, "hsp_mult": 1.0, "icono": "🐛", "acceso": 0
    },
    "OBRERO": {
        "nivel": 1, "meta_hive": 1000, "max_energia": 400, "bonus_tap": 1.1, "hsp_mult": 1.2, "icono": "🐝", "acceso": 1
    },
    "EXPLORADOR": {
        "nivel": 2, "meta_hive": 5000, "max_energia": 800, "bonus_tap": 1.2, "hsp_mult": 1.5, "icono": "🔭", "acceso": 2
    },
    "GUARDIAN": {
        "nivel": 3, "meta_hive": 20000, "max_energia": 1500, "bonus_tap": 1.5, "hsp_mult": 2.0, "icono": "🛡️", "acceso": 3
    },
    "REINA": {
        "nivel": 4, "meta_hive": 100000, "max_energia": 5000, "bonus_tap": 3.0, "hsp_mult": 5.0, "icono": "👑", "acceso": 3
    }
}

# ==============================================================================
# 🌐 MOTOR DE TRADUCCIÓN (TEXTOS COMPLETOS V13)
# ==============================================================================
TEXTS = {
    "es": {
        "intro_caption": "Bienvenido a The One Hive V13.\n\nEsto no es un airdrop.\nEsto no es una inversión.\n\nEs un sistema vivo midiendo participación e influencia (HSP).\n\nEl acceso temprano sigue abierto.",
        "btn_enter": "👉 Acceder al Sistema",
        "intro_step2": "**AVISO DE RED:**\n\nTu progreso es relativo a la actividad de la red.\n\nLos nodos más activos son priorizados en esta fase.\nLa participación temprana importa.",
        "btn_status": "👉 Verificar Nodo",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NODO ESTÁNDAR",
        "status_safe": "✅ NODO VERIFICADO",
        "lbl_energy": "⚡ Energía",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Red:**",
        "footer_msg": "📝 _Prioridad de red calculada en tiempo real._",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 PANALES",
        "btn_rank": "🧬 EVOLUCIÓN",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ PRIORIDAD ($)",
        # NUEVOS TEXTOS V13
        "hsp_lbl": "🌐 HSP (x{hsp:.2f})",
        "streak_lbl": "🔥 Streak: {streak}",
        "daily_combo": "🔥 **COMBO DIARIO**\n\nIngresa la secuencia exacta de emojis:\n`{combo}`\n\n_Escribe los emojis en el chat para reclamar el bono._",
        "combo_success": "🚀 **COMBO CORRECTO**\n+{amt} HIVE! Streak Aumentado.",
        "leaderboard": "🏆 **TOP HSP GLOBAL**\n\n{top10}",
        "predictions": "🧠 **PREDICCIONES HIVE**\n\nEvento: {evento}\n\n¿Sucederá? Vota para ganar HSP.",
        "pred_vote_ok": "✅ Voto registrado. Si aciertas, tu HSP subirá mañana.",
        "viral_1": "El acceso temprano sigue abierto. Un sistema vivo se está formando. Los que entran antes entienden.\n\n{link}",
        "viral_2": "No todos deberían entrar. El acceso temprano sigue abierto.\n\n{link}",
        "sys_event_1": "⚠️ Prioridad reasignada a nodos activos",
        "sys_event_2": "⏳ Ventana de expansión abierta",
        "sys_event_3": "🔒 Capacidad de fase alcanzando límite",
        "feed_action_1": "aseguró posición",
        "feed_action_2": "expandió conexión",
        "lock_msg": "🔒 FASE RESTRINGIDA. Nivel {lvl} requerido.",
        "protect_title": "⚠️ **ASEGURA TU NODO: {reason}**",
        "protect_body": "Al registrar un email:\n• Preservas tu progreso\n• Recibes actualizaciones del sistema\n• Obtienes notificaciones de acceso temprano\n\nNo vendemos cuentas.",
        "email_prompt": "🛡️ **REGISTRO DE NODO**\n\nIngresa tu EMAIL para asegurar persistencia:",
        "email_success": "✅ **NODO ASEGURADO**",
        "shop_title": "🛡️ **ACCESO PRIORITARIO MENSUAL**",
        "shop_body": "Esta suscripción mejora la velocidad y el acceso.\nNo garantiza ganancias.\n\nIncluye (30 Días):\n✅ Regeneración de energía más rápida\n✅ Acceso a tareas avanzadas\n✅ Ubicación prioritaria en actualizaciones",
        "btn_buy_prem": "🛡️ PRIORIDAD (30 DÍAS) - ${price}",
        "btn_buy_energy": "🔋 RECARGA ({cost} HIVE)",
        "pay_txt": "🛡️ **ACCESO PRIORITARIO (30 DÍAS)**\n\nEl pase dura 30 días exactos.\n\n🔹 **Opción A: Cripto (USDT)**\n`{wallet}`\n\n🔹 **Opción B: PayPal**\nBotón abajo.",
        "btn_paypal": "💳 Pagar con PayPal",
        "team_title": "👥 **EXPANSIÓN DE RED**",
        "team_body": "Nodos con conexiones activas avanzan más rápido.\nEl sistema detecta expansión real, no spam.\n\n🔗 Tu Enlace de Nodo:\n`{link}`",
        "tasks_title": "📡 **ZONAS DE ACTIVIDAD**",
        "tasks_body": "Selecciona el Panal según tu rango:\n\n🟢 **PANAL VERDE:** Nivel 0+\n🟡 **PANAL DORADO:** Explorador\n🔴 **PANAL ROJO:** Guardián",
        "btn_back": "🔙 VOLVER",
        "green_hive": "PANAL VERDE",
        "gold_hive": "PANAL DORADO",
        "red_hive": "PANAL ROJO",
        "squad_none_title": "⚠️ NODO INDIVIDUAL",
        "squad_none_body": "Los nodos individuales tienen menor prioridad.\nConecta con otros para escalar.",
        "btn_create_squad": "➕ CONECTAR ({cost} HIVE)",
        "squad_active": "🐝 **CONEXIÓN ACTIVA**\n👥 Nodos: {members}\n🔥 HSP Boost: ACTIVO",
        "no_balance": "❌ HIVE Insuficiente"
    },
    "en": {
        "intro_caption": "Welcome to The One Hive V13.\n\nThis is not an airdrop.\nThis is not an investment.\n\nIt’s a live system measuring participation and influence (HSP).",
        "btn_enter": "👉 Access System",
        "intro_step2": "**NETWORK NOTICE:**\n\nYour progress is relative to network activity.\n\nMore active nodes are being prioritized in this phase.\nEarly participation matters.",
        "btn_status": "👉 Verify Node",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ STANDARD NODE",
        "status_safe": "✅ VERIFIED NODE",
        "lbl_energy": "⚡ Energy",
        "lbl_honey": "🍯 Nectar",
        "lbl_feed": "📊 **Network:**",
        "footer_msg": "📝 _Network priority calculated in real-time._",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 HIVES",
        "btn_rank": "🧬 EVOLUTION",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 EXPAND",
        "btn_shop": "🛡️ PRIORITY ($)",
        # V13 English Keys
        "hsp_lbl": "🌐 HSP (x{hsp:.2f})",
        "streak_lbl": "🔥 Streak: {streak}",
        "daily_combo": "🔥 **DAILY COMBO**\n\nEnter the exact emoji sequence:\n`{combo}`\n\n_Type emojis in chat to claim bonus._",
        "combo_success": "🚀 **COMBO MATCH**\n+{amt} HIVE! Streak Increased.",
        "leaderboard": "🏆 **GLOBAL HSP TOP**\n\n{top10}",
        "predictions": "🧠 **HIVE PREDICTIONS**\n\nEvent: {evento}\n\nWill it happen? Vote to gain HSP.",
        "pred_vote_ok": "✅ Vote registered. Correct guess boosts HSP tomorrow.",
        "viral_1": "Early access is open. A live system is forming. Those who enter early understand.\n\n{link}",
        "viral_2": "Not everyone should enter. Early access is still open.\n\n{link}",
        "sys_event_1": "⚠️ Priority reassigned to active nodes",
        "sys_event_2": "⏳ Expansion window open",
        "sys_event_3": "🔒 Phase capacity reaching limit",
        "feed_action_1": "secured position",
        "feed_action_2": "expanded connection",
        "lock_msg": "🔒 RESTRICTED PHASE. Level {lvl} required.",
        "protect_title": "⚠️ **SECURE YOUR NODE: {reason}**",
        "protect_body": "By registering an email you:\n• Preserve your progress\n• Receive system updates\n• Get early access notifications\n\nWe do not sell accounts.",
        "email_prompt": "🛡️ **NODE REGISTRATION**\n\nEnter EMAIL to ensure persistence:",
        "email_success": "✅ **NODE SECURED**",
        "shop_title": "🛡️ **MONTHLY PRIORITY ACCESS**",
        "shop_body": "This subscription enhances speed and access.\nIt does not guarantee earnings.\n\nIncludes (30 Days):\n✅ Faster energy regeneration\n✅ Access to advanced task tiers\n✅ Priority placement in updates",
        "btn_buy_prem": "🛡️ PRIORITY (30 DAYS) - ${price}",
        "btn_buy_energy": "🔋 RECHARGE ({cost} HIVE)",
        "pay_txt": "🛡️ **PRIORITY ACCESS (30 DAYS)**\n\nPass valid for 30 days.\n\n🔹 **Option A: Crypto (USDT)**\n`{wallet}`\n\n🔹 **Option B: PayPal**\nButton below.",
        "btn_paypal": "💳 Pay with PayPal",
        "team_title": "👥 **NETWORK EXPANSION**",
        "team_body": "Nodes with active connections advance faster.\nThe system detects real expansion, not spam.\n\n🔗 Your Node Link:\n`{link}`",
        "tasks_title": "📡 **ACTIVITY ZONES**",
        "tasks_body": "Select Hive by rank:\n\n🟢 **GREEN HIVE:** Level 0+\n🟡 **GOLD HIVE:** Explorer\n🔴 **RED HIVE:** Guardian",
        "btn_back": "🔙 BACK",
        "green_hive": "GREEN HIVE",
        "gold_hive": "GOLD HIVE",
        "red_hive": "RED HIVE",
        "squad_none_title": "⚠️ INDIVIDUAL NODE",
        "squad_none_body": "Individual nodes have lower priority.\nConnect with others to scale.",
        "btn_create_squad": "➕ CONNECT ({cost} HIVE)",
        "squad_active": "🐝 **ACTIVE CONNECTION**\n👥 Nodes: {members}\n🔥 HSP Boost: ACTIVE",
        "no_balance": "❌ Insufficient HIVE"
    },
    "ru": {
        "intro_caption": "Добро пожаловать в The One Hive V13.\n\nЭто не аирдроп.\nЭто не инвестиция.\n\nЭто живая система (HSP).",
        "btn_enter": "👉 Доступ к Системе",
        "intro_step2": "**УВЕДОМЛЕНИЕ СЕТИ:**\n\nАктивные узлы имеют приоритет.",
        "btn_status": "👉 Проверить Узел",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ СТАНДАРТНЫЙ УЗЕЛ",
        "status_safe": "✅ ПРОВЕРЕННЫЙ УЗЕЛ",
        "lbl_energy": "⚡ Энергия",
        "lbl_honey": "🍯 Нектар",
        "lbl_feed": "📊 **Сеть:**",
        "footer_msg": "📝 _Приоритет в реальном времени._",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 ЗАДАНИЯ",
        "btn_rank": "🧬 ЭВОЛЮЦИЯ",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 РАСШИРЕНИЕ",
        "btn_shop": "🛡️ ПРИОРИТЕТ ($)",
        # V13
        "hsp_lbl": "🌐 HSP (x{hsp:.2f})",
        "streak_lbl": "🔥 Стрик: {streak}",
        "daily_combo": "🔥 **ЕЖЕДНЕВНОЕ КОМБО**\n\nВведите эмодзи:\n`{combo}`",
        "combo_success": "🚀 **КОМБО ВЕРНО**\n+{amt} HIVE!",
        "leaderboard": "🏆 **ТОП HSP**\n\n{top10}",
        "predictions": "🧠 **ПРЕДСКАЗАНИЯ**\n\nСобытие: {evento}",
        "pred_vote_ok": "✅ Голос принят.",
        "viral_1": "Ранний доступ открыт. Те, кто заходят раньше, понимают.\n\n{link}",
        "viral_2": "Не всем стоит заходить. Ранний доступ открыт.\n\n{link}",
        "sys_event_1": "⚠️ Приоритет переназначен активным узлам",
        "sys_event_2": "⏳ Окно расширения открыто",
        "sys_event_3": "🔒 Емкость фазы на пределе",
        "feed_action_1": "закрепил позицию",
        "feed_action_2": "расширил связь",
        "lock_msg": "🔒 ФАЗА ОГРАНИЧЕНА. Требуется уровень {lvl}.",
        "protect_title": "⚠️ **ЗАЩИТИТЕ УЗЕЛ: {reason}**",
        "protect_body": "Регистрируя email:\n• Сохраняете прогресс\n• Получаете обновления\n\nМы не продаем аккаунты.",
        "email_prompt": "🛡️ **РЕГИСТРАЦИЯ УЗЛА**\n\nВведите EMAIL для гарантии сохранения:",
        "email_success": "✅ **УЗЕЛ ЗАЩИЩЕН**",
        "shop_title": "🛡️ **МЕСЯЧНЫЙ ПРИОРИТЕТ**",
        "shop_body": "Подписка улучшает скорость и доступ.\nНе гарантирует заработок.\n\nВключает (30 Дней):\n✅ Быстрая регенерация\n✅ Доступ к задачам",
        "btn_buy_prem": "🛡️ ПРИОРИТЕТ (30 ДНЕЙ) - ${price}",
        "btn_buy_energy": "🔋 ЗАРЯДКА ({cost} HIVE)",
        "pay_txt": "🛡️ **ПРИОРИТЕТНЫЙ ДОСТУП**\n\nПропуск на 30 дней.\n\n🔹 **Опция A: USDT**\n`{wallet}`\n\n🔹 **Опция B: PayPal**\nКнопка ниже.",
        "btn_paypal": "💳 Оплата PayPal",
        "team_title": "👥 **РАСШИРЕНИЕ СЕТИ**",
        "team_body": "Узлы с активными связями продвигаются быстрее.\nСистема видит реальное расширение.\n\n🔗 Ссылка Узла:\n`{link}`",
        "tasks_title": "📡 **ЗОНЫ АКТИВНОСТИ**",
        "tasks_body": "Выберите Улей по рангу:\n\n🟢 **ЗЕЛЕНЫЙ:** Уровень 0+\n🟡 **ЗОЛОТОЙ:** Исследователь\n🔴 **КРАСНЫЙ:** Страж",
        "btn_back": "🔙 НАЗАД",
        "green_hive": "ЗЕЛЕНЫЙ УЛЕЙ",
        "gold_hive": "ЗОЛОТОЙ УЛЕЙ",
        "red_hive": "КРАСНЫЙ УЛЕЙ",
        "squad_none_title": "⚠️ ИНДИВИДУАЛЬНЫЙ УЗЕЛ",
        "squad_none_body": "Индивидуальные узлы имеют низкий приоритет.\nПодключайтесь к другим.",
        "btn_create_squad": "➕ ПОДКЛЮЧИТЬ ({cost} HIVE)",
        "squad_active": "🐝 **АКТИВНАЯ СВЯЗЬ**\n👥 Узлы: {members}\n🔥 HSP Boost: АКТИВЕН",
        "no_balance": "❌ Недостаточно HIVE"
    },
    "zh": {
        "intro_caption": "欢迎来到 The One Hive V13。\n\n这不是空投。\n这是一个衡量影响力 (HSP) 的系统。",
        "btn_enter": "👉 访问系统",
        "intro_step2": "**网络通知：**\n\n优先考虑活跃节点。",
        "btn_status": "👉 验证节点",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ 标准节点",
        "status_safe": "✅ 已验证节点",
        "lbl_energy": "⚡ 能量",
        "lbl_honey": "🍯 花蜜",
        "lbl_feed": "📊 **网络:**",
        "footer_msg": "📝 _实时优先级。_",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 任务",
        "btn_rank": "🧬 进化",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 扩张",
        "btn_shop": "🛡️ 优先 ($)",
        # V13
        "hsp_lbl": "🌐 HSP (x{hsp:.2f})",
        "streak_lbl": "🔥 连胜: {streak}",
        "daily_combo": "🔥 **每日组合**\n\n输入表情符号:\n`{combo}`",
        "combo_success": "🚀 **组合匹配**\n+{amt} HIVE!",
        "leaderboard": "🏆 **全球 HSP 排行**\n\n{top10}",
        "predictions": "🧠 **预测**\n\n事件: {evento}",
        "pred_vote_ok": "✅ 投票已记录。",
        "viral_1": "早期访问已开放。那些早进入的人明白。\n\n{link}",
        "viral_2": "不是每个人都应该进入。早期访问仍然开放。\n\n{link}",
        "sys_event_1": "⚠️ 优先级重新分配给活跃节点",
        "sys_event_2": "⏳ 扩张窗口开启",
        "sys_event_3": "🔒 阶段容量接近极限",
        "feed_action_1": "锁定位置",
        "feed_action_2": "扩展连接",
        "lock_msg": "🔒 受限阶段。需要等级 {lvl}。",
        "protect_title": "⚠️ **保护您的节点: {reason}**",
        "protect_body": "注册邮箱以：\n• 保留进度\n• 接收系统更新\n\n我们不出售账户。",
        "email_prompt": "🛡️ **节点注册**\n\n输入 EMAIL 以确保持久性:",
        "email_success": "✅ **节点已保护**",
        "shop_title": "🛡️ **每月优先访问**",
        "shop_body": "此订阅提高速度和访问权限。\n不保证收益。\n\n包括 (30天):\n✅ 更快的能量再生\n✅ 访问高级任务",
        "btn_buy_prem": "🛡️ 优先 (30天) - ${price}",
        "btn_buy_energy": "🔋 充电 ({cost} HIVE)",
        "pay_txt": "🛡️ **优先访问 (30天)**\n\n通行证有效期30天。\n\n🔹 **选项 A: USDT**\n`{wallet}`\n\n🔹 **选项 B: PayPal**\n下方按钮。",
        "btn_paypal": "💳 PayPal 支付",
        "team_title": "👥 **网络扩张**",
        "team_body": "具有活跃连接的节点进步更快。\n系统检测真实扩张，而非垃圾邮件。\n\n🔗 您的节点链接:\n`{link}`",
        "tasks_title": "📡 **活动区域**",
        "tasks_body": "按等级选择:\n\n🟢 **绿区:** 等级 0+\n🟡 **金区:** 探索者\n🔴 **红区:** 守卫者",
        "btn_back": "🔙 返回",
        "green_hive": "绿色蜂巢",
        "gold_hive": "金色蜂巢",
        "red_hive": "红色蜂巢",
        "squad_none_title": "⚠️ 个体节点",
        "squad_none_body": "个体节点优先级较低。\n与他人连接以扩展。",
        "btn_create_squad": "➕ 连接 ({cost} HIVE)",
        "squad_active": "🐝 **活跃连接**\n👥 节点: {members}\n🔥 HSP Boost: 活跃",
        "no_balance": "❌ HIVE 不足"
    },
    "pt": {
        "intro_caption": "Bem-vindo ao The One Hive V13.\n\nIsto não é um airdrop.\nÉ um sistema vivo (HSP).",
        "btn_enter": "👉 Acessar Sistema",
        "intro_step2": "**AVISO DE REDE:**\n\nNós mais ativos são priorizados.",
        "btn_status": "👉 Verificar Nó",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NÓ PADRÃO",
        "status_safe": "✅ NÓ VERIFICADO",
        "lbl_energy": "⚡ Energia",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Rede:**",
        "footer_msg": "📝 _Prioridade em tempo real._",
        "btn_mine": "⚡ TAP (HSP)",
        "btn_tasks": "🟢 FAVOS",
        "btn_rank": "🧬 EVOLUÇÃO",
        "btn_squad": "🐝 SQUAD",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ PRIORIDADE ($)",
        # V13
        "hsp_lbl": "🌐 HSP (x{hsp:.2f})",
        "streak_lbl": "🔥 Streak: {streak}",
        "daily_combo": "🔥 **COMBO DIÁRIO**\n\nDigite os emojis:\n`{combo}`",
        "combo_success": "🚀 **COMBO CORRETO**\n+{amt} HIVE!",
        "leaderboard": "🏆 **TOP HSP**\n\n{top10}",
        "predictions": "🧠 **PREVISÕES**\n\nEvento: {evento}",
        "pred_vote_ok": "✅ Voto registrado.",
        "viral_1": "Acesso antecipado aberto. Um sistema vivo está se formando. Quem entra cedo entende.\n\n{link}",
        "viral_2": "Nem todos devem entrar. Acesso antecipado ainda aberto.\n\n{link}",
        "sys_event_1": "⚠️ Prioridade reatribuída a nós ativos",
        "sys_event_2": "⏳ Janela de expansão aberta",
        "sys_event_3": "🔒 Capacidade da fase atingindo limite",
        "feed_action_1": "assegurou posição",
        "feed_action_2": "expandiu conexão",
        "lock_msg": "🔒 FASE RESTRITA. Nível {lvl} necessário.",
        "protect_title": "⚠️ **SEGURE SEU NÓ: {reason}**",
        "protect_body": "Ao registrar um email:\n• Preserva seu progresso\n• Recebe atualizações\n\nNão vendemos contas.",
        "email_prompt": "🛡️ **REGISTRO DE NÓ**\n\nDigite EMAIL para garantir persistência:",
        "email_success": "✅ **NÓ ASSEGURADO**",
        "shop_title": "🛡️ **ACESSO PRIORITÁRIO MENSAL**",
        "shop_body": "Esta assinatura melhora velocidade e acesso.\nNão garante ganhos.\n\nInclui (30 Dias):\n✅ Regeneração mais rápida\n✅ Acesso a tarefas avançadas",
        "btn_buy_prem": "🛡️ PRIORIDAD (30 DIAS) - ${price}",
        "btn_buy_energy": "🔋 RECARGA ({cost} HIVE)",
        "pay_txt": "🛡️ **ACESSO PRIORITÁRIO (30 DIAS)**\n\nPasse válido por 30 dias.\n\n🔹 **Opção A: Cripto (USDT)**\n`{wallet}`\n\n🔹 **Opção B: PayPal**\nBotão abaixo.",
        "btn_paypal": "💳 Pagar com PayPal",
        "team_title": "👥 **EXPANSÃO DE REDE**",
        "team_body": "Nós com conexões ativas avançam mais rápido.\nO sistema detecta expansão real, não spam.\n\n🔗 Seu Link de Nó:\n`{link}`",
        "tasks_title": "📡 **ZONAS DE ATIVIDADE**",
        "tasks_body": "Selecione o Favo:\n\n🟢 **VERDE:** Nível 0+\n🟡 **DOURADO:** Explorador\n🔴 **VERMELHO:** Guardião",
        "btn_back": "🔙 VOLTAR",
        "green_hive": "FAVO VERDE",
        "gold_hive": "FAVO DOURADO",
        "red_hive": "FAVO VERMELHO",
        "squad_none_title": "⚠️ NÓ INDIVIDUAL",
        "squad_none_body": "Nós individuais têm menor prioridade.\nConecte-se com outros para escalar.",
        "btn_create_squad": "➕ CONECTAR ({cost} HIVE)",
        "squad_active": "🐝 **CONEXÃO ATIVA**\n👥 Nós: {members}\n🔥 HSP Boost: ATIVO",
        "no_balance": "❌ Saldo Insuficiente"
    }
}

def get_text(lang_code: str, key: str, **kwargs) -> str:
    if lang_code and len(lang_code) > 2:
        lang_code = lang_code[:2]
    lang_dict = TEXTS.get(lang_code, TEXTS["es"]) # Default ES para V13
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
# UTILIDADES MEJORADAS
# ==============================================================================

def render_bar(current: float, total: float, length: int = 10) -> str:
    if total <= 0: total = 1
    pct = max(0.0, min(current / total, 1.0))
    fill = int(length * pct)
    return "▰" * fill + "▱" * (length - fill)

def generate_live_feed(lang: str) -> str:
    # Simulación de feed para el dashboard
    acciones = ["conectado", "minando", "HSP UP", "Combo OK", "Squad Join"]
    return f"• ID-{random.randint(100,999)} {random.choice(acciones)} ({random.randint(1,5)}s)"

def generate_daily_combo() -> str:
    """Genera un combo de emojis diario basado en la fecha"""
    combos = ["🐝👑🔥", "🍯⚡🛡️", "🔭🐛🟢", "🐝🍯💰", "👑🛡️⚡"]
    today = datetime.now().strftime("%Y%m%d")
    seed = hash(today) % len(combos)
    return combos[seed]

async def get_evento_diario() -> Dict:
    """Evento de predicción simulado"""
    eventos = [
        {"id": "btc_up", "desc": "¿Bitcoin sube hoy?", "outcome": random.choice([True, False])},
        {"id": "eth_up", "desc": "¿Ethereum pasa 3k?", "outcome": random.choice([True, False])},
        {"id": "hive_growth", "desc": "¿Hive crece 10%?", "outcome": True}
    ]
    return random.choice(eventos)

async def smart_edit(update: Update, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    except BadRequest as e:
        try:
            await update.callback_query.message.delete()
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        except Exception as e2:
            logger.error(f"Error SmartEdit: {e2}")

# ==============================================================================
# ENGINE V13: HIVE SYNERGY (HSP + RATE LIMIT + STREAK)
# ==============================================================================

class HiveSynergyEngine:
    @staticmethod
    def calculate_iil(balance: float, refs_count: int, joined_at: float) -> float:
        """Calcula el IIL clásico (base del HSP)"""
        days_alive = (time.time() - joined_at) / 86400
        if days_alive < 0: days_alive = 0
        act_score = math.log1p(balance) * 0.4
        ref_score = math.log1p(refs_count) * 0.4
        time_score = days_alive * 0.2
        return 1.0 + act_score + ref_score + time_score

    @staticmethod
    async def calculate_hsp(node: Dict) -> float:
        """Calcula el Hive Synergy Points (HSP)"""
        iil = node.get("iil", 1.0)
        
        # Factor Squad (Simulado para no hacer query pesada cada tap)
        squad_bonus = 1.0
        if node.get("cell_id"):
             squad_bonus = 1.2 
        
        # Factor Rango
        rango = node.get("caste", "LARVA")
        rango_mult = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])["hsp_mult"]
        
        hsp = iil * squad_bonus * rango_mult
        return hsp

    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        """Calcula el estado del nodo (Regen + Stats + Streak Reset)"""
        now = time.time()
        last_regen = float(node.get("last_regen", now))
        elapsed = now - last_regen
        
        balance = float(node.get("honey", 0))
        refs_count = len(node.get("referrals") or [])
        joined_at = float(node.get("joined_at", now))
        
        # 1. Calc IIL
        iil_score = HiveSynergyEngine.calculate_iil(balance, refs_count, joined_at)
        node["iil"] = iil_score
        
        # 2. Determinar Rango
        poder_total = balance + (refs_count * CONST["BONO_REFERIDO"])
        rango = "LARVA"
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder_total >= data["meta_hive"]:
                rango = nombre
                stats = data
        
        node["caste"] = rango
        node["max_polen"] = stats["max_energia"]
        
        # 3. Regen Energía (Basado en IIL)
        if elapsed > 0:
            base_regen = 0.8
            final_regen = base_regen * (iil_score * 0.5)
            if final_regen < 0.1: final_regen = 0.1
            
            regen_amt = elapsed * final_regen
            current_polen = float(node.get("polen", 0))
            node["polen"] = min(node["max_polen"], current_polen + int(regen_amt))
            
        node["last_regen"] = now
        
        # 4. Streak Check (Reset si pasa 24h sin tap)
        last_tap = float(node.get("last_tap", 0))
        if now - last_tap > 86400: # 24h
             node["streak"] = 0
             
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
    
    txt = f"{get_text(lang, 'protect_title', reason=reason)}\n\n{get_text(lang, 'protect_body')}\n\n`{code}`"
    await smart_edit(update, txt, InlineKeyboardMarkup([]))

# ==============================================================================
# STARTUP
# ==============================================================================
async def on_startup(application: Application):
    logger.info("🚀 INICIANDO SISTEMA HIVE V13.1 (FULL MONOLITH)")
    await db.connect() 

async def on_shutdown(application: Application):
    await db.close()

# ==============================================================================
# FLUJOS PRINCIPALES
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code
    args = context.args
    ref_id = int(args[0]) if args and args[0].isdigit() else None
    
    try: await db.create_node(user.id, user.first_name, user.username, ref_id)
    except: pass
    
    txt = get_text(lang, "intro_caption")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_enter"), callback_data="intro_step_2")]]
    
    try: await update.message.reply_photo(IMG_GENESIS, caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def intro_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = q.from_user.language_code
    await q.answer("...")
    await asyncio.sleep(0.5)
    try: await q.message.delete()
    except: pass

    txt = get_text(lang, "intro_step2")
    kb = [[InlineKeyboardButton(get_text(lang, "btn_status"), callback_data="go_dash")]]
    await q.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

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
        
        try: await db.create_node(uid, user.first_name, user.username)
        except: pass
        
        node = await db.get_node(uid)
        if not node: return 

        # ENGINE UPDATE V13
        node = HiveSynergyEngine.calculate_state(node)
        hsp = await HiveSynergyEngine.calculate_hsp(node) 
        node["hsp"] = hsp
        await db.save_node(uid, node)
        
        rango = node['caste']
        info = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])
        status_msg = get_text(lang, "status_unsafe") if not node.get("email") else get_text(lang, "status_safe")
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        bar = render_bar(polen, max_p)
        
        header = get_text(lang, "dash_header")
        lbl_e = get_text(lang, "lbl_energy")
        lbl_h = get_text(lang, "lbl_honey")
        lbl_hsp = get_text(lang, "hsp_lbl", hsp=hsp)
        lbl_str = get_text(lang, "streak_lbl", streak=node.get("streak", 0))
        lbl_f = get_text(lang, "lbl_feed")
        footer = get_text(lang, "footer_msg")
        live = generate_live_feed(lang)
        
        txt = (
            f"{header} | {info['icono']} **{rango}**\n"
            f"────────────────\n"
            f"{status_msg}\n\n"
            f"{lbl_e}: `{bar}`\n"
            f"{lbl_h}: `{node['honey']:.4f}`\n"
            f"{lbl_hsp}\n"
            f"{lbl_str}\n\n"
            f"{lbl_f}\n{live}\n\n"
            f"{footer}\n"
            f"────────────────"
        )
        
        kb = [
            [InlineKeyboardButton(get_text(lang, "btn_mine"), callback_data="forage")],
            [InlineKeyboardButton("🧠 PREDS", callback_data="preds"), InlineKeyboardButton("🔥 COMBO", callback_data="combo")],
            [InlineKeyboardButton("🏆 TOP", callback_data="lb"), InlineKeyboardButton(get_text(lang, "btn_squad"), callback_data="squad")],
            [InlineKeyboardButton(get_text(lang, "btn_tasks"), callback_data="tasks"), InlineKeyboardButton(get_text(lang, "btn_shop"), callback_data="shop")],
            [InlineKeyboardButton(get_text(lang, "btn_team"), callback_data="team")]
        ]
        await smart_edit(update, txt, InlineKeyboardMarkup(kb))
    except Exception as e: logger.error(f"Dash Error: {e}")

# ==============================================================================
# ACCIONES V13 (GAMIFICATION + RATE LIMIT)
# ==============================================================================

async def forage_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; uid = q.from_user.id
        node = await db.get_node(uid)
        
        # RATE LIMIT MANUAL (Anti-bot V13)
        now = time.time()
        last_tap = float(node.get("last_tap", 0))
        if now - last_tap < CONST["TAP_RATE_LIMIT"]:
            await q.answer("⏳ Chill...", show_alert=False)
            return

        node = HiveSynergyEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Low Energy", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_tap'] = now
        
        # V13 FORMULA: Base * Rango * HSP * Streak
        rango_bonus = RANGOS_CONFIG[node['caste']]['bonus_tap']
        hsp = await HiveSynergyEngine.calculate_hsp(node)
        streak = int(node.get("streak", 0))
        streak_mult = CONST["STREAK_BONUS"] ** min(streak, 10) # Cap streak bonus exp
        
        yield_amt = CONST['RECOMPENSA_BASE'] * rango_bonus * hsp * streak_mult
        
        node['honey'] += yield_amt
        node['streak'] = streak + 1 # Increment streak
        
        # NITRO TAP (Respuesta inmediata)
        await q.answer(f"✅ +{yield_amt:.4f} (Combo x{streak})")
        
        await db.save_node(uid, node)
        
        # Update visual aleatorio (Anti-Lag)
        if random.random() < 0.1: 
            await show_dashboard(update, context)
            
    except Exception: pass

# --- NUEVAS FUNCIONES GAMIFICADAS ---

async def daily_combo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    combo = generate_daily_combo()
    context.user_data['daily_combo'] = combo
    context.user_data['waiting_combo'] = True
    
    txt = get_text(lang, "daily_combo", combo=combo)
    kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def predictions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    evento = await get_evento_diario()
    context.user_data['evento'] = evento
    
    txt = get_text(lang, "predictions", evento=evento['desc'])
    kb = [
        [InlineKeyboardButton("✅ SÍ", callback_data="pred_si"), InlineKeyboardButton("❌ NO", callback_data="pred_no")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def pred_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, vote: str):
    lang = update.callback_query.from_user.language_code
    # Aquí se guardaría el voto en DB real
    await update.callback_query.answer(get_text(lang, "pred_vote_ok"), show_alert=True)
    await show_dashboard(update, context)

async def leaderboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    # Simulamos datos (en prod usar DB ZSET)
    top10 = "1. AlphaNode: 154 HSP\n2. BetaUser: 120 HSP\n3. Gamma: 110 HSP"
    txt = get_text(lang, "leaderboard", top10=top10)
    kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

# --- TEXT HANDLER PARA COMBOS Y EMAIL ---

async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    lang = update.effective_user.language_code
    step = context.user_data.get('step')
    
    if text.upper() == "/START": await start_command(update, context); return

    # COMBO CHECK
    if context.user_data.get('waiting_combo'):
        if text == context.user_data.get('daily_combo'):
            node = await db.get_node(uid)
            bonus = CONST["COMBO_DAILY_REWARD"]
            node['honey'] += bonus
            # Aumentar streak considerablemente por combo
            node['streak'] = int(node.get("streak", 0)) + 5 
            await db.save_node(uid, node)
            await update.message.reply_text(get_text(lang, "combo_success", amt=bonus))
            context.user_data['waiting_combo'] = False
            return
        # Si falla, no hace nada (permite reintentar)

    # EMAIL FLOW (EXISTENTE)
    if step == 'captcha_wait':
        if text == context.user_data.get('captcha'):
            context.user_data['step'] = 'consent_wait'
            kb = [[InlineKeyboardButton("✅ OK", callback_data="accept_terms")]]
            await update.message.reply_text("✅ OK", reply_markup=InlineKeyboardMarkup(kb))
        else: await update.message.reply_text("❌")
        return

    if step == 'email_wait':
        try:
            valid = validate_email(text)
            email = valid.normalized
            await db.update_email(uid, email)
            context.user_data['step'] = None
            node = await db.get_node(uid)
            if node:
                node['honey'] += 15.0 
                await db.save_node(uid, node)
            kb = [[InlineKeyboardButton("🟢 CONTINUAR", callback_data="go_dash")]]
            await update.message.reply_text(get_text(lang, "email_success"), reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text("⚠️ Email Error")
        return

    try:
        node = await db.get_node(uid)
        if node: await show_dashboard(update, context)
    except: pass

# --- MENUS CLÁSICOS ---

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
    node = await db.get_node(uid)
    
    # TRIGGER: Pide email si es Tier 2 o 3
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

async def squad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    
    cell_id = node.get("cell_id") or node.get("enjambre_id")
    if cell_id:
        cell = await db.get_cell(cell_id)
        if cell:
            members_count = len(cell.get('members', []))
            txt = get_text(lang, "squad_active", members=members_count)
            kb = [[InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
            await smart_edit(update, txt, InlineKeyboardMarkup(kb))
            return

    txt = f"{get_text(lang, 'squad_none_title')}\n\n{get_text(lang, 'squad_none_body')}"
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_create_squad", cost=CONST['COSTO_ENJAMBRE']), callback_data="mk_cell")],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def create_squad_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    
    # TRIGGER: Email check para Squad
    if not node.get("email"):
        await request_email_protection(update, context, "SQUAD")
        return
        
    if node['honey'] >= CONST['COSTO_ENJAMBRE']:
        node['honey'] -= CONST['COSTO_ENJAMBRE']
        cell_name = f"Hive-{random.randint(100,999)}"
        cell_id = await db.create_cell(uid, cell_name)
        if cell_id:
            node['enjambre_id'] = cell_id
            node['cell_id'] = cell_id
            await db.save_node(uid, node)
            await q.answer("✅"); await squad_menu(update, context)
        else: await q.answer("❌ Error DB", show_alert=True)
    else: await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    # TRIGGER: Email check para Shop
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
    node = await db.get_node(uid)
    if node['honey'] >= CONST['COSTO_RECARGA']:
        node['honey'] -= CONST['COSTO_RECARGA']
        node['polen'] = node['max_polen']
        await db.save_node(uid, node)
        await q.answer("⚡ OK"); await show_dashboard(update, context)
    else: await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.callback_query.from_user.language_code
    txt = get_text(lang, "pay_txt", price=CONST['PRECIO_ACELERADOR'], wallet=WALLET_TRC20_FIJA)
    kb = [
        [InlineKeyboardButton(get_text(lang, "btn_paypal"), url=LINK_PAYPAL_HARDCODED)],
        [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="shop")]
    ]
    await smart_edit(update, txt, InlineKeyboardMarkup(kb))

async def team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)
    # TRIGGER: Email check para Expand
    if not node.get("email"):
        await request_email_protection(update, context, "EXPAND")
        return
    link = f"https://t.me/{context.bot.username}?start={uid}"
    share_url = f"https://t.me/share/url?url={link}"
    txt = get_text(lang, "team_body", bonus=CONST['BONO_REFERIDO'], link=link)
    title = get_text(lang, "team_title")
    kb = [[InlineKeyboardButton("📤 SHARE", url=share_url)], [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, f"{title}\n\n{txt}", InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    lang = q.from_user.language_code

    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await smart_edit(update, get_text(lang, "email_prompt"), InlineKeyboardMarkup([]))
        return

    actions = {
        "intro_step_2": intro_step_2,
        "go_dash": show_dashboard, 
        "forage": forage_action, 
        "tasks": tasks_menu,
        "squad": squad_menu, "mk_cell": create_squad_logic,
        "shop": shop_menu, "buy_energy": buy_energy, "buy_premium": buy_premium, 
        "team": team_menu,
        "v_t1": lambda u,c: view_tier_generic(u, "v_t1", c),
        "v_t2": lambda u,c: view_tier_generic(u, "v_t2", c),
        "v_t3": lambda u,c: view_tier_generic(u, "v_t3", c),
        # ACCIONES V13 GAMIFICADAS
        "combo": daily_combo,
        "preds": predictions_menu,
        "pred_si": lambda u,c: pred_vote(u,c,"si"),
        "pred_no": lambda u,c: pred_vote(u,c,"no"),
        "lb": leaderboard_menu
    }
    
    if d in actions: await actions[d](update, context)
    try: await q.answer()
    except: pass

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 Node Purged")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("V13.1 HSP FULL MONOLITH")
async def broadcast_cmd(u, c): pass
