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

## Estado actual

- ✅ `engine/nutrition.py` — cálculo de TDEE (Mifflin-St Jeor) + reparto de macros por fase de peso.
- ⬜ `engine/progression.py` — pendiente (Fase 1).
- ⬜ `engine/periodization.py` — pendiente (Fase 1, ver pseudocódigo en `../00-research/06-periodizacion-ciencia-deportiva.md`).
- ⬜ `engine/guardrails.py` — pendiente (Fase 1).
- ⬜ `garmin_sync/client.py` — pendiente (siguiente paso).
