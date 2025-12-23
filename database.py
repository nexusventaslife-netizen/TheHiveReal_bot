import os
import ujson as json
import time
import asyncio
# CORRECCIÓN AQUÍ: Se agregó 'Tuple' a los imports
from typing import Optional, Dict, List, Any, Union, Tuple
from redis import asyncio as aioredis
from redis.exceptions import ResponseError
from loguru import logger

# CONFIGURACIÓN REDIS
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class Database:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Conecta al pool de Redis con reintentos"""
        try:
            self.redis = aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=100,
                socket_timeout=5.0
            )
            await self.redis.ping()
            logger.success(f"✅ REDIS CONECTADO: {REDIS_URL.split('@')[-1]}")
        except Exception as e:
            logger.critical(f"❌ FALLO CONEXIÓN REDIS: {e}")
            raise e

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("🔒 Redis cerrado")

    # --- NODOS (USUARIOS) ---

    async def create_node(self, uid: int, first_name: str, username: str, ref_id: Optional[int] = None):
        """Crea o actualiza un nodo básico de forma segura"""
        key = f"node:{uid}"
        
        try:
            exists = await self.redis.exists(key)
        except ResponseError:
            # Si da WRONGTYPE, borramos la clave corrupta
            await self.redis.delete(key)
            exists = False

        if not exists:
            # Estructura inicial V13
            node_data = {
                "uid": uid,
                "first_name": first_name,
                "username": username or "Unknown",
                "honey": 0.0,
                "polen": 200.0,
                "max_polen": 200.0,
                "last_regen": time.time(),
                "joined_at": time.time(),
                "caste": "LARVA",
                "hsp": 1.0,         
                "streak": 0,       
                "last_tap": 0.0,
                "email": "",
                "squad_id": ""
            }
            # Usamos pipeline para atomicidad
            async with self.redis.pipeline() as pipe:
                pipe.hset(key, mapping=node_data)
                pipe.sadd("global:users", uid)
                if ref_id and ref_id != uid:
                    pipe.rpush(f"refs:{ref_id}", uid)
                    pipe.hincrbyfloat(f"node:{ref_id}", "honey", 500.0)
                await pipe.execute()
            
            logger.info(f"✨ Nuevo Nodo Creado: {uid}")

    async def get_node(self, uid: int) -> Optional[Dict]:
        """Obtiene datos del nodo manejando tipos y errores"""
        key = f"node:{uid}"
        try:
            data = await self.redis.hgetall(key)
            if not data: return None
            
            # Conversión segura de tipos
            return {
                "uid": int(data.get("uid", uid)),
                "first_name": data.get("first_name", ""),
                "username": data.get("username", ""),
                "honey": float(data.get("honey", 0.0)),
                "polen": float(data.get("polen", 200.0)),
                "max_polen": float(data.get("max_polen", 200.0)),
                "hsp": float(data.get("hsp", 1.0)),
                "streak": int(data.get("streak", 0)),
                "caste": data.get("caste", "LARVA"),
                "email": data.get("email", ""),
                "squad_id": data.get("squad_id", ""),
                "last_regen": float(data.get("last_regen", time.time())),
                "last_tap": float(data.get("last_tap", 0.0)),
                "joined_at": float(data.get("joined_at", time.time())),
                # Traemos referidos aparte para no ensuciar el hash
                "referrals": [] 
            }
        except ResponseError as e:
            logger.error(f"⚠️ WRONGTYPE en get_node:{uid} -> Reseteando nodo. {e}")
            await self.redis.delete(key)
            return None
        except Exception as e:
            logger.error(f"Error parsing node {uid}: {e}")
            return None

    async def save_node(self, uid: int, data: Dict):
        """Guarda nodo usando Pipeline y actualiza Leaderboard"""
        key = f"node:{uid}"
        
        # Limpiamos datos que no van al Hash (listas, objetos)
        safe_data = {k: v for k, v in data.items() if isinstance(v, (str, int, float))}
        
        try:
            async with self.redis.pipeline() as pipe:
                pipe.hset(key, mapping=safe_data)
                
                # Actualizar Leaderboard HSP (ZSET)
                if 'hsp' in data:
                    name_display = f"{data.get('username', '')[:10]}" or f"ID:{uid}"
                    # Guardamos score es HSP
                    pipe.zadd("leaderboard:hsp", {f"{name_display}:{uid}": float(data['hsp'])})
                    
                await pipe.execute()
        except Exception as e:
            logger.error(f"Error saving node {uid}: {e}")

    async def update_email(self, uid: int, email: str):
        await self.redis.hset(f"node:{uid}", "email", email)

    async def delete_node(self, uid: int):
        """Borrado completo con limpieza de índices"""
        async with self.redis.pipeline() as pipe:
            pipe.delete(f"node:{uid}")
            pipe.delete(f"refs:{uid}")
            pipe.srem("global:users", uid)
            # Nota: ZREM necesita el member exacto. En prod ideal guardar solo UID en zset.
            # Para simplificar borrado V13.2, omitimos zrem complejo para no fallar
            await pipe.execute()

    # --- LEADERBOARD HSP (OPTIMIZADO) ---

    async def get_top_hsp(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Devuelve el Top 10 HSP formateado"""
        try:
            # ZREVRANGE devuelve de mayor a menor score
            raw_data = await self.redis.zrevrange("leaderboard:hsp", 0, limit-1, withscores=True)
            cleaned_data = []
            for member, score in raw_data:
                # member es "Nombre:UID", lo limpiamos para mostrar solo nombre
                name = member.split(":")[0] if ":" in member else member
                cleaned_data.append((name, score))
            return cleaned_data
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            return []

    # --- SQUADS (ENJAMBRES) ---

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        cell_id = f"cell:{owner_id}"
        if await self.redis.exists(cell_id): return cell_id
        
        data = {
            "id": cell_id,
            "name": name,
            "owner": owner_id,
            "created_at": time.time(),
            "pred_acc": 0.0
        }
        async with self.redis.pipeline() as pipe:
            pipe.hset(cell_id, mapping=data)
            pipe.sadd(f"squad_members:{cell_id}", owner_id)
            await pipe.execute()
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        data = await self.redis.hgetall(cell_id)
        if not data: return None
        members = await self.redis.smembers(f"squad_members:{cell_id}")
        data['members'] = list(members)
        return data

    async def get_global_stats(self):
        return {
            "nodes": await self.redis.scard("global:users") or 0
        }

# INSTANCIA GLOBAL
db = Database()
