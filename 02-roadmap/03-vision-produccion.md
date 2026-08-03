# Visión de producto: Pulse como app de producción (WHOOP/Garmin-like)

> Documento de trabajo vivo. Creado tras petición explícita del usuario de
> escalar Pulse de "app funcional" a "producto pulido, listo para vender".
> Esto es un proyecto de **meses**, no de una sesión — este documento existe
> para que cualquier sesión futura (mía o de otro agente) continúe
> exactamente donde se dejó, con criterio y evidencia, sin re-investigar
> lo ya investigado ni fingir progreso que no existe.

## Cómo se está operando este proyecto

- **No hay "cientos de agentes en paralelo corriendo indefinidamente"** de forma literal - eso no es técnicamente viable en una sesión de agente. Lo que sí se hace: delegar investigación/auditoría a subagentes especializados en paralelo cuando el trabajo es independiente (ya hecho: 4 investigaciones en paralelo para este documento), y ejecutar la construcción secuencialmente con TDD + revisión de código + verificación real (Playwright, curl, Docker) en cada pieza, igual que el resto del proyecto hasta ahora.
- **Honestidad de progreso innegociable**: cada épica de este documento se marca como hecha solo cuando está verificada de verdad (tests pasando + build + revisión +, cuando aplica, prueba visual real). Nunca se declara "listo para producción" sin evidencia.
- **Reutilizar antes que reinventar** (petición explícita del usuario): antes de escribir una integración externa nueva, se investiga primero si wger (ya integrado) o el propio backend ya lo resuelven.

## Investigación ya realizada (no repetir)

### 1. Nutrición — wger ya resuelve esto, no añadir una tercera fuente
wger expone un módulo de nutrición completo en su API REST (ya usado por `wger_client/` para ejercicios):
- `ingredient/` / `ingredientinfo/` - catálogo de alimentos, en realidad datos de **Open Food Facts re-normalizados** (`source_name: "Open Food Facts"`). Público, sin auth, 120/min lista, 300/min detalle.
- `nutritionplan/` / `meal/` / `mealitem/` / `nutritiondiary/` - planes de dieta, comidas estructuradas, y el diario de consumo real (esto es exactamente el "food log" que falta).
- **Gotchas a programar defensivamente:**
  - Los campos numéricos de nutrientes vienen como **strings** (`"protein": "6.100"`) - castear a `Number` antes de sumar, si no, concatenación de strings silenciosa.
  - `fiber`/`is_vegan` suelen ser `null` (hereda la dispersión de datos de OFF) - nunca asumir presencia.
  - El orden de la lista de ingredientes **no está garantizado** - nunca asumir que `results[0]` es estable.
  - **CVE-2026-27839**: IDOR conocido en los sub-endpoints `.../nutritional_values/` de `nutritionplan`/`meal`/`mealitem` (filtra macros de otros usuarios vía PK secuencial). Confirmar que la instancia de wger usada está parcheada, o evitar esos sub-endpoints y calcular agregados en nuestro propio backend a partir de `mealitem`/`nutritiondiary` ya acotados al usuario autenticado.
- USDA FoodData Central y Open Food Facts directo: **descartados para v1** (más trabajo de integración por menos beneficio que reutilizar wger). Revisar solo si se necesita precisión de micronutrientes que wger/OFF no dan.

### 2. Garmin — actividades (carrera/ciclismo/fuerza) nunca se han sincronizado, solo recovery diario
El cliente actual (`garmin_sync/client.py`) solo trae HRV/training readiness/body battery/sueño - **nunca actividades**. Para añadir carrera/ciclismo/fuerza:
- Librería `python-garminconnect` (ya dependencia) expone `get_activities(start, limit)`, `get_activities_by_date(...)`, y detalle vía `get_activity_details`/`get_activity_exercise_sets` (este último es el que da series/reps/peso para fuerza).
- Forma del JSON de cada actividad: `activityType.typeKey` discrimina el deporte (`"running"`, `"cycling"`/`"road_biking"`, `"strength_training"`). Carrera trae `distance`, `avgStrideLength`, `steps`, `vO2MaxValue`. Ciclismo trae `averagePower`, `normalizedPower`, `trainingStressScore`. Fuerza no trae distancia/velocidad útiles - usar `get_activity_exercise_sets` para el desglose real.
- **Riesgo de bloqueo de cuenta**: el patrón peligroso NO es sondear `get_activities` con el token cacheado, es volver a hacer login repetidamente. Mantener la regla ya existente (un solo intento de login, token cacheado) y añadir: sondear la lista de actividades como mucho cada 15-60 min, y solo llamar a los endpoints de detalle (pesados) para IDs de actividad nuevos, nunca releer detalle de actividades ya vistas.
- Proyecto de referencia para inspiración de modelo de datos (no para reusar código directamente, es una app standalone con su propio stack InfluxDB): `arpanghosh8453/garmin-grafana`.

### 3. Fotos de progreso + composición corporal — NO calcular %grasa desde una foto
Investigación concluyente: MediaPipe Pose Landmarker (`@mediapipe/tasks-vision`, tarea `PoseLandmarker`) da 33 landmarks de pose en 2D/pseudo-3D, **no circunferencias corporales**. Sin profundidad real ni múltiples ángulos calibrados con objeto de referencia, un %grasa derivado de una sola foto **no es defendible** - violaría el principio ya aplicado en este proyecto de "nunca falsa precisión" (el propio método Navy con cinta métrica ya se cuida de esto mostrando siempre un rango, nunca un número puntual).
- **Plan v1 correcto**: capturar landmarks por foto (frontal/lateral/espalda, ya modelado en `ProgressPhoto.angulo`), mostrar solo una **tendencia relativa de silueta** (ratios hombro/cintura/cadera cambiando con el tiempo), etiquetada explícitamente como eso - nunca un número de %grasa.
- Un %grasa foto-derivado con rango (más ancho que el de la cinta métrica) solo como posible v2/experimental, exigiendo múltiples ángulos + objeto de referencia/altura conocida, y siempre contrastado contra el método Navy.
- Gotchas técnicas: todo cliente (`"use client"`, nunca SSR), servir los assets WASM/modelo desde `public/` propio (no CDN, por privacidad/CSP), modelo `full` (~9MB) cargado perezosamente solo al entrar al flujo de foto, nunca en el bundle principal.

### 4. Auditoría de features frente a WHOOP/Garmin Connect/Strava
Backlog priorizado (ver detalle completo en el research; resumen aquí):

**MUST-HAVE** (tabla de apuestas para un "coach personal" creíble):
1. Carga de entrenamiento numérica (ratio agudo:crónico) - hoy solo existe el semáforo categórico. Con datos ya existentes, sin integración nueva.
2. Vista de detalle por sesión (series/reps o ritmo/HR por intervalo, notas).
3. Diario de hábitos tipo "WHOOP Journal" (sueño, cafeína, alcohol, estrés) correlacionado con recovery en el tiempo. Backend nuevo, sin integración externa.
4. Resumen periódico (semanal/mensual) de tendencias - agregación sobre datos ya existentes.
5. **Activar Garmin real** - el desbloqueo de mayor apalancamiento, del que dependen varios SHOULD-HAVE.
6. Tracking de adherencia al plan (¿hiciste lo que tocaba?).
7. Predicción de rendimiento/cuenta atrás a evento, condicional a si hay usuarios de resistencia.

**SHOULD-HAVE**: constructor de entrenamientos estructurados/push a reloj, alertas de desviación de baseline (RHR/HRV fuera de lo normal), monitor de estrés (depende de datos Garmin reales), planificador de rutas, informe exportable en PDF, escritura en wger (hoy solo lectura).

**WON'T-HAVE-YET (explícito, no es scope creep sin querer)**: feed social, kudos/comentarios, segmentos/leaderboards, clubs/retos grupales, hardware, dashboards multi-usuario para entrenadores, chatbot conversacional de IA (la app ya puede mostrar la misma información como vistas estructuradas antes de necesitar un chat).

## Épicas de trabajo (orden sugerido, no todas bloquean entre sí)

| # | Épica | Estado | Depende de |
|---|---|---|---|
| 1 | Arquitectura de información: navegación multi-página responsive | ✅ Hecho (este PR) | - |
| 2 | Backend: ingestión de actividades Garmin (carrera/ciclismo/fuerza) | ⬜ Pendiente | Fase H (credenciales reales) para probar de verdad; el código se puede construir y testear con dobles antes |
| 3 | Backend: carga de entrenamiento numérica (acute:chronic ratio) | ⬜ Pendiente | Ninguna - datos ya existentes |
| 4 | Backend + frontend: food log real vía wger (nutritionplan/meal/nutritiondiary) | ⬜ Pendiente | Verificar parche del CVE-2026-27839 en la instancia de wger usada |
| 5 | Frontend: página Garmin con datos reales (una vez haya Fase H o al menos ingestión de actividades) | ⬜ Pendiente | Épica 2 |
| 6 | Frontend: selector de ejercicios de wger dentro de una sesión | ⬜ Pendiente | Ninguna - el cliente ya existe |
| 7 | Diario de hábitos (journal) + correlación con recovery | ⬜ Pendiente | Ninguna |
| 8 | Resumen periódico / informe exportable | ⬜ Pendiente | Ninguna |
| 9 | Fotos de progreso: captura de landmarks + tendencia de silueta (SIN %grasa desde foto) | ⬜ Pendiente (Fase G) | Ninguna |
| 10 | Gráficas de volumen por deporte (fuerza/hipertrofia vs. resistencia) | ⬜ Pendiente | Épicas 2 y 3 para tener datos reales que graficar |

## Principios que no cambian con la escala del proyecto

- TDD real, revisión de código antes de cada merge, verificación honesta (no fingir que algo funciona sin probarlo).
- Nunca falsa precisión: rangos donde el dominio es incierto, categorías donde el motor de reglas es categórico.
- Reutilizar wger antes que añadir una integración externa nueva.
- Documentar cada decisión y hallazgo aquí, para que la siguiente sesión no repita la investigación.
