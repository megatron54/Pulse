# Plan de desarrollo: siguiente fase (post rate-limit fix + rediseño frontend v2.1)

> Este documento NO repite investigación ya hecha - cada punto enlaza a la
> sección correspondiente de [`03-vision-produccion.md`](03-vision-produccion.md)
> (fuente de verdad de estado/hallazgos). Este documento solo secuencia y
> prioriza el trabajo pendiente ya identificado allí, en fases ejecutables.
> Actualizar la tabla de épicas de `03-vision-produccion.md` según se
> complete cada punto - este plan no duplica esa tabla, la ordena.

## Estado de partida (2026-09-13)

Completado en la sesión más reciente: fix del rate-limiting real de Garmin
(backfill a background + sync manual + sync incremental cada 2h, ver
investigación #15), ingesta de pasos, ejes/leyenda en gráficas de detalle,
fusión Entrenamiento+Recuperación+Análisis, reorden de nav (Cuerpo en 2º
lugar), `BodyGoalInsightCard`. 661 tests backend + 150 tests frontend en
verde, `npm run build` limpio.

Pendiente real identificado en el backlog (`03-vision-produccion.md`),
priorizado aquí por impacto y por dependencias reales entre épicas - no
por orden numérico de la tabla.

## Fase 1 — Cerrar huecos de producto ya reconocidos como parciales (bajo riesgo, sin investigación nueva)

Estas piezas ya tienen su research hecho o son extensión directa de código existente.

1. ✅ **Hecho** — **Épica G (slot de coach por deporte)**: `generate_context_narrative` (Capa 3, reutilizada tal cual) integrado como `GET /garmin/activities/narrative`, contexto de carga semanal (sesiones y km de la semana actual vs. media de las 4 previas) por categoría, visible en la ficha de detalle de cada deporte (`SportActivityHistoryCard`).
2. ✅ **Hecho** — **Épica G (detalle de series/reps de gimnasio)**: ingesta de `get_activity_exercise_sets` (nuevo modelo `GarminExerciseSet`, idempotente por `(user_id, activity_id, numero_serie)`), solo para actividades nuevas (misma mitigación de riesgo de bloqueo de cuenta que el resto de la ingesta), + detalle expandible por sesión de fuerza en `SportActivityHistoryCard`. Cierra el MUST-HAVE #2 del punto 4. Nota de honestidad: los nombres de campo de Garmin (`setType`, `repetitionCount`, `weight`, `category`) no estaban documentados en el repo ni en la librería local - se usaron los nombres estándar de la comunidad, sin verificar todavía contra una sesión de fuerza real del usuario.
3. **Épica H (extender coach a nutrición)**: una vez exista contexto de nutrición suficientemente rico (ver Fase 2, punto 6), añadir `generate_context_narrative` para nutrición. Bloqueada por la Fase 2 si se quiere un contexto con datos reales de macros diarios, no solo el resultado del motor.
4. ✅ **Hecho** — **Épica 8 (informe exportable)**: botón "Descargar PDF" en `PeriodicSummaryCard` vía el diálogo de impresión nativo del navegador ("Guardar como PDF", `[data-print-target]` + `@media print` en `globals.css`), sin dependencia nueva de generación de PDF.
5. ✅ **Hecho** — **Épica B (fases de sueño detalladas)**: columnas `deep_sleep_seg`/`light_sleep_seg`/`rem_sleep_seg`/`awake_sleep_seg` en `GarminDailyMetrics` (no una tabla `GarminSleepDetail` separada, mismo criterio ya usado para `pasos`) + desglose visual (barra apilada) en el histórico de Salud y recovery.

**Por qué primero**: ninguna de estas 5 piezas requiere investigación dedicada nueva ni decisiones de producto pendientes de confirmar con el usuario - son ejecutables ya, con TDD normal.

## Fase 2 — Nutrición: diario real + recetas (la pieza de producto más grande sin construir)

Ver desglose completo en investigación #7 del vision doc - aquí solo la secuencia de ejecución:

6. **Input diario de comidas vía wger** (`nutritiondiary`/`meal`/`mealitem`) - Épica 11 depende de esto. Atención a los gotchas ya documentados (campos numéricos como string, CVE-2026-27839 en sub-endpoints `nutritional_values`, orden de `ingredient/` no garantizado).
7. **Recetas** (Épica 11): modelo de datos nuevo sobre `mealitem` de wger (una receta = lista de `mealitem` + instrucciones), o evaluar la alternativa más barata de "guardar una combinación de `mealitem` como plantilla reusable" antes de construir un modelo nuevo completo.
8. Exponer con más detalle en la UI la calculadora de calorías/macros que ya existe en `engine/nutrition.py` (hoy solo se ve el resultado final del día) - trabajo de frontend puro, sin backend nuevo.

**Por qué segundo**: es la pieza de producto explícitamente pedida por el usuario ("Nutrición equivalente a MyFitnessPal") con research ya cerrada (wger es la fuente, MyFitnessPal descartado) - solo falta construir.

## Fase 3 — Motor de timing/ayuno intermitente (la pieza de mayor riesgo, requiere investigación dedicada previa)

Épica 13. **No empezar a codificar sin antes completar el paso 0**:

0. Sesión de investigación científica dedicada (mismo patrón que `00-research/06-periodizacion-ciencia-deportiva.md` y `00-research/08-nutricion-recovery-ciencia.md`) sobre timing de nutrientes/ayuno intermitente - la evidencia es mixta/contestada, cualquier umbral debe documentar su fuente.
1. Motor de reglas determinista (Capa 1 nueva, sin red) con condiciones auditables, ej. "si recuperación 3+ días en amarillo/rojo Y usuario en déficit → sugerir redistribuir carbohidratos hacia el entrenamiento en vez de ayuno prolongado".
2. Conectar a Capa 3 (solo explica, nunca decide) - reutiliza el patrón anti-alucinación numérica ya construido (investigación #13 del vision doc).

**Depende de**: Fase 1 (carga ya existe), Fase 2 (nutrición real, no solo el resultado agregado), Épica 9 (fotos/tendencia, ver Fase 4) según el research defina qué inputs son necesarios.

## Fase 4 — Fotos de progreso (research ya cerrada, solo falta construir)

Épica 9, investigación #3 del vision doc ya concluyente: **nunca %grasa desde foto**, solo tendencia relativa de silueta (ratios hombro/cintura/cadera) vía MediaPipe Pose Landmarker. Plan ya escrito en el research - ejecutar tal cual:
- Captura de landmarks por foto (frontal/lateral/espalda, ya modelado en `ProgressPhoto.angulo`).
- Todo cliente (`"use client"`), assets WASM servidos desde `public/` propio, modelo cargado perezosamente.
- Integrar como una señal más en `BodyGoalInsightCard`/insights de Cuerpo, nunca como número de %grasa.

## Fase 5 — Integraciones de investigación pendiente (no empezar sin sesión de research dedicada)

Estas tres NO tienen research suficiente todavía (ver investigación #12 del vision doc) - cualquier trabajo de código antes de la sesión de research sería prometer algo no verificado:

- **Épica 17 (intervals.icu)**: términos de uso, límites de rate, si requiere cuenta intervals.icu separada, si "Build Your Own Coach" es API pública documentada o producto cerrado.
- **Épica 18 (`coach.md`)**: preferencias de coaching persistentes editables por el usuario - research menor (formato de archivo, cómo se inyecta en la plantilla de Capa 3), ejecutable rápido una vez decidido el formato.
- **Épica 19 (Telegram)**: bot propio vía `@BotFather`, empuje del mensaje ya generado por Capa 3 - sin chat conversacional nuevo (ya descartado como WON'T-HAVE-YET). Research menor, mayormente de implementación.

De las tres, 18 y 19 son las más baratas de investigar y ejecutar (no dependen de negociar con un tercero) - candidatas a intercalarse en cualquier fase anterior si surge tiempo libre.

## Fase 6 — Baja prioridad / opcional

- **Épica 12 (HealthKit como fuente secundaria)**: solo iOS, resúmenes aproximados de MyFitnessPal sin desglose - prioridad baja explícita, no bloquea nada más.
- **Épica 4 (sustituto del food log revertido)**: ya resuelto de facto por la Fase 2 (wger vía `nutritiondiary`) - marcar como cerrada cuando la Fase 2 esté hecha, en vez de tratarla como una épica separada.

## Cómo usar este documento

- Cada fase es secuencial por dependencia real, no por preferencia - Fase 3 (ayuno) necesita el research antes que nada, Fase 2 (nutrición) necesita estar hecha antes de que ese research tenga inputs reales que evaluar.
- Dentro de una fase, las épicas listadas SÍ pueden paralelizarse si hay presupuesto de sesión para ello.
- Al completar cualquier punto: actualizar su fila en la tabla de épicas de `03-vision-produccion.md` (Estado + evidencia real de verificación), añadir entrada a `CHANGELOG.md`, y si introduce un hallazgo/decisión de diseño no obvio, documentarlo en la sección "Investigación ya realizada" del vision doc para que no se repita.
