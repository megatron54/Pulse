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
- ✅ `engine/progression.py` — estimación de 1RM (Epley), doble progresión de series, autorregulación de carga vía RIR (APRE).
- ✅ `engine/periodization.py` — semáforo de readiness diario (RED/YELLOW/GREEN) a partir de HRV/Body Battery/Training Readiness/ACWR/sueño/dolor, y decisión de sesión del día.
- ✅ `engine/guardrails.py` — guardrails transversales: deload forzado por ACWR sostenido, pausa de déficit calórico por RED sostenido en corte, descanso forzado pre-competición, validación de no apilar sesiones de alta demanda.
- ⬜ `garmin_sync/client.py` — pendiente (siguiente paso).
