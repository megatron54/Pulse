# Arquitectura general

## Vista de conjunto

```
┌────────────────────────────────────────────────────────────────────┐
│                        CLIENTES (Flutter)                          │
│   App móvil (iOS/Android) + App escritorio (Win/Mac/Linux)         │
│   - Chat con el coach · Dashboards de progreso · Cámara (fotos)     │
│   - Registro de comidas/entrenos · Notificaciones                  │
└───────────────────────────┬──────────────────────────────────────┘
                             │ REST/GraphQL
┌───────────────────────────▼──────────────────────────────────────┐
│                     BACKEND (Python/FastAPI)                       │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ CAPA 1 · MOTOR DE REGLAS DETERMINISTA                     │    │
│  │  - engine/nutrition.py   (TDEE, macros)                   │    │
│  │  - engine/progression.py (RIR, %1RM, doble progresión)     │    │
│  │  - engine/periodization.py (ACWR, bloques, readiness)      │    │
│  │  - engine/guardrails.py  (reglas duras de seguridad)       │    │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ CAPA 2 · DATOS Y MEMORIA                                  │    │
│  │  - wger (Django, self-hosted) — tracking base              │    │
│  │  - Postgres — entrenamientos, wearables, perfil, historial │    │
│  │  - Store LangGraph / Mem0 — memoria de usuario a largo plazo│    │
│  │  - Job batch semanal — resumen/digest del usuario          │    │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ CAPA 3 · CONVERSACIONAL (LLM)                             │    │
│  │  - LangGraph — orquestación, nodo LLM al final del grafo   │    │
│  │  - Modelo barato/pequeño (GPT-4o-mini) o local (Ollama)    │    │
│  │  - Validador post-output                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ INGESTA DE DATOS                                          │    │
│  │  - garmin_sync/ (python-garminconnect, cron diario)        │    │
│  │  - body_analysis/ (MediaPipe Pose + fórmula Navy)          │    │
│  │  - food_photo/ (LLM Vision → macros, patrón Nutritheous)   │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

## Por qué esta separación (no negociable)

El motor de reglas (Capa 1) decide todo lo que puede causar daño si se equivoca: calorías, progresión de carga, cuándo descansar. El LLM (Capa 3) nunca toca esos números — solo los explica. Esto significa:

- El producto **funciona sin conexión a ningún LLM** (degradación elegante).
- Cada decisión es **auditable**: se puede ver exactamente qué regla la generó.
- El coste de IA se mantiene bajo (prompts cortos, modelos pequeños).
- Los errores se convierten en "¿escribí bien la regla?" (revisable, testeable) en vez de "¿alucinó el modelo?" (impredecible).

## Flujo de datos típico (ejemplo: día de entrenamiento)

1. Cron nocturno sincroniza Garmin → HRV, sueño, Body Battery, Training Readiness del día anterior.
2. Motor de reglas calcula `readiness_score` (RED/YELLOW/GREEN) y decide tipo/volumen de sesión según el plan semanal y el bloque de periodización activo.
3. Motor de reglas calcula el ajuste nutricional del día (déficit/mantenimiento/superávit según fase de peso y carga del día).
4. El usuario abre la app → ve la sesión y las macros ya calculadas.
5. El usuario pregunta al coach "¿por qué hoy toca menos volumen?" → la Capa 3 recibe la decisión ya tomada (tipada) + resumen de perfil, y solo redacta la explicación.
6. El usuario sube foto de progreso → pipeline on-device (MediaPipe + Navy) calcula rango de %grasa, se guarda en historial inmutable.
7. El usuario sube foto de una comida → LLM Vision extrae macros estimados, el usuario confirma/ajusta, se registra.

## Principio de "historial inmutable"

Ningún registro pasado se sobreescribe. Cambios de peso, medidas, o revisiones de un entrenamiento se añaden como nuevas entradas versionadas. Esto permite que el motor de reglas y el LLM siempre trabajen con tendencias reales, no con datos corregidos a posteriori que ocultarían el comportamiento real del usuario.
