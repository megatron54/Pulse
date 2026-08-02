# Pulse — Entrenador personal con IA (multi-deporte, multi-objetivo)

> App personal (móvil + escritorio) que actúa como entrenador y nutricionista, integrando datos de Garmin, fotos de progreso y objetivos múltiples (fuerza, hipertrofia, running, natación, artes marciales, estética, cortes de peso, rendimiento general).

## Estado del proyecto

**Fase actual:** Investigación completada → Diseño de arquitectura y roadmap.
**Última actualización:** 2026-08-02

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
1. [01-fases-desarrollo.md](02-roadmap/01-fases-desarrollo.md) — Roadmap por fases (MVP → v1 → v2)

### 📦 recursos/ — Material descargado y referencias
- `recursos/repos/` — Repos GitHub clonados localmente (código real reutilizable)
- `recursos/datasets/` — Datasets de referencia (ejercicios, nutrición)
- `recursos/papers/` — Papers científicos citados, resumidos
- [recursos/00-indice-recursos.md](recursos/00-indice-recursos.md) — Índice completo con enlaces

## Decisión de alcance (pendiente de confirmar contigo)

- **Usuarios:** solo tú (self-hosted, 1 usuario) — simplifica mucho Garmin, privacidad y multiusuario.
- **Plataformas:** móvil + escritorio desde una sola base de código.
- **Filosofía central:** el motor de reglas determinista decide (macros, progresión, periodización, seguridad); la IA solo explica y conversa. Nunca al revés.

## Próximos pasos sugeridos

1. Confirmar/ajustar el stack propuesto en `01-arquitectura/02-stack-tecnologico.md`.
2. Congelar el roadmap de fases en `02-roadmap/01-fases-desarrollo.md`.
3. Arrancar Fase 0 (setup del entorno + wger self-hosted + sync Garmin básico) con TDD desde el primer commit.
