# Pulse — Entrenador personal con IA (multi-deporte, multi-objetivo)

![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/-Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/-Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Playwright](https://img.shields.io/badge/-Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![TDD](https://img.shields.io/badge/tests-TDD%20~100%25%20engine-success?style=flat-square)

> App personal (móvil + escritorio) que actúa como entrenador y nutricionista, integrando datos reales de Garmin, wger (ejercicios/nutrición) y objetivos múltiples (fuerza, hipertrofia, running, artes marciales, composición corporal, cortes de peso).

## Estado del proyecto

**Fase actual:** aplicación funcional en uso real (mono-usuario), con Garmin Connect real emparejado y sincronizando. Backend (FastAPI) + frontend (Next.js) + Postgres, todo en Docker o local. Desarrollo continuo con TDD estricto, revisión de código antes de cada merge, y verificación manual real (Playwright) además de tests automatizados.

**Documento vivo de seguimiento:** [`02-roadmap/03-vision-produccion.md`](02-roadmap/03-vision-produccion.md) — épicas hechas/pendientes, hallazgos de investigación, decisiones de diseño. Léelo antes de retomar el trabajo para no repetir investigación ya hecha.

## Arquitectura en 3 capas

1. **Capa 1 — Motor de reglas determinista** (`backend/engine/`): decide nutrición, progresión, periodización, readiness (semáforo RED/YELLOW/GREEN) y guardrails de seguridad. Sin llamadas a red ni a IA. Cobertura de tests ~100% — es la capa que toma decisiones que importan.
2. **Capa 2 — Servicios/API** (`backend/services/`, `backend/api/`): orquesta la Capa 1 con datos reales (Garmin, wger) y los expone vía REST.
3. **Capa 3 — Coach conversacional** (`backend/coach/`): IA (Gemini, con fallback determinista) que **explica** las decisiones ya tomadas por la Capa 1 — nunca decide por su cuenta.

Detalle completo en [`01-arquitectura/`](01-arquitectura/).

## Qué funciona hoy

- **Garmin Connect real**: emparejamiento seguro (`backend/scripts/garmin_pair.py`), sincronización nocturna automática de recovery (HRV/Body Battery/sleep/training readiness, cuando el dispositivo lo soporta) y actividades — corre como servicio Docker propio (`scheduler`), no depende de dejar un terminal manual abierto.
- **wger**: catálogo de ejercicios, diario de comidas real (vía el propio wger del usuario, token permanente).
- **Motor de reglas**: nutrición (TDEE + macros por fase), progresión (1RM, doble progresión, autorregulación RIR/APRE), periodización (readiness diario, ACWR real), guardrails (deload forzado, pausa de déficit por mala recuperación sostenida).
- **Diario de hábitos** correlacionado con recovery (estilo WHOOP Journal), resumen periódico de tendencias.
- **Frontend**: dashboard visual (gráficas reales, no listados) estilo WHOOP/Apple Health/Samsung Health — ver [`frontend/README.md`](frontend/README.md).

## Quickstart

```powershell
cp .env.example .env
docker compose up -d --build
# o, equivalente y con espera automatica a que todo quede listo + apertura del navegador:
.\start.ps1
```

- Backend: http://localhost:8000 (docs interactivas en `/docs`)
- Frontend: http://localhost:3000

Esto levanta los 4 servicios (Postgres, backend, frontend, y el scheduler nocturno de Garmin) — `docker compose ps` debe mostrar los 4 como `healthy`. Ver [`DEPLOYMENT.md`](DEPLOYMENT.md) para variables de entorno y verificación. Para desarrollo local sin Docker del backend/frontend (solo Postgres en Docker), ver [`backend/README.md`](backend/README.md) y [`frontend/README.md`](frontend/README.md).

## Índice de documentación

### 📚 00-research/ — Investigación profunda
1. [01-resumen-ejecutivo.md](00-research/01-resumen-ejecutivo.md) — TL;DR de todo lo investigado
2. [02-mercado-apps-existentes.md](00-research/02-mercado-apps-existentes.md) — Competencia y hueco de mercado
3. [03-garmin-integracion.md](00-research/03-garmin-integracion.md) — Cómo extraer datos de Garmin para uso personal
4. [04-reutilizacion-open-source.md](00-research/04-reutilizacion-open-source.md) — Qué reutilizar vs. qué construir
5. [05-analisis-corporal-foto.md](00-research/05-analisis-corporal-foto.md) — Estimación de composición corporal por foto
6. [06-periodizacion-ciencia-deportiva.md](00-research/06-periodizacion-ciencia-deportiva.md) — Ciencia de periodización multi-objetivo
7. [07-arquitectura-coach-ia.md](00-research/07-arquitectura-coach-ia.md) — Patrones de arquitectura para el coach conversacional

### 🏗️ 01-arquitectura/ — Diseño técnico
1. [01-arquitectura-general.md](01-arquitectura/01-arquitectura-general.md) — Las 3 capas del sistema
2. [02-stack-tecnologico.md](01-arquitectura/02-stack-tecnologico.md) — Decisiones de stack
3. [03-modelo-datos.md](01-arquitectura/03-modelo-datos.md) — Esquema de datos principal

### 🗺️ 02-roadmap/ — Plan de ejecución
1. [01-fases-desarrollo.md](02-roadmap/01-fases-desarrollo.md) — Roadmap original por fases (MVP → v1 → v2)
2. [02-plan-autonomo.md](02-roadmap/02-plan-autonomo.md) — Plan de ejecución autónomo por fases (A-J)
3. **[03-vision-produccion.md](02-roadmap/03-vision-produccion.md)** — Documento vivo: estado real de cada épica, hallazgos, decisiones pendientes. **Empieza aquí.**

### 📦 recursos/ — Material descargado y referencias
- `recursos/repos/` — Repos GitHub clonados localmente (código real reutilizable, no versionado)
- [recursos/00-indice-recursos.md](recursos/00-indice-recursos.md) — Índice completo con enlaces

## Principios que no cambian

- **TDD real**: tests antes que implementación, revisión de código antes de cada merge.
- **Nunca falsa precisión**: rangos donde el dominio es incierto, categorías donde el motor es categórico. Ninguna métrica se fabrica cuando faltan datos ("unknown is not zero").
- **La IA nunca decide**, solo explica una decisión ya tomada por reglas deterministas auditables.
- **Reutilizar antes que reinventar**: wger antes que una integración externa nueva; cuando ni eso sirve, se documenta honestamente que no hay integración viable en vez de prometerla.

## Autor

**Miguel Serra Ferrando** — Telecommunications Engineer
[GitHub](https://github.com/megatron54) · [LinkedIn](https://www.linkedin.com/in/miguel-serra-ferrando) · [Email](mailto:miguel.serra.ferrando@gmail.com)
