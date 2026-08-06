# Despliegue de Pulse (stack propio)

> wger (`backend/infra/wger-docker/`) es un stack separado a propósito
> (ver `01-arquitectura/01-arquitectura-general.md`) y se despliega aparte
> siguiendo `backend/infra/README.md`. Este documento cubre solo el stack
> propio de Pulse: Postgres + backend (FastAPI) + frontend (Next.js).

## Requisitos

- Docker Desktop (o Docker Engine + Compose plugin) instalado y corriendo.
- Una API key de Google Gemini (opcional - la app funciona sin ella, ver
  `00-research/07-arquitectura-coach-ia.md`, principio "IA opcional y no
  autoritativa").

## Pasos

```powershell
cp .env.example .env
# Editar .env: como mínimo, PULSE_API_KEY si PULSE_ENV != dev
docker compose up -d --build
```

- Backend: http://localhost:8000 (docs interactivas en `/docs`)
- Frontend: http://localhost:3000
- Postgres: `localhost:5433` (mismo puerto que en desarrollo local, ver
  `backend/infra/README.md`)
- `scheduler`: sin puerto expuesto (job nocturno de Garmin, `docker compose logs scheduler` para ver su actividad)

## Verificación

```powershell
curl http://localhost:8000/health
docker compose ps   # los 4 servicios (db, backend, frontend, scheduler) "healthy"
```

## Variables de entorno (ver `.env.example` para la lista completa)

| Variable | Obligatoria | Notas |
|---|---|---|
| `POSTGRES_PASSWORD` | Recomendada | Por defecto usa una contraseña de desarrollo, cámbiala fuera de local |
| `PULSE_API_KEY` | Sí, si `PULSE_ENV != dev` | Auth v1 (fail-closed, ver `backend/api/dependencies.py`) |
| `PULSE_ENV` | No (`dev` por defecto) | `dev` desactiva la exigencia de `PULSE_API_KEY` |
| `PULSE_FRONTEND_ORIGIN` | Sí en producción | CORS - debe ser el origen exacto del frontend desplegado |
| `NEXT_PUBLIC_API_URL` | Sí | Se embebe en el build del frontend (build arg), no es runtime |
| `GEMINI_API_KEY` | No | Sin ella, el coach usa su plantilla determinista |
| `PULSE_GARMIN_TOKENS_DIR` | No (usa `/data/garmin-tokens` en Docker) | Directorio base donde `scripts/garmin_pair.py` cachea el token OAuth de Garmin - en Docker apunta al volumen nombrado `garmin-tokens` compartido entre `backend` y `scheduler`; fuera de Docker cae a `~/.garminconnect` |

## Emparejar una cuenta Garmin real (una sola vez, por usuario)

```powershell
docker compose exec backend python -m scripts.garmin_pair --user-id <id>
```

Interactivo (pide email/contraseña por terminal, **nunca** se guardan ni se pasan por un chat de IA - ver el docstring de `backend/scripts/garmin_pair.py`). El token queda cacheado en el volumen `garmin-tokens`, visible tanto para `backend` como para el `scheduler` nocturno.

## Estado de verificación de esta pieza (honestidad de progreso)

- ✅ Imagen Docker del **backend**: construida y verificada.
- ✅ Imagen Docker del **frontend**: construida y verificada en esta sesión (el bloqueo de `npm ci` visto anteriormente no se reprodujo - probablemente fue un problema transitorio de red/DNS del contenedor, no del Dockerfile).
- ✅ `docker-compose.yml` raíz completo (los 3 servicios juntos): probado de extremo a extremo desde cero (volumen de Postgres nuevo, sin ningún paso manual) - los 3 contenedores quedan `healthy`, `/health` responde y se pudo crear un usuario real a través de la API que corre en Docker.
- **Hallazgo real corregido en esta sesión:** al levantar el stack sobre un Postgres recién creado, la base de datos quedaba sin tablas - nada ejecutaba `Base.metadata.create_all()` fuera de los tests/CI. El primer request real fallaba con `UndefinedTable`. Corregido con `backend/scripts/ensure_schema.py` (idempotente, se ejecuta antes de `uvicorn` en el `CMD` del Dockerfile del backend) en vez de un evento `lifespan` de FastAPI, para no acoplar los tests de integración de la API (que usan su propio engine SQLite) al `DATABASE_URL` real.
- ✅ **`scheduler` (4º servicio, PR #47):** reutiliza la imagen de `backend`, corre `python -m scheduler.app` en primer plano. **Hallazgo real:** el token OAuth de Garmin vivía en una ruta del host (fuera de Docker) - se resolvió con el volumen nombrado `garmin-tokens` + `PULSE_GARMIN_TOKENS_DIR` (ver tabla de variables arriba). El `HEALTHCHECK` heredado del Dockerfile de `backend` (llama a `:8000/health`) no aplica aquí (sin servidor HTTP) - se sobrescribe en `docker-compose.yml` con un healthcheck de liveness de proceso.

## CI (GitHub Actions)

`.github/workflows/ci.yml` ejecuta en cada push/PR a `main`/`develop`:
1. Tests del backend con cobertura (umbral mínimo 85%, cobertura real ~97%).
2. Verificación del esquema contra un Postgres real (create/drop/create).
3. Arranque real de la API contra ese Postgres y chequeo de `/health`.
4. Lint + tests unitarios (Vitest) + build del frontend.
