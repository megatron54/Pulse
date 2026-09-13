# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado: [SemVer](https://semver.org/lang/es/) informal (proyecto personal,
mono-usuario - no hay compromiso de compatibilidad de API entre versiones).

## [Unreleased]

### Añadido
- Persistencia completa de la composición de bioimpedancia de la báscula
  Feelfit (músculo, hueso, % agua, BMI) - antes se descartaba y solo se
  guardaba peso/% de grasa, pese a que la báscula ya la reportaba en cada
  medición.
- Reconstrucción de composición/layout (v2.1) de las 7 páginas del
  frontend, sin cambiar el tema visual Apple-clean: nuevo kit de UI
  (`StatTile`, `SegmentedControl`, `ChipFilter`, `ActivityListItem`,
  `MacroBar`, `FormField`, `Disclosure`, `PageHeader`) con patrones de
  layout inspirados en Garmin Connect/Strava/MyFitnessPal (rail de
  métricas, feed de actividades, diario de macros, formularios
  reagrupados).
- Ingesta de pasos diarios de Garmin (`GarminDailyMetrics.pasos`), visibles
  en el hero de "Hoy" junto a VFC/Body Battery/sueño/estrés.
- Ejes, unidad y leyenda visibles en las gráficas de páginas de detalle
  (Cuerpo, Entrenamiento/Recuperación/Análisis) - el `AreaTrendChart`
  minimalista sin ejes se mantiene solo en el mini-trend de "Hoy".
- Página "Entrenamiento" fusiona Recuperación y Análisis en pestañas,
  eliminando tarjetas duplicadas entre las tres rutas antiguas.
- `BodyGoalInsightCard` en "Cuerpo": compara la tendencia real de peso
  (báscula Feelfit) contra la fase de peso activa del usuario y explica si
  va en línea o desviada, sin inventar un objetivo numérico inexistente.
- Endpoint de sync manual bajo demanda `POST /users/{id}/garmin/sync`
  (solo el día pedido) y job de scheduler de sync incremental frecuente
  (cada 2h configurable) para datos quasi en tiempo real sin repetir el
  backfill histórico.
- Coach narrativo (Capa 3) por deporte: `GET /users/{id}/garmin/activities/narrative`
  reutiliza `generate_context_narrative` (Épica H) con un contexto propio de
  carga semanal (sesiones y km de la semana actual vs. media de las 4
  previas) para running/ciclismo/gimnasio, visible en la ficha de detalle de
  cada categoría.
- Fases de sueño (profundo/ligero/REM/despierto) de `get_sleep_data`, nuevas
  columnas en `GarminDailyMetrics` y desglose visual (barra apilada) en el
  histórico de Salud y recovery.
- Botón "Descargar PDF" en el resumen semanal (`PeriodicSummaryCard`) que
  exporta el informe vía el diálogo de impresión nativo del navegador
  ("Guardar como PDF"), sin depender de una librería de generación de PDF
  nueva.
- Desglose de series/reps/peso de sesiones de gimnasio (`get_activity_exercise_sets`),
  ingerido solo para actividades nuevas (nunca se relee el detalle de una
  ya vista, por el mismo motivo de riesgo de bloqueo de cuenta ya
  documentado) y visible como detalle expandible bajo cada actividad de
  gimnasio en su histórico. Nombres de campo de Garmin (`setType`,
  `repetitionCount`, `weight`, `category`) sin verificar aún contra una
  sesión de fuerza real del usuario - mismo caveat de honestidad que la
  agrupación de `typeKey` por categoría.

- Proveedor de LLM del coach desacoplado del cliente concreto (`coach/llm_client.py`:
  `LlmClient`/`LlmError` genéricos, `coach/llm_factory.py` elige el
  proveedor por variable de entorno) + soporte de Ollama local
  (`coach/ollama_client.py`) como proveedor preferido, gratis y sin
  enviar datos de salud a terceros - reemplaza la dependencia exclusiva
  de Gemini, cuyo SDK (`google-generativeai`) fue deprecado por Google.
  Gemini se mantiene como alternativa vía `GEMINI_API_KEY`.

### Corregido
- Rate-limiting al conectar Garmin: el backfill de 90 días (~900 llamadas)
  corría de forma síncrona dentro de la petición HTTP de alta y podía
  dejarla colgada varios minutos. Ahora la petición devuelve el usuario en
  cuanto login+perfil tienen éxito y el backfill continúa en background.

### Cambiado
- Navegación reducida de 7 a 5 secciones de primer nivel: Hoy, Cuerpo,
  Entrenamiento, Nutrición, Coach - Cuerpo pasa a segundo lugar.

## [0.2.0] - 2026-08-10

### Añadido
- Reconstrucción completa del frontend: design system único (Apple-clean,
  tema claro/oscuro real), navegación de 7 secciones, tarjeta de recuperación
  automática (sin check-in manual).
- Conectar Garmin como único mecanismo de alta de usuario (sustituye el
  onboarding manual), con backfill histórico automático (90 días).
- Histórico intradía de Garmin: ritmo cardíaco, body battery y estrés
  minuto a minuto.
- Conexión custom con báscula Feelfit (peso/composición corporal) vía su
  API no oficial, con sincronización nocturna automática.
- Motor propio de recomendación de planes nutricionales (déficit,
  mantenimiento, recomposición, superávit) con duración determinada -
  el sistema recomienda, el usuario confirma. Sustituye a wger para el
  diario de comidas (wger se mantiene solo para el catálogo de ejercicios).
- Logo de la app (mancuerna blanca sobre fondo negro) e iconos para
  Windows/macOS/iOS/Android/favicon web.

### Eliminado
- Diario de comidas vía wger y el check-in manual de recovery (incluido
  dolor articular) - ambos sustituidos por fuentes automáticas.

## [0.1.0] - 2026-08-05 y anteriores

Ver el historial de commits (`git log --oneline`) para el detalle completo
de esta fase inicial: motor de reglas (nutrición, progresión, periodización,
readiness), integración real con Garmin Connect y wger, dashboard visual,
diario de hábitos, prueba de concepto de app nativa de escritorio (Tauri).
