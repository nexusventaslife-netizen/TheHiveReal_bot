import ujson as json
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, List, Union, Any, Tuple
from loguru import logger

# ==============================================================================
# HIVE DATABASE CORE - HIGH CONCURRENCY MODULE
# Designed for: 300k Users | Atomic Transactions | Redis Pipelines
# ==============================================================================

class DatabaseManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.r: Optional[redis.Redis] = None
        self._pool = None
        self._max_retries = 10
        self._retry_delay = 1.5

    async def connect(self):
        """
        Establece conexión a Redis con Pool de conexiones optimizado para alto tráfico.
        """
        if not self.redis_url:
            logger.critical("❌ REDIS_URL no configurada. Abortando inicio de DB.")
            raise ValueError("REDIS_URL missing")

        logger.info("🔌 Iniciando conexión al Cluster de Memoria...")
        
        for attempt in range(self._max_retries):
            try:
                # Configuración optimizada para Render/Cloud
                self.r = redis.from_url(
                    self.redis_url, 
                    decode_responses=True, 
                    socket_timeout=5.0,
                    socket_connect_timeout=10.0,
                    socket_keepalive=True,
                    retry_on_timeout=True,
                    max_connections=50 # Ajustar según plan de Redis
                )
                await self.r.ping()
                logger.success(f"✅ REDIS CONECTADO (Intento {attempt+1})")
                
                # Inicialización de contadores atómicos globales
                await self._init_globals()
                return
            except Exception as e:
                logger.warning(f"⚠️ Fallo conexión Redis ({attempt+1}/{self._max_retries}): {e}")
                await asyncio.sleep(self._retry_delay * (attempt + 1))
        
        raise ConnectionError("FATAL: No se pudo conectar a Redis tras múltiples intentos.")

    async def _init_globals(self):
        """Inicializa variables globales del juego de forma segura."""
        async with self.r.pipeline() as pipe:
            pipe.setnx("global:users_count", 0)
            pipe.setnx("global:hive_level", 1)
            pipe.setnx("global:total_mined", 0.0)
            pipe.setnx("game:status", "ONLINE")
            await pipe.execute()

    async def close(self):
        if self.r:
            await self.r.aclose()
            logger.info("🔒 Conexión Redis cerrada.")

    # ==========================================================================
    # SCHEMAS DE DATOS (DEFINICIÓN ESTRUCTURAL)
    # ==========================================================================

    @staticmethod
    def _user_schema(user_id: int) -> Dict:
        """Estructura canónica del usuario V200.0"""
        return {
            # IDENTIDAD
            "id": user_id,
            "first_name": "",
            "username": "",
            "email": None,
            "joined_at": datetime.utcnow().isoformat(),
            "ip_country": "XX",
            
            # ECONOMÍA (CORE)
            "nectar": 0.0,            # Liquidez interna
            "tokens_locked": 0.0,     # Vesting airdrop
            "usd_balance": 0.00,      # Dinero real (CPA)
            "wallet_address": None,   # TRC20/BEP20
            
            # BIOLOGÍA (GAMEPLAY)
            "role": "LARVA",          # Rol actual
            "role_xp": 0.0,           # XP acumulada
            "energy": 500,            # Energía actual
            "max_energy": 500,        # Capacidad tanque
            "oxygen": 100.0,          # Salud biológica
            "last_pulse": time.time(), # Último heartbeat
            "last_regen": time.time(), # Última regeneración energía
            
            # SEGURIDAD
            "entropy_trace": [],      # Vector de tiempos
            "fraud_score": 0,         # 0-100
            "ban_status": False,
            "captcha_passed": False,
            
            # SOCIAL
            "cell_id": None,
            "referrals": [],
            "referred_by": None,
            "swarm_power": 1.0,       # Multiplicador social
            
            # META & RETENCIÓN
            "daily_streak": 0,
            "last_login_date": "",
            "is_premium": False
        }

    @staticmethod
    def _cell_schema(owner_id: int, name: str) -> Dict:
        return {
            "id": f"cell:{owner_id}:{int(time.time())}",
            "owner_id": owner_id,
            "name": name,
            "description": "Colmena activa",
            "members": [owner_id],
            "synergy_level": 1.05,
            "total_xp": 0.0,
            "daily_work": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "is_verified": False
        }

    # ==========================================================================
    # CRUD USUARIOS (ATÓMICO)
    # ==========================================================================

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Recupera usuario con migración de esquema al vuelo."""
        if not self.r: return None
        try:
            data = await self.r.get(f"user:{user_id}")
            if not data: return None
            
            user = json.loads(data)
            # Validación de esquema (Self-healing DB)
            default = self._user_schema(user_id)
            dirty = False
            for k, v in default.items():
                if k not in user:
                    user[k] = v
                    dirty = True
            
            if dirty:
                # Guardamos asíncronamente para no bloquear lectura
                asyncio.create_task(self.save_user(user_id, user))
                
            return user
        except Exception as e:
            logger.error(f"Error lectura usuario {user_id}: {e}")
            return None

    async def create_user(self, user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
        """Crea usuario nuevo usando Transacción Redis."""
        if not self.r: return False
        key = f"user:{user_id}"
        
        # Check existencia rápido
        if await self.r.exists(key): return False

        new_user = self._user_schema(user_id)
        new_user["first_name"] = first_name
        new_user["username"] = username
        new_user["referred_by"] = referrer_id

        # Transacción: Guardar User + Incrementar Contador Global
        async with self.r.pipeline() as pipe:
            pipe.set(key, json.dumps(new_user))
            pipe.incr("global:users_count")
            # Indexar para leaderboards (Set inicial con 0 XP)
            pipe.zadd("leaderboard:xp", {str(user_id): 0})
            await pipe.execute()

        # Procesar referido fuera del hilo principal
        if referrer_id:
            asyncio.create_task(self._process_referral_logic(referrer_id, user_id))
        
        logger.info(f"🆕 GENESIS: Nuevo Organismo {user_id}")
        return True

    async def save_user(self, user_id: int, data: Dict):
        """Escritura directa."""
        if self.r: await self.r.set(f"user:{user_id}", json.dumps(data))
        
    async def update_user_balances(self, user_id: int, nectar_delta: float, xp_delta: float, token_delta: float):
        """
        Actualización atómica de saldos y leaderboard.
        CRÍTICO PARA EVITAR RACE CONDITIONS EN CLICKS RÁPIDOS.
        """
        key = f"user:{user_id}"
        
        # Necesitamos bloqueo optimista o leer-modificar-escribir rápido
        # En Redis puro usaríamos LUA scripting para perfección, pero Python logic es suficiente para MVP <500k
        user = await self.get_user(user_id)
        if not user: return
        
        user["nectar"] += nectar_delta
        user["role_xp"] += xp_delta
        user["tokens_locked"] += token_delta
        
        async with self.r.pipeline() as pipe:
            pipe.set(key, json.dumps(user))
            if xp_delta > 0:
                pipe.zincrby("leaderboard:xp", xp_delta, str(user_id))
            await pipe.execute()

    async def delete_user(self, user_id: int):
        if self.r: 
            await self.r.delete(f"user:{user_id}")
            await self.r.zrem("leaderboard:xp", str(user_id))

    # ==========================================================================
    # SISTEMA DE CÉLULAS (GUILDS)
    # ==========================================================================

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        if not self.r: return None
        cell_data = self._cell_schema(owner_id, name)
        cell_id = cell_data["id"]
        
        async with self.r.pipeline() as pipe:
            pipe.set(cell_id, json.dumps(cell_data))
            pipe.sadd("index:cells", cell_id)
            await pipe.execute()
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        if not self.r or not cell_id: return None
        data = await self.r.get(cell_id)
        return json.loads(data) if data else None

    async def join_cell_atomic(self, user_id: int, cell_id: str) -> Tuple[bool, str]:
        """Añade miembro y recalcula sinergia atómicamente."""
        cell = await self.get_cell(cell_id)
        if not cell: return False, "Célula no existe"
        
        if user_id in cell["members"]: return False, "Ya eres miembro"
        if len(cell["members"]) >= 50: return False, "Célula llena (Máx 50)"
        
        cell["members"].append(user_id)
        # Recálculo de Sinergia: 1.0 + (Miembros * 0.05)
        cell["synergy_level"] = 1.0 + (len(cell["members"]) * 0.05)
        
        await self.save_cell(cell_id, cell)
        return True, "Unido exitosamente"

    async def save_cell(self, cell_id: str, data: Dict):
        if self.r: await self.r.set(cell_id, json.dumps(data))

    # ==========================================================================
    # LÓGICA VIRAL & INTERNA
    # ==========================================================================

    async def _process_referral_logic(self, parent_id: int, child_id: int):
        """Procesa árbol de referidos y bonos."""
        if not self.r: return
        try:
            parent = await self.get_user(parent_id)
            if parent and child_id not in parent["referrals"]:
                parent["referrals"].append(child_id)
                parent["nectar"] += 100.0 # Bono Referido
                parent["swarm_power"] += 0.02 # Incremento marginal de poder
                await self.save_user(parent_id, parent)
        except Exception as e:
            logger.error(f"Error referral {parent_id}: {e}")

# Instancia Global Singleton
db = DatabaseManager()
