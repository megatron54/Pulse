# Backend — Pulse

Motor de reglas determinista (Capa 1) + sincronización de datos (Garmin).

## Setup

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

## Estructura

- `engine/` — Capa 1: nutrición, progresión, periodización, guardrails. 100% determinista, sin llamadas a red ni a IA. Cobertura de tests objetivo: 90%+ (esta capa decide cosas que importan).
- `garmin_sync/` — Ingesta de datos desde Garmin Connect vía `python-garminconnect`.
- `tests/` — Tests unitarios (pytest), TDD: se escriben antes que la implementación.

## Cómo arrancar la API

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload
```

Docs interactivas (OpenAPI/Swagger) en `http://127.0.0.1:8000/docs`.

## Estado actual

- ✅ `engine/nutrition.py` — cálculo de TDEE (Mifflin-St Jeor) + reparto de macros por fase de peso.
- ✅ `engine/progression.py` — estimación de 1RM (Epley), doble progresión de series, autorregulación de carga vía RIR (APRE).
- ✅ `engine/periodization.py` — semáforo de readiness diario (RED/YELLOW/GREEN) a partir de HRV/Body Battery/Training Readiness/ACWR/sueño/dolor, y decisión de sesión del día.
- ✅ `engine/guardrails.py` — guardrails transversales: deload forzado por ACWR sostenido, pausa de déficit calórico por RED sostenido en corte, descanso forzado pre-competición, validación de no apilar sesiones de alta demanda.
- ✅ `garmin_sync/client.py` + `garmin_sync/mapper.py` — sincronización con Garmin Connect (login de un solo intento, sin reintento agresivo; aislamiento de fallos por campo; mapeo a RecoveryContext con principio "unknown is not zero"). Testeado sin red real (api_factory inyectable). **Pendiente:** verificar la forma real de los payloads `_extraer_*` contra una cuenta Garmin viva en la primera sincronización end-to-end.
- ✅ `services/` — orquestación: readiness (Garmin + check-in manual), nutrición diaria, sesión diaria, composición corporal.
- ✅ `coach/` — Capa 3 conversacional (Gemini free tier + fallback determinista).
- ✅ `api/` — API REST (FastAPI) sobre todos los servicios. Auth v1 = API key simple (`X-API-Key`, fail-closed fuera de `PULSE_ENV=dev`). `uvicorn api.main:app` para arrancar.
