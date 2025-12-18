import ujson as json
import os
import time
import asyncio
import redis.asyncio as redis
from datetime import datetime
from typing import Optional, Dict, List, Any
from loguru import logger

# ==============================================================================
# HIVE DATABASE CORE - V301 PRODUCTION (FULL)
# ==============================================================================

class DatabaseManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.r: Optional[redis.Redis] = None
        self._max_retries = 10
        self._retry_delay = 2
        
        # --- ESQUEMA MAESTRO DEL NODO (USUARIO) ---
        # Define la estructura exacta de datos para cada persona
        self.DEFAULT_NODE_SCHEMA = {
            # 1. IDENTIDAD
            "id": 0,
            "first_name": "",
            "username": "",
            "email": None,              # Identificador único de vinculación
            "joined_at": "",
            
            # 2. BIOLOGÍA (GAMEPLAY)
            "caste": None,              # Rol Genético (Recolector, Guardián, Explorador)
            "polen": 500,               # Energía actual
            "max_polen": 500,           # Capacidad máxima (variable por casta)
            "oxygen": 100.0,            # Salud (Decae con inactividad)
            
            # 3. ECONOMÍA (TOKENOMICS)
            "honey": 0.0,               # Miel (Saldo Líquido)
            "honey_vested": 0.0,        # Miel Futura (Airdrop)
            "real_balance": 0.0,        # Saldo USD (CPA)
            
            # 4. CRONOBIOLOGÍA
            "last_pulse": 0,            # Timestamp última acción
            "last_regen": 0,            # Timestamp última regeneración
            "zumbido_hoy": False,       # Participación en activación diaria
            
            # 5. ESTRUCTURA SOCIAL
            "enjambre_id": None,        # ID de la Célula
            "referrals": [],            # Lista de IDs invitados
            "padre_id": None,           # Quién me invitó
            "swarm_power": 1.0,         # Multiplicador viral
            
            # 6. SEGURIDAD & META
            "entropy_trace": [],        # Vector de tiempos para anti-bot
            "verificado": False,        # ¿Email confirmado?
            "banned": False,            # Estado de baneo
            "is_premium": False         # Estado de pago
        }

    async def connect(self):
        """
        Establece la conexión al Cluster de Redis con política de reintentos agresiva.
        """
        if not self.redis_url:
            logger.critical("❌ ERROR CRÍTICO: REDIS_URL no encontrada en variables de entorno.")
            raise ValueError("REDIS_URL missing")

        logger.info("🔌 Iniciando enlace neuronal con la Base de Datos...")
        
        for attempt in range(self._max_retries):
            try:
                # Configuración optimizada para alta carga (Render/AWS)
                self.r = redis.from_url(
                    self.redis_url, 
                    decode_responses=True, 
                    socket_timeout=5.0,
                    socket_connect_timeout=10.0,
                    socket_keepalive=True,
                    retry_on_timeout=True,
                    max_connections=100 # Pool amplio
                )
                await self.r.ping()
                logger.success(f"✅ MEMORIA COLMENA CONECTADA (Intento {attempt+1})")
                
                # Inicialización de Contadores Globales (Si es el primer arranque)
                await self._init_globals()
                return
            except Exception as e:
                logger.warning(f"⚠️ Fallo conexión Redis ({attempt+1}/{self._max_retries}): {e}")
                await asyncio.sleep(self._retry_delay)
        
        raise ConnectionError("FATAL: Imposible conectar a Redis tras múltiples intentos.")

    async def _init_globals(self):
        """Inicializa las variables globales del mundo si no existen."""
        async with self.r.pipeline() as pipe:
            pipe.setnx("global:nodos_activos", 0)
            pipe.setnx("global:miel_total", 0.0)
            pipe.setnx("global:ciclo_actual", 1)
            await pipe.execute()

    async def close(self):
        if self.r:
            await self.r.aclose()
            logger.info("🔒 Conexión Redis cerrada correctamente.")

    # ==========================================================================
    # GESTIÓN DE NODOS (USUARIOS) - CRUD COMPLETO
    # ==========================================================================

    async def create_node(self, user_id: int, first_name: str, username: str, referrer_id: int = None) -> bool:
        """
        Registra un nuevo Nodo en el sistema.
        Usa transacciones atómicas para asegurar consistencia global.
        """
        if not self.r: return False
        key = f"node:{user_id}"
        
        # Verificar existencia rápida (Bloom Filter conceptual)
        if await self.r.exists(key): return False

        # Instanciar nuevo nodo
        new_node = self.DEFAULT_NODE_SCHEMA.copy()
        new_node.update({
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_at": datetime.utcnow().isoformat(),
            "last_pulse": time.time(),
            "last_regen": time.time(),
            "padre_id": referrer_id
        })

        # Escritura Atómica: Guardar Datos + Incrementar Contador Global
        async with self.r.pipeline() as pipe:
            pipe.set(key, json.dumps(new_node))
            pipe.incr("global:nodos_activos")
            await pipe.execute()

        # Procesar Viralidad (Segundo plano)
        if referrer_id:
            asyncio.create_task(self._process_referral_bonus(referrer_id, user_id))
        
        logger.info(f"🧬 NUEVO NODO ACTIVADO: {user_id}")
        return True

    async def get_node(self, user_id: int) -> Optional[Dict]:
        """
        Recupera un Nodo y repara su estructura si es antigua (Self-Healing).
        """
        if not self.r: return None
        try:
            data = await self.r.get(f"node:{user_id}")
            if not data: return None
            
            node = json.loads(data)
            
            # Migración de Esquema en Caliente
            dirty = False
            for k, v in self.DEFAULT_NODE_SCHEMA.items():
                if k not in node:
                    node[k] = v
                    dirty = True
            
            if dirty:
                await self.save_node(user_id, node)
                
            return node
        except Exception as e:
            logger.error(f"Error recuperando nodo {user_id}: {e}")
            return None

    async def save_node(self, user_id: int, data: Dict):
        """Persiste el estado del nodo en memoria rápida."""
        if self.r: await self.r.set(f"node:{user_id}", json.dumps(data))

    async def update_email(self, user_id: int, email: str):
        """Vincula identidad y marca verificado."""
        node = await self.get_node(user_id)
        if node:
            node["email"] = email
            node["verificado"] = True
            await self.save_node(user_id, node)
            logger.info(f"📧 Identidad vinculada nodo {user_id}: {email}")

    async def delete_node(self, user_id: int):
        """Eliminación dura (Hard Delete) para resets."""
        if self.r: 
            await self.r.delete(f"node:{user_id}")
            logger.warning(f"💀 Nodo {user_id} purgado del sistema.")

    # ==========================================================================
    # GESTIÓN DE ENJAMBRES (CÉLULAS)
    # ==========================================================================

    async def create_cell(self, owner_id: int, name: str) -> Optional[str]:
        """Crea una nueva estructura celular (Enjambre)."""
        if not self.r: return None
        
        cell_id = f"cell:{owner_id}:{int(time.time())}"
        cell_data = {
            "id": cell_id,
            "owner_id": owner_id,
            "name": name,
            "members": [owner_id],
            "synergy": 1.05,          # Multiplicador base
            "total_honey": 0.0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await self.r.set(cell_id, json.dumps(cell_data))
        return cell_id

    async def get_cell(self, cell_id: str) -> Optional[Dict]:
        if not self.r or not cell_id: return None
        data = await self.r.get(cell_id)
        return json.loads(data) if data else None

    async def update_cell(self, cell_id: str, data: Dict):
        if self.r: await self.r.set(cell_id, json.dumps(data))

    # ==========================================================================
    # MÉTRICAS GLOBALES (CONCIENCIA COLECTIVA)
    # ==========================================================================

    async def add_global_honey(self, amount: float):
        """Suma producción a la métrica mundial visible."""
        if self.r and amount > 0:
            await self.r.incrbyfloat("global:miel_total", amount)

    async def get_global_stats(self) -> Dict:
        """Devuelve el estado del mundo para el Dashboard."""
        if not self.r: return {"nodes": 0, "honey": 0}
        
        # Lectura en Pipeline para velocidad
        async with self.r.pipeline() as pipe:
            pipe.get("global:nodos_activos")
            pipe.get("global:miel_total")
            res = await pipe.execute()
            
        return {
            "nodes": int(res[0] or 0),
            "honey": float(res[1] or 0)
        }

    # ==========================================================================
    # LÓGICA VIRAL INTERNA
    # ==========================================================================

    async def _process_referral_bonus(self, parent_id: int, child_id: int):
        """Ejecuta la recompensa por expansión de red."""
        try:
            parent = await self.get_node(parent_id)
            if parent and child_id not in parent["referrals"]:
                parent["referrals"].append(child_id)
                # Recompensa: Miel + Recarga de Energía
                parent["honey"] += 100.0
                parent["polen"] = parent["max_polen"] 
                parent["swarm_power"] += 0.05 # Incremento de poder social
                await self.save_node(parent_id, parent)
        except Exception as e:
            logger.error(f"Error procesando referido {parent_id}: {e}")

# Instancia Global Exportada
db = DatabaseManager()
