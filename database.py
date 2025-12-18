import ujson as json
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, List, Union, Any
from loguru import logger

# ==============================================================================
# CAPA DE PERSISTENCIA - HIVE CORE V200.0 (FIXED)
# ==============================================================================

class DatabaseManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.r: Optional[redis.Redis] = None
        self._max_retries = 5
        self._retry_delay = 2

    async def connect(self):
        """Conexión robusta con reintentos."""
        if not self.redis_url:
            logger.critical("❌ REDIS_URL no encontrada en variables de entorno.")
            # No levantamos excepción aquí para permitir que el bot arranque y muestre error en logs
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
                
                # Inicializar contadores globales si no existen
                await self.r.setnx("global:users_count", 0)
                return
            except Exception as e:
                logger.warning(f"⚠️ Fallo conexión Redis (Intento {attempt+1}/{self._max_retries}): {e}")
                await asyncio.sleep(self._retry_delay * (attempt + 1))
        
        logger.critical("🔥 NO SE PUDO CONECTAR A REDIS TRAS VARIOS INTENTOS.")

    async def close(self):
        if self.r:
            await self.r.aclose()
            logger.info("🔒 Conexión Redis cerrada.")

    # --- MODELOS DE DATOS ---

    @staticmethod
    def _get_default_user_schema(user_id: int) -> Dict:
        return {
            # IDENTIDAD
            "id": user_id,
            "first_name": "",
            "username": "",
            "email": None,
            "joined_at": datetime.utcnow().isoformat(),
            
            # ECONOMÍA
            "nectar": 0.0,            
            "tokens_locked": 0.0,     
            "usd_balance": 0.00,      
            
            # BIOLOGÍA (GAMEPLAY)
            "role": "LARVA",
            "role_xp": 0.0,
            "energy": 300,
            "max_energy": 300,
            "oxygen": 100.0,
            "last_pulse": time.time(),
            "last_update_ts": time.time(),
            
            # ANTI-FRAUDE
            "entropy_trace": [],
            "fraud_score": 0,
            "ban_status": False,
            
            # SOCIAL
            "cell_id": None,
            "referrals": [],
            "referred_by": None,
            "swarm_power": 1.0,
            
            # META
            "is_premium": False
        }

    @staticmethod
    def _get_default_cell_schema(owner_id: int, name: str) -> Dict:
        return {
            "id": f"cell:{owner_id}:{int(time.time())}",
            "owner_id": owner_id,
            "name": name,
            "members": [owner_id],
            "synergy_level": 1.05,
            "total_xp": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "is_verified": False
        }

    # --- OPERACIONES CRUD USUARIOS ---

    async def get_user(self, user_id: int) -> Optional[Dict]:
        if not self.r: return None
        try:
            data = await self.r.get(f"user:{user_id}")
            if not data: return None
            
            user = json.loads(data)
            # Migración defensiva: asegurar que existan todas las claves
            default = self._get_default_user_schema(user_id)
            updated = False
            for k, v in default.items():
                if k not in user:
                    user[k] = v
                    updated = True
            
            if updated:
                await self.save_user(user_id, user) 
            return user
        except Exception as e:
            logger.error(f"Error recuperando usuario {user_id}: {e}")
            return None

    async def create_user_if_new(self, user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
        if not self.r: return False
        key = f"user:{user_id}"
        
        if await self.r.exists(key):
            return False # Ya existe

        new_user = self._get_default_user_schema(user_id)
        new_user["first_name"] = first_name
        new_user["username"] = username
        new_user["referred_by"] = referrer_id

        async with self.r.pipeline() as pipe:
            pipe.set(key, json.dumps(new_user))
            pipe.incr("global:users_count")
            await pipe.execute()

        # Procesar referido asíncronamente
        if referrer_id:
            await self._process_referral(referrer_id, user_id)
        
        logger.info(f"🆕 Nuevo Usuario Registrado: {user_id}")
        return True

    async def save_user(self, user_id: int, data: Dict):
        if self.r: await self.r.set(f"user:{user_id}", json.dumps(data))

    async def delete_user(self, user_id: int):
        """Hard reset para testing."""
        if self.r: 
            await self.r.delete(f"user:{user_id}")
            logger.warning(f"🗑️ Usuario {user_id} eliminado de DB.")

    async def update_email(self, user_id: int, email: str):
        """
        [CORREGIDO] Función faltante que causaba el error.
        Actualiza el email del usuario y guarda el estado.
        """
        user = await self.get_user(user_id)
        if user:
            user["email"] = email
            await self.save_user(user_id, user)
            logger.info(f"📧 Email actualizado para {user_id}: {email}")

    # --- OPERACIONES CRUD CÉLULAS ---

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        if not self.r: return None
        cell_data = self._get_default_cell_schema(owner_id, name)
        cell_id = cell_data["id"]
        
        await self.r.set(cell_id, json.dumps(cell_data))
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        if not self.r or not cell_id: return None
        data = await self.r.get(cell_id)
        return json.loads(data) if data else None

    async def update_cell(self, cell_id: str, data: Dict):
        if self.r: await self.r.set(cell_id, json.dumps(data))

    # --- OPERACIONES INTERNAS ---

    async def _process_referral(self, referrer_id: int, child_id: int):
        """Lógica viral segura."""
        if not self.r: return
        try:
            parent = await self.get_user(referrer_id)
            if parent and child_id not in parent["referrals"]:
                parent["referrals"].append(child_id)
                parent["nectar"] += 50.0 # Bono por referido
                parent["swarm_power"] += 0.05 # Sube el multiplicador
                await self.save_user(referrer_id, parent)
        except Exception as e:
            logger.error(f"Error procesando referido {referrer_id}: {e}")

# Instancia Global
db = DatabaseManager()
