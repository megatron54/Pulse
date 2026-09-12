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
