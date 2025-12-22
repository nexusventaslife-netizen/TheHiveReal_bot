import logging
import asyncio
import random
import time
import math
import os
import ujson as json
from typing import Tuple, List, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes, Application
from telegram.error import BadRequest
from loguru import logger
from email_validator import validate_email

# IMPORTAMOS TU BASE DE DATOS REDIS (NO BORRES DATABASE.PY)
from database import db 

# ==============================================================================
# 🐝 THE ONE HIVE: V12.4 (PRODUCTION MASTER - FULL CODE)
# ==============================================================================

logger = logging.getLogger("HiveLogic")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ------------------------------------------------------------------------------
# 💰 ZONA DE PAGOS (CONFIGURACIÓN A FUEGO)
# ------------------------------------------------------------------------------
# 1. ENLACE PAYPAL (FIJO)
LINK_PAYPAL_HARDCODED = "https://www.paypal.com/ncp/payment/L6ZRFT2ACGAQC"

# 2. TU BILLETERA USDT TRC20 (EDITAR AQUÍ ABAJO)
WALLET_TRC20_FIJA = "PEGAR_TU_USDT_TRC20_AQUI" 
# ------------------------------------------------------------------------------

# --- IDENTIDAD VISUAL ---
IMG_GENESIS = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"
IMG_DASHBOARD = "https://i.postimg.cc/W46KZqR6/Gemini-Generated-Image-qm6hoyqm6hoyqm6h-(1).jpg"

# --- CONSTANTES DE ECONOMÍA ---
CONST = {
    "COSTO_POLEN": 10,        
    "RECOMPENSA_BASE": 0.05,
    "DECAY_OXIGENO": 4.0,     
    "COSTO_ENJAMBRE": 100,    
    "COSTO_RECARGA": 50,      
    "BONO_REFERIDO": 500,
    "PRECIO_ACELERADOR": 9.99, # PRECIO MENSUAL
    "TRIGGER_EMAIL_HONEY": 50,
    "SQUAD_MULTIPLIER": 0.05   # 5% extra por amigo
}

# --- JERARQUÍA EVOLUTIVA ---
RANGOS_CONFIG = {
    "LARVA": {
        "nivel": 0, 
        "meta_hive": 0,       
        "max_energia": 200,  
        "bonus_tap": 1.0, 
        "icono": "🐛", 
        "acceso": 0
    },
    "OBRERO": {
        "nivel": 1, 
        "meta_hive": 1000,    
        "max_energia": 400,  
        "bonus_tap": 1.1, 
        "icono": "🐝", 
        "acceso": 1
    },
    "EXPLORADOR": {
        "nivel": 2, 
        "meta_hive": 5000,    
        "max_energia": 800,  
        "bonus_tap": 1.2, 
        "icono": "🔭", 
        "acceso": 2
    },
    "GUARDIAN": {
        "nivel": 3, 
        "meta_hive": 20000,   
        "max_energia": 1500, 
        "bonus_tap": 1.5, 
        "icono": "🛡️", 
        "acceso": 3
    },
    "REINA": {
        "nivel": 4, 
        "meta_hive": 100000,  
        "max_energia": 5000, 
        "bonus_tap": 3.0, 
        "icono": "👑", 
        "acceso": 3
    }
}

# ==============================================================================
# 🌐 MOTOR DE TRADUCCIÓN (NARRATIVA SCALE-LOCK / AUTHORITY)
# ==============================================================================
TEXTS = {
    "es": {
        "intro_caption": "Bienvenido a The One Hive.\n\nEsto no es un airdrop.\nEsto no es una inversión.\n\nEs un sistema vivo midiendo participación e influencia.\n\nEl acceso temprano sigue abierto.\nLas reglas se siguen ajustando.",
        "btn_enter": "👉 Acceder al Sistema",
        "intro_step2": "**AVISO DE RED:**\n\nTu progreso es relativo a la actividad de la red.\n\nLos nodos más activos son priorizados en esta fase.\nLa participación temprana importa.",
        "btn_status": "👉 Verificar Nodo",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NODO ESTÁNDAR",
        "status_safe": "✅ NODO VERIFICADO",
        "lbl_energy": "⚡ Energía (IIL: x{iil:.2f})",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Red:**",
        "footer_msg": "📝 _Prioridad de red calculada en tiempo real._",
        "btn_mine": "⚡ EXTRACT (TAP)",
        "btn_tasks": "🟢 PANALES",
        "btn_rank": "🧬 EVOLUCIÓN",
        "btn_squad": "🐝 CONEXIONES",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ PRIORIDAD ($)",
        "viral_1": "El acceso temprano sigue abierto. Un sistema vivo se está formando. Los que entran antes entienden.\n\n{link}",
        "viral_2": "No todos deberían entrar. El acceso temprano sigue abierto.\n\n{link}",
        "sys_event_1": "ℹ️ Asignando ancho de banda prioritario",
        "sys_event_2": "ℹ️ Nuevos bloques de tareas disponibles",
        "sys_event_3": "ℹ️ Ajustando dificultad de red",
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
        "squad_active": "🐝 **CONEXIÓN ACTIVA**\n👥 Nodos: {members}\n🔥 IIL Boost: ACTIVO",
        "no_balance": "❌ HIVE Insuficiente"
    },
    "en": {
        "intro_caption": "Welcome to The One Hive.\n\nThis is not an airdrop.\nThis is not an investment.\n\nIt’s a live system measuring participation and influence.\n\nEarly access is still open.\nRules are still adjusting.",
        "btn_enter": "👉 Access System",
        "intro_step2": "**NETWORK NOTICE:**\n\nYour progress is relative to network activity.\n\nMore active nodes are being prioritized in this phase.\nEarly participation matters.",
        "btn_status": "👉 Verify Node",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ STANDARD NODE",
        "status_safe": "✅ VERIFIED NODE",
        "lbl_energy": "⚡ Energy (IIL: x{iil:.2f})",
        "lbl_honey": "🍯 Nectar",
        "lbl_feed": "📊 **Network:**",
        "footer_msg": "📝 _Network priority calculated in real-time._",
        "btn_mine": "⚡ EXTRACT (TAP)",
        "btn_tasks": "🟢 HIVES",
        "btn_rank": "🧬 EVOLUTION",
        "btn_squad": "🐝 CONNECTIONS",
        "btn_team": "👥 EXPAND",
        "btn_shop": "🛡️ PRIORITY ($)",
        "viral_1": "Early access is open. A live system is forming. Those who enter early understand.\n\n{link}",
        "viral_2": "Not everyone should enter. Early access is still open.\n\n{link}",
        "sys_event_1": "ℹ️ Allocating priority bandwidth",
        "sys_event_2": "ℹ️ New task blocks available",
        "sys_event_3": "ℹ️ Adjusting network difficulty",
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
        "squad_active": "🐝 **ACTIVE CONNECTION**\n👥 Nodes: {members}\n🔥 IIL Boost: ACTIVE",
        "no_balance": "❌ Insufficient HIVE"
    },
    "ru": {
        "intro_caption": "Добро пожаловать в The One Hive.\n\nЭто не аирдроп.\nЭто не инвестиция.\n\nЭто живая система, измеряющая участие и влияние.",
        "btn_enter": "👉 Доступ к Системе",
        "intro_step2": "**УВЕДОМЛЕНИЕ СЕТИ:**\n\nВаш прогресс зависит от активности сети.\n\nАктивные узлы имеют приоритет.",
        "btn_status": "👉 Проверить Узел",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ СТАНДАРТНЫЙ УЗЕЛ",
        "status_safe": "✅ ПРОВЕРЕННЫЙ УЗЕЛ",
        "lbl_energy": "⚡ Энергия (IIL: x{iil:.2f})",
        "lbl_honey": "🍯 Нектар",
        "lbl_feed": "📊 **Сеть:**",
        "footer_msg": "📝 _Приоритет рассчитывается в реальном времени._",
        "btn_mine": "⚡ ИЗВЛЕЧЬ (TAP)",
        "btn_tasks": "🟢 ЗАДАНИЯ",
        "btn_rank": "🧬 ЭВОЛЮЦИЯ",
        "btn_squad": "🐝 СВЯЗИ",
        "btn_team": "👥 РАСШИРЕНИЕ",
        "btn_shop": "🛡️ ПРИОРИТЕТ ($)",
        "viral_1": "Ранний доступ открыт. Те, кто заходят раньше, понимают.\n\n{link}",
        "viral_2": "Не всем стоит заходить. Ранний доступ открыт.\n\n{link}",
        "sys_event_1": "ℹ️ Приоритет переназначен активным узлам",
        "sys_event_2": "ℹ️ Окно расширения открыто",
        "sys_event_3": "ℹ️ Емкость фазы на пределе",
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
        "squad_active": "🐝 **АКТИВНАЯ СВЯЗЬ**\n👥 Узлы: {members}\n🔥 IIL Boost: АКТИВЕН",
        "no_balance": "❌ Недостаточно HIVE"
    },
    "zh": {
        "intro_caption": "欢迎来到 The One Hive。\n\n这不是空投。\n这不是投资。\n\n这是一个衡量参与度和影响力的实时系统。",
        "btn_enter": "👉 访问系统",
        "intro_step2": "**网络通知：**\n\n您的进度与网络活动相关。\n\n在此阶段优先考虑更活跃的节点。",
        "btn_status": "👉 验证节点",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ 标准节点",
        "status_safe": "✅ 已验证节点",
        "lbl_energy": "⚡ 能量 (IIL: x{iil:.2f})",
        "lbl_honey": "🍯 花蜜",
        "lbl_feed": "📊 **网络:**",
        "footer_msg": "📝 _实时计算网络优先级。_",
        "btn_mine": "⚡ 提取 (TAP)",
        "btn_tasks": "🟢 任务",
        "btn_rank": "🧬 进化",
        "btn_squad": "🐝 连接",
        "btn_team": "👥 扩张",
        "btn_shop": "🛡️ 优先 ($)",
        "viral_1": "早期访问已开放。那些早进入的人明白。\n\n{link}",
        "viral_2": "不是每个人都应该进入。早期访问仍然开放。\n\n{link}",
        "sys_event_1": "ℹ️ 优先级重新分配给活跃节点",
        "sys_event_2": "ℹ️ 扩张窗口开启",
        "sys_event_3": "ℹ️ 阶段容量接近极限",
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
        "squad_active": "🐝 **活跃连接**\n👥 节点: {members}\n🔥 IIL Boost: 活跃",
        "no_balance": "❌ HIVE 不足"
    },
    "pt": {
        "intro_caption": "Bem-vindo ao The One Hive.\n\nIsto não é um airdrop.\nIsto não é investimento.\n\nÉ um sistema vivo medindo participação e influência.",
        "btn_enter": "👉 Acessar Sistema",
        "intro_step2": "**AVISO DE REDE:**\n\nSeu progresso é relativo à atividade da rede.\n\nNós mais ativos são priorizados nesta fase.",
        "btn_status": "👉 Verificar Nó",
        "dash_header": "🏰 **THE ONE HIVE**",
        "status_unsafe": "⚠️ NÓ PADRÃO",
        "status_safe": "✅ NÓ VERIFICADO",
        "lbl_energy": "⚡ Energia (IIL: x{iil:.2f})",
        "lbl_honey": "🍯 Néctar",
        "lbl_feed": "📊 **Rede:**",
        "footer_msg": "📝 _Prioridade de rede calculada em tempo real._",
        "btn_mine": "⚡ EXTRAIR (TAP)",
        "btn_tasks": "🟢 FAVOS",
        "btn_rank": "🧬 EVOLUÇÃO",
        "btn_squad": "🐝 CONEXÕES",
        "btn_team": "👥 EXPANDIR",
        "btn_shop": "🛡️ PRIORIDADE ($)",
        "viral_1": "Acesso antecipado aberto. Um sistema vivo está se formando. Quem entra cedo entende.\n\n{link}",
        "viral_2": "Nem todos devem entrar. Acesso antecipado ainda aberto.\n\n{link}",
        "sys_event_1": "ℹ️ Prioridade reatribuída a nós ativos",
        "sys_event_2": "ℹ️ Janela de expansão aberta",
        "sys_event_3": "ℹ️ Capacidade da fase atingindo limite",
        "feed_action_1": "assegurou posição",
        "feed_action_2": "expandiu conexão",
        "lock_msg": "🔒 FASE RESTRITA. Nível {lvl} necessário.",
        "protect_title": "⚠️ **SEGURE SEU NÓ: {reason}**",
        "protect_body": "Ao registrar um email:\n• Preserva seu progresso\n• Recebe atualizações\n\nNão vendemos contas.",
        "email_prompt": "🛡️ **REGISTRO DE NÓ**\n\nDigite EMAIL para garantir persistência:",
        "email_success": "✅ **NÓ ASSEGURADO**",
        "shop_title": "🛡️ **ACESSO PRIORITÁRIO MENSAL**",
        "shop_body": "Esta assinatura melhora velocidade e acesso.\nNão garante ganhos.\n\nInclui (30 Dias):\n✅ Regeneração mais rápida\n✅ Acesso a tarefas avançadas",
        "btn_buy_prem": "🛡️ PRIORIDADE (30 DIAS) - ${price}",
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
        "squad_active": "🐝 **CONEXÃO ATIVA**\n👥 Nós: {members}\n🔥 IIL Boost: ATIVO",
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
# BIO ENGINE (FACTOR X: IIL + TYPE SAFETY)
# ==============================================================================
class BioEngine:
    @staticmethod
    def calculate_iil(balance: float, refs_count: int, joined_at: float) -> float:
        """
        Calcula el Índice de Influencia Latente (IIL)
        IIL = (log(1 + actividad) * 0.4) + (log(1 + referidos) * 0.4) + (dias * 0.2)
        """
        days_alive = (time.time() - joined_at) / 86400
        if days_alive < 0: days_alive = 0
        
        # Logaritmos para suavizar el crecimiento (Scale-Lock)
        act_score = math.log1p(balance) * 0.4
        ref_score = math.log1p(refs_count) * 0.4
        time_score = days_alive * 0.2
        
        iil = 1.0 + act_score + ref_score + time_score
        return iil

    @staticmethod
    def calculate_state(node: Dict) -> Dict:
        now = time.time()
        
        # Validación de tipos
        last_regen = node.get("last_regen", now)
        if not isinstance(last_regen, (int, float)): last_regen = now
        elapsed = now - last_regen
        
        balance = float(node.get("honey", 0))
        refs_list = node.get("referrals") or []
        refs_count = len(refs_list)
        
        joined_at_raw = node.get("joined_at", now)
        try: joined_at = float(joined_at_raw)
        except: joined_at = float(now)
            
        iil_score = BioEngine.calculate_iil(balance, refs_count, joined_at)
        node["iil_score"] = iil_score 

        poder_total = balance + (refs_count * CONST["BONO_REFERIDO"])
        multiplicador_squad = 1.0 + (refs_count * CONST["VIRAL_FACTOR"])
        if multiplicador_squad > 5.0: multiplicador_squad = 5.0
        node["squad_multiplier"] = multiplicador_squad 
        
        rango = "LARVA"
        stats = RANGOS_CONFIG["LARVA"]
        for nombre, data in RANGOS_CONFIG.items():
            if poder_total >= data["meta_hive"]:
                rango = nombre
                stats = data
        
        node["caste"] = rango 
        if "max_polen" not in node: node["max_polen"] = 500
        node["max_polen"] = stats["max_energia"]
        
        if elapsed > 0:
            base_regen_rate = 0.8
            final_regen_rate = base_regen_rate * (iil_score * 0.5) 
            if final_regen_rate < 0.1: final_regen_rate = 0.1
            
            regen_amount = elapsed * final_regen_rate
            current_polen = float(node.get("polen", 0))
            node["polen"] = min(node["max_polen"], current_polen + int(regen_amount))
            
        node["last_regen"] = now
        node["synergy"] = multiplicador_squad
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
    logger.info("🚀 INICIANDO SISTEMA HIVE V12.4 (PRODUCTION MASTER)")
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
    await asyncio.sleep(0.8)
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
            # Muestra el botón para aceptar términos que dispara el pedido de email
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

        node = BioEngine.calculate_state(node)
        await db.save_node(uid, node)
        
        rango = node['caste']
        info = RANGOS_CONFIG.get(rango, RANGOS_CONFIG["LARVA"])
        status_msg = get_text(lang, "status_unsafe") if not node.get("email") else get_text(lang, "status_safe")
        
        polen = int(node['polen'])
        max_p = int(node['max_polen'])
        iil = node.get("iil", 1.0)
        bar = render_bar(polen, max_p)
        
        header = get_text(lang, "dash_header")
        lbl_e = get_text(lang, "lbl_energy", iil=iil)
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
    node = await db.get_node(uid)
    
    # TRIGGER: Solo pide email aquí si es Tier 2 o Tier 3
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
        node = await db.get_node(uid)
        node = BioEngine.calculate_state(node)
        
        if node['polen'] < CONST['COSTO_POLEN']:
            await q.answer("⚡ Low Energy. Increase IIL.", show_alert=True); return

        node['polen'] -= CONST['COSTO_POLEN']
        node['last_pulse'] = time.time()
        yield_amt = CONST['RECOMPENSA_BASE'] * RANGOS_CONFIG[node['caste']]['bonus_tap']
        
        iil = node.get("iil", 1.0)
        yield_amt *= (iil * 0.2) + 0.8 
        
        node['honey'] += yield_amt
        
        # NITRO TAP: Responder antes de guardar
        await q.answer(f"✅ +{yield_amt:.4f}")

        # Guardar en DB
        await db.save_node(uid, node)
        
        # Solo actualiza visualmente el 5% de las veces para evitar Lag
        if random.random() < 0.05: 
            await show_dashboard(update, context)
            
    except Exception: pass

async def rank_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_dashboard(update, context) 

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
    
    # TRIGGER: Pide email para CREAR SQUAD (escalar)
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
        else:
            await q.answer("❌ Error DB", show_alert=True)
            
    else: 
        await q.answer(get_text(lang, "no_balance"), show_alert=True)

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    lang = q.from_user.language_code
    node = await db.get_node(uid)

    # TRIGGER: Pide email para PAGAR (Shop)
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

    # TRIGGER: Pide email para EXPANDIR (Referidos)
    if not node.get("email"):
        await request_email_protection(update, context, "EXPAND")
        return

    link = f"https://t.me/{context.bot.username}?start={uid}"
    share_url = f"https://t.me/share/url?url={link}"
    
    txt = get_text(lang, "team_body", bonus=CONST['BONO_REFERIDO'], link=link)
    title = get_text(lang, "team_title")
    kb = [[InlineKeyboardButton("📤 SHARE LINK", url=share_url)], [InlineKeyboardButton(get_text(lang, "btn_back"), callback_data="go_dash")]]
    await smart_edit(update, f"{title}\n\n{txt}", InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    lang = q.from_user.language_code

    # --- LÓGICA DE CAPTCHA/EMAIL FIXED ---
    if d == "accept_terms":
        context.user_data['step'] = 'email_wait'
        await smart_edit(update, get_text(lang, "email_prompt"), InlineKeyboardMarkup([]))
        return
    # -------------------------------------

    if d == "intro_step_2": await intro_step_2(update, context); return

    actions = {
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
    await db.delete_node(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("💀 Node Purged")

async def invite_cmd(u, c): await team_menu(u, c)
async def help_cmd(u, c): await u.message.reply_text("V12.4 PROD FINAL")
async def broadcast_cmd(u, c): pass
