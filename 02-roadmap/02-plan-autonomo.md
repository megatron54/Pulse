# Plan de trabajo autónomo (front + back, funcionalidad completa)

> Sustituye/complementa a `01-fases-desarrollo.md`. Este documento es el
> plan operativo real para seguir construyendo sin depender de que el
> usuario esté presente. Cada fase tiene entregable, definición de
> "hecho", y qué decisiones tomo yo mismo si surge ambigüedad (con el
> criterio ya usado en esta sesión: decidir, documentar, seguir).

## Principios de ejecución autónoma

1. **No pregunto si puedo decidir con criterio de ingeniería razonable.**
   Registro la decisión en el commit/PR y en este documento si es
   arquitectónica. Solo me detengo ante bloqueos reales: credenciales
   que no tengo (Garmin real, claves de Gemini), o acciones destructivas
   irreversibles fuera del repo.
2. **TDD + code-review en cada pieza**, como en toda la sesión anterior.
3. **Cada fase termina con la app *más* funcional que al empezar**,
   verificable (tests, o una llamada HTTP real que se pueda mostrar).
4. **Un cambio de stack ya decidido en esta fase:** en vez de forkear la
   app Flutter de wger de entrada (bloqueado por necesitar el SDK de
   Flutter y un emulador/dispositivo, que no puedo verificar aquí de
   forma autónoma), el frontend v1 será una **app web (Next.js)** sobre
   la misma API REST. Es ejecutable, testeable e iterable sin ningún
   toolchain nativo. Se empaqueta luego como PWA/Capacitor para móvil
   sin rehacer el frontend. Si el usuario prefiere Flutter nativo más
   adelante, se retoma sin perder el trabajo del backend/API.

## Mapa de fases

| Fase | Entregable | Bloqueada por |
|---|---|---|
| A | API REST (FastAPI) sobre los servicios ya construidos | Nada — empiezo aquí |
| B | Frontend web (Next.js) consumiendo la API | Fase A |
| C | Scheduler diario (cron real, APScheduler) | Fase A |
| D | Auth mínima (single-user, API key/JWT) | Fase A |
| E | Integración wger (proxy de ejercicios/sets vía su API REST) | Fase A |
| F | Motor de plan semanal (TrainingBlock → sesión de cada día) | Fase A, engine ya existente |
| G | Ingesta de fotos + composición corporal en el navegador (MediaPipe.js) | Fase B |
| H | Sincronización Garmin real | **Bloqueada de verdad**: necesito credenciales reales del usuario en algún momento. Todo lo demás no depende de esto. |
| I | Dashboards de tendencia (HRV, peso, volumen) | Fase B |
| J | Empaquetado (Docker Compose único para todo el stack Pulse) | Fases A-C |

## Fase A — API REST (FastAPI)

**Por qué primero:** sin esto no hay frontend posible. Es la pieza que más desbloquea.

Entregables:
- `backend/api/main.py` — app FastAPI.
- Routers por dominio: `/readiness`, `/nutrition`, `/session`, `/body-composition`, `/users`.
- Cada endpoint es un adaptador fino sobre los `services/*` ya existentes y probados — **cero lógica nueva de negocio aquí**, solo serialización HTTP (Pydantic schemas de request/response).
- Manejo de errores: `ValueError` de los servicios → HTTP 400/404 según corresponda; `InsufficientDataError` → 422 con detalle.
- Tests con `TestClient` (httpx), sin necesidad de servidor real corriendo.
- Documentación automática (`/docs`, OpenAPI) gratis por usar FastAPI.

Definición de "hecho": se puede hacer `curl` o Postman contra `http://localhost:8000` y obtener/crear datos reales en el Postgres de Pulse.

## Fase B — Frontend web (Next.js)

Entregables:
- Scaffold Next.js (App Router, TypeScript) en `frontend/`.
- Páginas: dashboard del día (readiness + sesión + macros), registro de peso/medidas, chat con el coach.
- Cliente API tipado (fetch contra la API de Fase A).
- Sin diseño elaborado en v1: funcional primero, pulido después (coherente con "no rushear" pero priorizando que *funcione* antes que *se vea bien*).

## Fase C — Scheduler diario ✅

- `backend/scheduler/app.py`: entrypoint APScheduler (`BlockingScheduler`, cron configurable vía `PULSE_SCHEDULER_HORA`/`_MINUTO`, por defecto 04:00), ejecuta `services.scheduler_service.run_daily_sync_for_all_users` cada madrugada para todos los usuarios con `GarminCredentials` activas (nueva tabla, solo referencia a `token_store_dir` - nunca contraseñas).
- Aislamiento por usuario: un fallo sincronizando a uno (rate-limit, token caducado, `InsufficientDataError`) nunca impide sincronizar al resto ni aborta el batch (incluida la escritura de la propia auditoría del fallo).
- Job envuelto en try/except propio: un error inesperado no documentado no debe poder tumbar el proceso de larga duración.
- Sin credenciales reales todavía (Fase H bloqueada): cada pasada sincroniza 0 usuarios y termina en <1s, pero el código no necesita cambios cuando existan.
- `acwr`/`joint_pain_flag` usan valores neutrales documentados (1.0 / False) porque no hay forma automática de obtenerlos aún; el check-in manual sigue disponible para declarar dolor articular real.

## Fase D — Auth mínima

- Al ser mono-usuario, una API key simple en header (`X-API-Key`) basta para v1 — evita la complejidad de un sistema de login completo antes de que haga falta.

## Fase E — Integración wger ✅ (parcial)

- `backend/wger_client/client.py`: cliente de solo lectura del catálogo público de ejercicios de wger (categorías, equipamiento, búsqueda de ejercicios por categoría/idioma) vía su API REST (`/api/v2/`), verificado a mano contra la instancia real corriendo en `localhost` — nunca toca la base de datos de wger directamente, manteniendo la separación de esquemas de la Fase 0.
- Payload de wger (profundamente anidado, con traducciones por idioma) se aplana a los campos que Pulse necesita, con aislamiento por-item: un ejercicio malformado se omite en vez de tumbar toda la búsqueda.
- Alcance deliberado de esta primera versión: solo lectura del catálogo público (sin token). Los endpoints por-usuario de wger (peso, planes de nutrición) devuelven 403 sin autenticación y quedan fuera — se añadirán cuando Pulse necesite escribir en wger, no solo leer su catálogo de ejercicios.
- Pendiente/documentado como deuda menor: solo se lee la primera página de resultados (sin seguir `next`); aceptable mientras el catálogo de wger quepa en el límite de página configurado.

## Fase F — Plan semanal automático

- Extiende `TrainingBlock` con una tabla nueva `weekly_schedule` (día de la semana → `SessionType` planificado), y una función que, dado el bloque activo, determina `planned_session` para `session_service.compute_daily_session` sin que haya que pasarlo a mano.

## Fase G — Fotos + composición corporal en navegador

- `@mediapipe/tasks-vision` (JS) en el frontend: pose + segmentación corrida en el propio navegador del usuario (mismo principio de privacidad ya documentado: la imagen no sale del dispositivo).
- El frontend calcula las medidas y llama al endpoint de Fase A con los números, nunca con la imagen.

## Fase H — Garmin real (bloqueada)

- Todo el código ya existe y está probado con dobles. Cuando el usuario aporte credenciales/token, se ejecuta una prueba end-to-end real y se ajustan los `_extraer_*` de `garmin_sync/client.py` contra la forma real de los payloads (ya anotado como deuda técnica desde el PR original).

## Fase I — Dashboards ✅ (parcial)

- `frontend/src/components/Sparkline.tsx`: gráfica de línea en SVG puro, sin dependencia externa (Recharts/Chart.js descartados a propósito para no aumentar la superficie de auditoría del frontend por una gráfica simple - coherente con la decisión de "0 vulnerabilidades" del PR #26).
- `WeightTrendCard` (línea continua sobre `/body-measurements/history`, deduplicado a última fila por día) y `ReadinessTrendCard` (bloques de color rojo/amarillo/verde sobre `/readiness/history` - categórico, una línea continua sería engañosa) sobre los endpoints de historial ya existentes.
- Se añadió Vitest + Testing Library al frontend (no existía ningún runner de tests unitarios todavía) — 11 tests, TDD real, cableado en CI (`npm test`).
- Pendiente: gráficas de macros/nutrición y de volumen de entrenamiento (Fase F) todavía no tienen dashboard propio.

## Fase J — Empaquetado único ✅

- `docker-compose.yml` en la raíz (Postgres de Pulse + backend FastAPI + frontend Next.js) — verificado de extremo a extremo en esta sesión: `docker compose up -d --build` desde un volumen de Postgres nuevo, los 3 servicios quedan `healthy`, se creó un usuario real a través de la API corriendo en Docker.
- **Hallazgo real corregido:** un Postgres recién creado quedaba sin tablas (nada ejecutaba `create_all()` fuera de tests/CI) - el primer request fallaba con `UndefinedTable`. Corregido con `backend/scripts/ensure_schema.py` (idempotente, se ejecuta antes de `uvicorn` en el `CMD` del Dockerfile), sin acoplar esto a un lifespan de FastAPI que interferiría con los tests de integración.
- Añadido un job `docker-compose-smoke-test` en CI que reproduce este smoke test completo en cada push/PR, como regresión permanente de este hallazgo.
- Imagen del frontend: se reconstruyó y funcionó sin problemas en esta sesión (el cuelgue de `npm ci` visto anteriormente no se reprodujo).

## Registro de decisiones tomadas en este documento

- **Frontend v1 = Next.js web, no Flutter nativo** (ver principios arriba). Reevaluable más adelante sin coste de backend.
- **wger se integra vía su API REST**, no vía acceso directo a su base de datos.
- **Auth v1 = API key simple**, no OAuth/JWT completo (mono-usuario).
