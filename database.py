import ujson as json
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

# ==============================================================================
# CAPA DE PERSISTENCIA - HIVE CORE (FIXED PRODUCTION)
# ==============================================================================

class DatabaseManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.r: Optional[redis.Redis] = None
        self._max_retries = 5
        self._retry_delay = 2

    async def connect(self):
        """Conexión robusta a Redis."""
        if not self.redis_url:
            logger.critical("❌ REDIS_URL no encontrada.")
            return

        for attempt in range(self._max_retries):
            try:
                self.r = redis.from_url(
                    self.redis_url, 
                    decode_responses=True, 
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                    retry_on_timeout=True
                )
                await self.r.ping()
                logger.success("✅ CONEXIÓN REDIS ESTABLECIDA")
                # Inicializar contadores si no existen
                await self.r.setnx("global:users_count", 0)
                return
            except Exception as e:
                logger.warning(f"⚠️ Fallo Redis ({attempt+1}/{self._max_retries}): {e}")
                await asyncio.sleep(self._retry_delay)
        
        logger.critical("🔥 NO SE PUDO CONECTAR A REDIS.")

    async def close(self):
        if self.r: await self.r.aclose()

    # --- SCHEMAS ---
    @staticmethod
    def _default_user(user_id: int) -> Dict:
        return {
            "id": user_id, "first_name": "", "username": "", "email": None,
            "joined_at": datetime.utcnow().isoformat(),
            "nectar": 0.0, "tokens_locked": 0.0, "usd_balance": 0.0,
            "role": "LARVA", "role_xp": 0.0, "energy": 300, "max_energy": 300,
            "oxygen": 100.0, "last_pulse": time.time(), "last_update_ts": time.time(),
            "entropy_trace": [], "fraud_score": 0, "ban_status": False,
            "cell_id": None, "referrals": [], "referred_by": None, "swarm_power": 1.0,
            "is_premium": False
        }

    @staticmethod
    def _default_cell(owner_id: int, name: str) -> Dict:
        return {
            "id": f"cell:{owner_id}:{int(time.time())}", "owner_id": owner_id, "name": name,
            "members": [owner_id], "synergy_level": 1.05, "total_xp": 0.0,
            "created_at": datetime.utcnow().isoformat()
        }

    # --- MÉTODOS DE USUARIO (Coincidentes con bot_logic) ---

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Obtiene un usuario."""
        if not self.r: return None
        data = await self.r.get(f"user:{user_id}")
        if not data: return None
        
        user = json.loads(data)
        # Migración defensiva
        defaults = self._default_user(user_id)
        dirty = False
        for k, v in defaults.items():
            if k not in user:
                user[k] = v
                dirty = True
        if dirty: await self.save_user(user_id, user)
        return user

    async def create_user(self, user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
        """
        Crea un usuario si no existe.
        RENOMBRADO de create_user_if_new a create_user para corregir el error.
        """
        if not self.r: return False
        key = f"user:{user_id}"
        
        if await self.r.exists(key): return False

        new_user = self._default_user(user_id)
        new_user["first_name"] = first_name
        new_user["username"] = username
        new_user["referred_by"] = referrer_id

        async with self.r.pipeline() as pipe:
            pipe.set(key, json.dumps(new_user))
            pipe.incr("global:users_count")
            await pipe.execute()

        if referrer_id:
            await self._process_referral(referrer_id, user_id)
        
        logger.info(f"🆕 Usuario Creado: {user_id}")
        return True

    async def save_user(self, user_id: int, data: Dict):
        """Guarda los datos del usuario."""
        if self.r: await self.r.set(f"user:{user_id}", json.dumps(data))

    async def update_email(self, user_id: int, email: str):
        """Actualiza el email del usuario."""
        user = await self.get_user(user_id)
        if user:
            user["email"] = email
            await self.save_user(user_id, user)
            logger.info(f"📧 Email guardado para {user_id}")

    async def delete_user(self, user_id: int):
        """Elimina un usuario (Reset)."""
        if self.r: await self.r.delete(f"user:{user_id}")

    # --- MÉTODOS DE CÉLULAS ---

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        if not self.r: return None
        cell_data = self._default_cell(owner_id, name)
        cell_id = cell_data["id"]
        await self.r.set(cell_id, json.dumps(cell_data))
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        if not self.r or not cell_id: return None
        data = await self.r.get(cell_id)
        return json.loads(data) if data else None

    async def update_cell(self, cell_id: str, data: Dict):
        if self.r: await self.r.set(cell_id, json.dumps(data))

    # --- INTERNOS ---

    async def _process_referral(self, referrer_id: int, child_id: int):
        if not self.r: return
        try:
            parent = await self.get_user(referrer_id)
            if parent and child_id not in parent["referrals"]:
                parent["referrals"].append(child_id)
                parent["nectar"] += 50.0
                parent["swarm_power"] += 0.05
                await self.save_user(referrer_id, parent)
        except Exception:
            pass

# Instancia Global
db = DatabaseManager()
