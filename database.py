import os
import ujson as json
import time
import asyncio
from typing import Optional, Dict, List, Any
from redis import asyncio as aioredis
from loguru import logger

# CONFIGURACIÓN REDIS
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class Database:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.local_cache = {}

    async def connect(self):
        """Conecta al pool de Redis"""
        try:
            self.redis = aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=100
            )
            await self.redis.ping()
            logger.success(f"✅ REDIS CONECTADO: {REDIS_URL.split('@')[-1]}")
        except Exception as e:
            logger.critical(f"❌ FALLO CONEXIÓN REDIS: {e}")
            raise e

    async def close(self):
        """Cierra la conexión"""
        if self.redis:
            await self.redis.close()
            logger.info("🔒 Redis cerrado")

    # --- NODOS (USUARIOS) ---

    async def create_node(self, uid: int, first_name: str, username: str, ref_id: Optional[int] = None):
        """Crea o actualiza un nodo básico"""
        key = f"node:{uid}"
        exists = await self.redis.exists(key)
        
        if not exists:
            # Estructura inicial V13
            node_data = {
                "uid": uid,
                "first_name": first_name,
                "username": username or "",
                "honey": 0.0,
                "polen": 200.0,     # Max inicial
                "max_polen": 200.0,
                "last_regen": time.time(),
                "joined_at": time.time(),
                "caste": "LARVA",
                "hsp": 1.0,         # Nuevo HSP
                "streak": 0,        # Nuevo Streak
                "last_tap": 0.0,
                "email": "",
                "squad_id": ""
            }
            await self.redis.hset(key, mapping=node_data)
            
            # Gestionar referido
            if ref_id and ref_id != uid:
                # Verificar si el referrer existe
                if await self.redis.exists(f"node:{ref_id}"):
                    await self.redis.rpush(f"refs:{ref_id}", uid)
                    # Bonus simple al referrer
                    await self.redis.hincrbyfloat(f"node:{ref_id}", "honey", 500.0)
            
            # Añadir al set global de usuarios
            await self.redis.sadd("global:users", uid)
            logger.info(f"✨ Nuevo Nodo Creado: {uid}")

    async def get_node(self, uid: int) -> Optional[Dict]:
        """Obtiene datos del nodo. Retorna Dict o None"""
        key = f"node:{uid}"
        data = await self.redis.hgetall(key)
        if not data: return None
        
        # Conversión de tipos críticos
        try:
            data['honey'] = float(data.get('honey', 0))
            data['polen'] = float(data.get('polen', 200))
            data['max_polen'] = float(data.get('max_polen', 200))
            data['hsp'] = float(data.get('hsp', 1.0))
            data['last_regen'] = float(data.get('last_regen', time.time()))
            data['last_tap'] = float(data.get('last_tap', 0))
            data['streak'] = int(data.get('streak', 0))
            data['uid'] = int(data.get('uid', uid))
            # Cargar referidos (lazy load si es necesario, o solo count)
            # data['referrals'] = await self.redis.lrange(f"refs:{uid}", 0, -1) 
        except Exception as e:
            logger.error(f"Error parsing node {uid}: {e}")
        
        # Obtener lista de referidos ID
        refs = await self.redis.lrange(f"refs:{uid}", 0, -1)
        data['referrals'] = [int(x) for x in refs]
        
        return data

    async def save_node(self, uid: int, data: Dict):
        """Guarda estado del nodo + Actualiza Leaderboard"""
        key = f"node:{uid}"
        # Convertir listas/complejos a str si es necesario (Redis HSET es flat)
        save_data = data.copy()
        if 'referrals' in save_data: del save_data['referrals'] # No guardar lista en hash
        
        await self.redis.hset(key, mapping=save_data)
        
        # ACTUALIZAR LEADERBOARD HSP (ZSET)
        if 'hsp' in data:
            await self.redis.zadd("leaderboard:hsp", {str(data['username'] or uid): float(data['hsp'])})

    async def update_email(self, uid: int, email: str):
        await self.redis.hset(f"node:{uid}", "email", email)

    async def delete_node(self, uid: int):
        """Reset total (Danger Zone)"""
        await self.redis.delete(f"node:{uid}")
        await self.redis.delete(f"refs:{uid}")
        await self.redis.zrem("leaderboard:hsp", str(uid))

    # --- SQUADS (ENJAMBRES) ---

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        cell_id = f"cell:{owner_id}" # ID simple basado en owner
        if await self.redis.exists(cell_id): return cell_id
        
        data = {
            "id": cell_id,
            "name": name,
            "owner": owner_id,
            "created_at": time.time(),
            "pred_acc": 0.0 # Accuracy de predicciones del squad
        }
        await self.redis.hset(cell_id, mapping=data)
        await self.redis.sadd(f"squad_members:{cell_id}", owner_id)
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        data = await self.redis.hgetall(cell_id)
        if not data: return None
        # Traer miembros
        members = await self.redis.smembers(f"squad_members:{cell_id}")
        data['members'] = list(members)
        return data

    async def join_cell(self, uid: int, cell_id: str):
        await self.redis.sadd(f"squad_members:{cell_id}", uid)
        await self.redis.hset(f"node:{uid}", "squad_id", cell_id)

    # --- LEADERBOARD & UTILS ---

    async def get_global_stats(self):
        return {
            "nodes": await self.redis.scard("global:users") or 0,
            "top_hsp": await self.redis.zrange("leaderboard:hsp", 0, 0, desc=True, withscores=True)
        }
    
    # Métodos proxy para raw access si se necesita
    async def zrevrange(self, key: str, start: int, end: int, withscores=False):
        return await self.redis.zrange(key, start, end, desc=True, withscores=withscores)
    
    async def set(self, key: str, value: Any, ex: int = None):
        await self.redis.set(key, value, ex=ex)

    async def exists(self, key: str):
        return await self.redis.exists(key)

# INSTANCIA GLOBAL
db = Database()
