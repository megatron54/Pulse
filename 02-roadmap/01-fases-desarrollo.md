# Roadmap por fases

> Filosofía: sin prisa, cada fase debe quedar sólida (con tests) antes de pasar a la siguiente. No se rusheará.

## Estado real a fecha de esta actualización (238 tests, 16 PRs fusionados)

- ✅ **Fase 0 (cimientos):** wger corriendo en Docker, Postgres propio de Pulse, sync Garmin sin red real en tests.
- ✅ **Fase 1 (motor de reglas):** nutrition, progression, periodization, guardrails, body_composition — Capa 1 completa y 100% determinista.
- ✅ **Orquestación (no estaba en el plan original como fase separada, pero es donde ha ido el esfuerzo principal):** `readiness_service`, `nutrition_service`, `session_service`, `body_composition_service` conectan Capa 1 + persistencia + Garmin de extremo a extremo.
- ✅ **Capa 3 conversacional:** implementada con Google Gemini (free tier) + fallback determinista garantizado — decisión de stack que sustituye a GPT-4o-mini/Ollama del plan original.
- ⬜ **Fase 2 (análisis corporal por foto):** solo la fórmula (Navy) está hecha. Falta la ingesta real de fotos + MediaPipe Pose para derivar medidas automáticamente — hoy `record_body_measurement` recibe medidas ya tomadas a mano.
- ⬜ **Fase 3 (app cliente):** no empezada. Sigue siendo fork de la app Flutter oficial de wger.
- ⬜ **Motor de periodización de bloques/rotación semanal:** `decide_session` decide el día a partir de un `planned_session` recibido como parámetro; el subsistema que decide automáticamente qué toca cada día de la semana (usando `TrainingBlock`) no está construido — se dejó fuera deliberadamente para no improvisar un diseño de scheduling sin pensarlo con cuidado.
- ⬜ **Integración de series/repeticiones reales:** `engine/progression.py` (1RM, doble progresión, RIR) está completo y probado, pero no conectado a persistencia porque esos datos viven en el tracking de wger (base de datos separada) — pendiente decidir cómo integrar (API REST de wger vs. tabla propia).
- ⬜ **Cron real:** `sync_and_compute_readiness` se ejecuta hoy manualmente/desde tests; falta el scheduler diario real (Fase 0 lo mencionaba, no implementado).

## Fase 0 — Cimientos (infraestructura, sin IA todavía)
- Desplegar wger self-hosted vía Docker Compose.
- Poblar BD de ejercicios (wger + free-exercise-db como complemento).
- Configurar Postgres con las tablas nuevas de `03-modelo-datos.md`.
- Implementar `garmin_sync/` con `python-garminconnect`: cron diario, cacheo de token, staging JSON crudo → ETL a Postgres.
- Exportación GDPR manual inicial como backup histórico.
- **Criterio de salida**: puedes ver tus datos de Garmin de los últimos 30 días en tu propia base de datos, sincronizados automáticamente cada noche, con tests de la capa de ingesta.

## Fase 1 — Motor de reglas determinista (el corazón del sistema)
- `engine/nutrition.py`: TDEE (Mifflin-St Jeor) + macros por objetivo/fase.
- `engine/progression.py`: RIR/%1RM, doble progresión de series.
- `engine/periodization.py`: readiness score (RED/YELLOW/GREEN), bloques de periodización, ACWR.
- `engine/guardrails.py`: reglas duras de seguridad (dolor→descanso, déficit mínimo, ACWR máximo).
- Tests unitarios exhaustivos de todo el motor (TDD, sin excepciones — esta capa decide cosas que importan).
- **Criterio de salida**: el sistema puede decidir automáticamente qué entrenar hoy y cuántas calorías/macros, sin ninguna IA, con 100% de las decisiones testeadas y auditables.

## Fase 2 — Análisis corporal por foto
- Pipeline MediaPipe Pose on-device (móvil) para landmarks + segmentación.
- Fórmula Navy calibrada con altura del usuario.
- UI de protocolo de fotos (guía de ángulo/luz/distancia).
- Almacenamiento cifrado local de fotos de progreso.
- **Criterio de salida**: puedes hacerte una foto y obtener un rango de %grasa corporal + tendencia de 4-6 semanas, todo procesado en el dispositivo.

## Fase 3 — App cliente (Flutter, fork de wger)
- Fork de la app Flutter oficial de wger.
- Integrar las nuevas pantallas: readiness diario, plan del día (entreno+nutrición ya calculados), fotos de progreso, dashboards de tendencia.
- Sincronización con el backend propio (no solo wger nativo).
- **Criterio de salida**: app funcional en tu móvil y escritorio mostrando el plan del día generado por el motor de reglas.

## Fase 4 — Capa conversacional (IA)
- Integrar LangGraph con Store de memoria de usuario + checkpointer de conversación.
- Nodo final del grafo: LLM (GPT-4o-mini o local) que recibe decisiones tipadas del motor de reglas y redacta explicaciones.
- Validador post-output.
- Chat en la app conectado a este flujo.
- **Criterio de salida**: puedes preguntarle al coach "¿por qué hoy toca esto?" y recibir una explicación coherente basada en tus datos reales, nunca inventada.

## Fase 5 — Análisis de comida por foto
- Integración LLM Vision (patrón Nutritheous) para estimar macros desde foto de comida.
- Flujo de confirmación/ajuste manual antes de registrar.
- **Criterio de salida**: puedes fotografiar un plato y obtener una estimación de macros que puedes corregir antes de guardar.

## Fase 6 — Refinamiento y multi-objetivo avanzado
- Rotación de bloques de periodización multi-objetivo completa (fuerza+hipertrofia+resistencia+artes marciales+cortes simultáneos).
- Ajuste fino de guardrails con datos reales de uso propio.
- Dashboards de tendencia avanzados (fuerza, VO2max, composición corporal, adherencia).

## Reglas de todo el roadmap
- Cada fase se cierra con tests pasando y una revisión de código (@code-reviewer) antes de avanzar.
- No se activa la Capa 3 (IA) hasta que la Capa 1 (motor de reglas) esté sólida y probada — la IA nunca es un atajo para no terminar la lógica determinista.
- Uso personal primero: no se diseña para multiusuario hasta que el sistema funcione bien para ti durante al menos un ciclo completo de entrenamiento (8-12 semanas).
