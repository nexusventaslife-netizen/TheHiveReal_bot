```markdown
# TheHiveReal_bot - Redis / Arq Integration (Notas de despliegue)

Resumen:
- Integración de Redis para caché, métricas y rate-limiting.
- Arq como backend de workers para tareas asíncronas.
- Telegram usando Webhooks (FastAPI expone `/telegram/webhook`).

Variables de entorno necesarias:
- TELEGRAM_TOKEN: token del bot.
- TELEGRAM_WEBHOOK_URL: URL pública donde Render (o tu provider) enviará updates.
- DATABASE_URL: Postgres/AsyncPG connection string.
- REDIS_URL: redis://[:password@]host:port/db
- ADMIN_ID, DATA_BUYER_KEY, etc.

Instalación (entorno virtual):
- pip install -r requirements.txt

Ejecutar la API (ej. en Render):
- Asegúrate de configurar REDIS_URL y TELEGRAM_WEBHOOK_URL como environment vars.
- Para exponer webhook: configura Render para apuntar a https://<service>.onrender.com/telegram/webhook
- (Opcional) configura Telegram webhook con:
  https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=<TELEGRAM_WEBHOOK_URL>

Iniciar worker (ARQ):
- ARQ busca la clase WorkerSettings en el módulo tasks.py
- Ejecuta en el entorno con acceso a REDIS_URL:
  arq tasks.WorkerSettings
  (Asegúrate de tener arq instalado en el entorno)

Notas operacionales:
- TTLs de caché: puedes ajustar en cache.py o inicializar con parámetros.
- Para una instalación en producción considera:
  - Réplicas Redis (sentinel/cluster) y TLS.
  - Usar Citus / Aurora / replicas para Postgres.
  - Monitoreo de latencia (Grafana/Prometheus) y APM.
  - Autoescalado de workers arq según longitud de cola.

Comprobaciones después del despliegue:
- Verifica que `GET /health` responda.
- Verifica que webhook de Telegram reciba updates.
- Verifica que `arq` worker esté en línea y consuma jobs en Redis.
```
