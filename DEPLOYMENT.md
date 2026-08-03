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

- ✅ Imagen Docker del **backend**: construida y verificada en esta sesión (854MB, healthcheck incluido).
- ⬜ Imagen Docker del **frontend**: el Dockerfile existe y sigue el patrón estándar de build multi-stage de Next.js, pero **no se verificó construyéndola en esta sesión** (el build se quedó colgado en `npm ci` dentro del contenedor por más de 5 minutos sin causa identificada - posible problema de red/DNS del contenedor en este entorno concreto, no necesariamente un problema del Dockerfile). El frontend SÍ está verificado funcionando fuera de Docker (build local + pruebas end-to-end en navegador real contra el backend real, ver PRs de Fase B/F). **Pendiente:** depurar el build de la imagen Docker del frontend en un entorno con red de contenedores fiable.
- ⬜ `docker-compose.yml` raíz completo (los 3 servicios juntos): no probado de extremo a extremo por el mismo bloqueo del frontend.

## CI (GitHub Actions)

`.github/workflows/ci.yml` ejecuta en cada push/PR a `main`/`develop`:
1. Tests del backend con cobertura (umbral mínimo 85%, cobertura real ~97%).
2. Verificación del esquema contra un Postgres real (create/drop/create).
3. Arranque real de la API contra ese Postgres y chequeo de `/health`.
4. Lint + build del frontend.
