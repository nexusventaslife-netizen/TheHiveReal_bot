import ujson as json
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
# AQUI ESTABA EL ERROR, AHORA ESTA Dict INCLUIDO
from typing import Optional, Dict, List, Union, Any
from loguru import logger

# ==============================================================================
# HIVE DATABASE CORE - V303 (FULL STABLE)
# ==============================================================================

class DatabaseManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.r: Optional[redis.Redis] = None
        self._max_retries = 10
        self._retry_delay = 2
        
        # --- ESQUEMA MAESTRO DEL NODO ---
        self.DEFAULT_NODE_SCHEMA = {
            # IDENTIDAD
            "id": 0, "first_name": "", "username": "", "email": None, "joined_at": "",
            
            # BIOLOGÍA
            "caste": None, "polen": 500, "max_polen": 500, "oxygen": 100.0,
            
            # ECONOMÍA
            "honey": 0.0, "honey_vested": 0.0, "real_balance": 0.0,
            
            # CRONOBIOLOGÍA
            "last_pulse": 0, "last_regen": 0, "zumbido_hoy": False,
            
            # SOCIAL
            "cell_id": None, "referrals": [], "padre_id": None, "swarm_power": 1.0,
            
            # SEGURIDAD
            "entropy_trace": [], "verificado": False, "banned": False, "is_premium": False
        }

    async def connect(self):
        if not self.redis_url:
            logger.critical("❌ ERROR: REDIS_URL no encontrada.")
            raise ValueError("REDIS_URL missing")

        for attempt in range(self._max_retries):
            try:
                self.r = redis.from_url(
                    self.redis_url, 
                    decode_responses=True, 
                    socket_timeout=5.0,
                    retry_on_timeout=True,
                    max_connections=100
                )
                await self.r.ping()
                logger.success(f"✅ MEMORIA COLMENA CONECTADA")
                await self._init_globals()
                return
            except Exception as e:
                logger.warning(f"⚠️ Fallo Redis ({attempt+1}): {e}")
                await asyncio.sleep(self._retry_delay)
        
        raise ConnectionError("FATAL: Redis no conecta.")

    async def _init_globals(self):
        async with self.r.pipeline() as pipe:
            pipe.setnx("hive:global:nodes", 0)
            pipe.setnx("hive:global:honey", 0.0)
            await pipe.execute()

    async def close(self):
        if self.r: await self.r.aclose()

    # --- GESTIÓN DE NODOS ---

    async def create_node(self, user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
        if not self.r: return False
        key = f"node:{user_id}"
        
        if await self.r.exists(key): return False

        new_node = self.DEFAULT_NODE_SCHEMA.copy()
        new_node.update({
            "id": user_id, "first_name": first_name, "username": username,
            "joined_at": datetime.utcnow().isoformat(),
            "last_pulse": time.time(), "last_regen": time.time(),
            "padre_id": referrer_id
        })

        async with self.r.pipeline() as pipe:
            pipe.set(key, json.dumps(new_node))
            pipe.incr("hive:global:nodes")
            await pipe.execute()

        if referrer_id:
            asyncio.create_task(self._process_referral_bonus(referrer_id, user_id))
        
        logger.info(f"🧬 NODO CREADO: {user_id}")
        return True

    async def get_node(self, user_id: int) -> Optional[Dict]:
        if not self.r: return None
        try:
            data = await self.r.get(f"node:{user_id}")
            if not data: return None
            
            node = json.loads(data)
            dirty = False
            for k, v in self.DEFAULT_NODE_SCHEMA.items():
                if k not in node:
                    node[k] = v
                    dirty = True
            
            if dirty: await self.save_node(user_id, node)
            return node
        except Exception as e:
            logger.error(f"Error nodo {user_id}: {e}")
            return None

    async def save_node(self, user_id: int, data: Dict):
        if self.r: await self.r.set(f"node:{user_id}", json.dumps(data))

    async def update_email(self, user_id: int, email: str):
        node = await self.get_node(user_id)
        if node:
            node["email"] = email
            node["verificado"] = True
            await self.save_node(user_id, node)

    async def delete_node(self, user_id: int):
        if self.r: await self.r.delete(f"node:{user_id}")

    # --- GESTIÓN DE ENJAMBRES ---

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        if not self.r: return None
        cell_id = f"cell:{owner_id}:{int(time.time())}"
        cell_data = {
            "id": cell_id, "owner_id": owner_id, "name": name,
            "members": [owner_id], "synergy": 1.05,
            "total_honey": 0.0, "created_at": datetime.utcnow().isoformat()
        }
        await self.r.set(cell_id, json.dumps(cell_data))
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        if not self.r or not cell_id: return None
        data = await self.r.get(cell_id)
        return json.loads(data) if data else None

    async def update_cell(self, cell_id: str, data: Dict):
        if self.r: await self.r.set(cell_id, json.dumps(data))

    # --- MÉTRICAS ---

    async def add_global_honey(self, amount: float):
        if self.r and amount > 0:
            await self.r.incrbyfloat("hive:global:honey", amount)

    async def get_global_stats(self) -> Dict:
        if not self.r: return {"nodes": 0, "honey": 0}
        async with self.r.pipeline() as pipe:
            pipe.get("hive:global:nodes")
            pipe.get("hive:global:honey")
            res = await pipe.execute()
        return {"nodes": int(res[0] or 0), "honey": float(res[1] or 0)}

    # --- INTERNOS ---

    async def _process_referral_bonus(self, padre_id: int, hijo_id: int):
        try:
            padre = await self.get_node(padre_id)
            if padre and hijo_id not in padre["referrals"]:
                padre["referrals"].append(hijo_id)
                padre["honey"] += 100.0
                padre["polen"] = padre["max_polen"]
                await self.save_node(padre_id, padre)
        except: pass

# Instancia global
db = DatabaseManager()
