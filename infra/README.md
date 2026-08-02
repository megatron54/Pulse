# Infraestructura — Fase 0

## wger (backend base)

Repo oficial clonado en `wger-docker/` (https://github.com/wger-project/docker).

**Entorno elegido: `dev-postgres`** (usa PostgreSQL, coherente con la decisión de stack en `01-arquitectura/02-stack-tecnologico.md`).

### Cómo arrancarlo (cuando Docker Desktop esté instalado y corriendo)

```powershell
cd infra\wger-docker\dev-postgres
copy .env.example .env
# Revisar .env y ajustar contraseñas/puertos si hace falta
docker compose up -d
```

Tras el primer arranque, wger queda disponible normalmente en `http://localhost` (revisar el `.env` de esa carpeta para el puerto exacto y credenciales de admin generadas).

### Verificación de que funciona
```powershell
docker compose ps        # todos los servicios "healthy"/"running"
docker compose logs web  # sin errores de arranque
```

Abrir `http://localhost` en el navegador → debe aparecer la pantalla de login de wger.

### Notas
- Este entorno es de **desarrollo**. Para producción real habría que usar el `docker-compose.yml` de la raíz de `wger-docker/` (con reverse proxy, Celery, etc.) — no es prioritario ahora, es para más adelante si se despliega en un servidor propio permanente.
- No modificar el contenido de `wger-docker/` directamente (es un repo de terceros clonado) — cualquier configuración propia va en un `.env` local (ya ignorado por git) o en un `docker-compose.override.yml` (hay un ejemplo: `docker-compose.override.example.yml` en la raíz del repo clonado).
- Recordatorio del roadmap: "regularly pull the latest version" — de vez en cuando hacer `git pull` dentro de `wger-docker/` para traer actualizaciones del compose oficial.

## Siguiente pieza (independiente de Docker): sync de Garmin

El módulo `backend/garmin_sync/` no depende de Docker/wger — corre en un venv Python normal y escribe a la base de datos. Ver `backend/README.md`.
