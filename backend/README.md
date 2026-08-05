# Backend — Pulse

Motor de reglas determinista (Capa 1) + servicios de orquestación (Capa 2, Garmin/wger reales) + coach conversacional (Capa 3) + API REST (FastAPI).

## Setup

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

Requiere Postgres corriendo (ver `infra/docker-compose.pulse.yml` en la raíz, o el `docker compose up` completo desde la raíz del repo) - los tests usan su propio SQLite en memoria y no necesitan Postgres real.

## Estructura

- `engine/` — **Capa 1**: `nutrition.py` (TDEE + macros por fase), `progression.py` (1RM, doble progresión, autorregulación RIR/APRE), `periodization.py` (semáforo de readiness RED/YELLOW/GREEN, decisión de sesión), `guardrails.py` (deload forzado, pausa de déficit calórico). 100% determinista, sin red ni IA, cobertura ~100%.
- `garmin_sync/` — Cliente de Garmin Connect (`client.py`, login de un solo intento sin reintento agresivo), mapeo a `RecoveryContext` (`mapper.py`, principio "unknown is not zero"), mapeo de actividades (`activity_mapper.py`).
- `wger_client/` — Cliente HTTP del catálogo de ejercicios/nutrición de wger (self-hosted, ver `infra/`).
- `repositories/` — Acceso a datos (SQLAlchemy), un módulo por agregado (readiness, garmin, habits, training blocks, wger credentials...).
- `services/` — Capa 2: orquesta repositorios + `engine/` + clientes externos. Un servicio por caso de uso (readiness, food log, habit correlation, periodic summary, garmin pairing/activity sync, scheduler...).
- `coach/` — **Capa 3**: explicación conversacional (Gemini free tier + fallback determinista por plantilla) de una decisión ya tomada por la Capa 1 - nunca decide por su cuenta.
- `api/` — API REST (FastAPI). Auth v1 = API key simple (`X-API-Key`, fail-closed fuera de `PULSE_ENV=dev`). Routers: `users`, `readiness`, `session`, `nutrition`, `food_log`, `body_composition`, `training_blocks`, `exercises`, `habits`, `garmin`, `summary`.
- `scheduler/` — Job nocturno (APScheduler) que sincroniza recovery y actividades de Garmin para todos los usuarios con credenciales activas.
- `scripts/` — `ensure_schema.py` (crea/verifica el esquema, idempotente, se ejecuta antes de arrancar la API), `garmin_pair.py` (emparejamiento inicial interactivo de una cuenta Garmin real - **nunca** pasa la contraseña por un chat de IA ni por la API, se ejecuta a mano en terminal).
- `tests/` — TDD real: se escriben antes que la implementación. ~500 tests, ~97% cobertura (gate de CI: 85%).

## Cómo arrancar la API

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m scripts.ensure_schema
uvicorn api.main:app --reload
```

Docs interactivas (OpenAPI/Swagger) en `http://127.0.0.1:8000/docs`.

## Emparejar una cuenta Garmin real

```powershell
python -m scripts.garmin_pair --user-id <id>
```

Pide email/contraseña por terminal (nunca se guardan, solo se usan para un login en memoria); soporta verificación en dos pasos. Tras emparejar, el scheduler nocturno sincroniza automáticamente - ver `services/scheduler_service.py`.

## Ejecutar el scheduler nocturno

```powershell
python -m scheduler.app
```

Proceso de larga duración independiente de la API (como un worker de colas) - sincroniza recovery (04:00) y actividades (04:15) de todos los usuarios con `GarminCredentials` activas.

## Tests y cobertura

```powershell
pytest -q
pytest --cov=engine --cov=services --cov=repositories --cov=coach --cov=api --cov=models --cov=garmin_sync --cov=scheduler --cov=wger_client --cov-report=term-missing --cov-fail-under=85
```
