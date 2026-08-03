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

## Verificación

```powershell
curl http://localhost:8000/health
docker compose ps   # todos los servicios "healthy"
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

## Estado de verificación de esta pieza (honestidad de progreso)

- ✅ Imagen Docker del **backend**: construida y verificada.
- ✅ Imagen Docker del **frontend**: construida y verificada en esta sesión (el bloqueo de `npm ci` visto anteriormente no se reprodujo - probablemente fue un problema transitorio de red/DNS del contenedor, no del Dockerfile).
- ✅ `docker-compose.yml` raíz completo (los 3 servicios juntos): probado de extremo a extremo desde cero (volumen de Postgres nuevo, sin ningún paso manual) - los 3 contenedores quedan `healthy`, `/health` responde y se pudo crear un usuario real a través de la API que corre en Docker.
- **Hallazgo real corregido en esta sesión:** al levantar el stack sobre un Postgres recién creado, la base de datos quedaba sin tablas - nada ejecutaba `Base.metadata.create_all()` fuera de los tests/CI. El primer request real fallaba con `UndefinedTable`. Corregido con `backend/scripts/ensure_schema.py` (idempotente, se ejecuta antes de `uvicorn` en el `CMD` del Dockerfile del backend) en vez de un evento `lifespan` de FastAPI, para no acoplar los tests de integración de la API (que usan su propio engine SQLite) al `DATABASE_URL` real.

## CI (GitHub Actions)

`.github/workflows/ci.yml` ejecuta en cada push/PR a `main`/`develop`:
1. Tests del backend con cobertura (umbral mínimo 85%, cobertura real ~97%).
2. Verificación del esquema contra un Postgres real (create/drop/create).
3. Arranque real de la API contra ese Postgres y chequeo de `/health`.
4. Lint + tests unitarios (Vitest) + build del frontend.
