# Integración con Garmin para uso personal

## Resumen ejecutivo

Existe un ecosistema maduro de herramientas no oficiales para extraer tus propios datos de Garmin Connect sin pasar por el programa de partner del Health API oficial (que requiere aprobación comercial). El pilar es **`python-garminconnect`**, clonado localmente en `recursos/repos/python-garminconnect/`.

## 1. `python-garminconnect` (cyberjunky) — la librería estándar

- Repo: https://github.com/cyberjunky/python-garminconnect — MIT, ~2.7k★, muy activo.
- Autenticación: motor nativo que emula el login de la app móvil oficial (reemplazó a la librería `garth`, discontinuada en 2026 tras un cambio de Garmin). Usa múltiples estrategias de login en cascada + impersonación TLS (`curl_cffi`) para evitar bloqueos de Cloudflare.
- Datos expuestos (130+ métodos, 13 categorías): perfil, actividades y entrenamientos, HRV, VO2max, training status/readiness, Body Battery, stress, sueño, composición corporal/peso, hidratación, nutrición diaria, subida de workouts.
- Tokens guardados localmente en `~/.garminconnect/garmin_tokens.json` (permisos 0600), con auto-refresh indefinido mientras el refresh token viva.

## 2. Riesgos reales y cómo mitigarlos

- **Rate limiting por cuenta** (no por IP): login repetido fallido puede bloquear la cuenta 48-72h (documentado en el foro oficial de Garmin). Mitigación: **cachear el token siempre**, nunca relogin salvo expiración real, sincronizar solo 1x/día (ventana nocturna).
- **No hay casos documentados de ban permanente** por uso 100% personal/no comercial. El consenso de comunidad (miles de usuarios, dashboards públicos en Grafana Labs) es que el riesgo es bajo para 1 usuario.
- **Fragilidad técnica**: cada cambio de backend de Garmin puede romper la librería temporalmente (pasó con `garth` en 2026). Hay que asumir mantenimiento continuo y vigilar el CHANGELOG.

## 3. Alternativas / redes de seguridad

| Método | Uso |
|---|---|
| Exportación GDPR ("Export Your Data") | Backup trimestral/anual del histórico completo (ZIP con FIT+CSV) |
| Parseo directo de `.FIT` | `fitparse` (clonado en `recursos/repos/python-fitparse/`) o el fork mejor mantenido `fitdecode` — 100% offline, sin riesgo de cuenta |
| GoldenCheetah | Software desktop con importador FIT nativo y motor de métricas, útil para análisis offline |

**Nota:** no existe ningún webhook/callback personal sin ser partner oficial — todo uso no-partner es polling activo.

## 4. Proyectos de referencia (para inspirarse en la arquitectura de sync)

| Proyecto | Qué hace |
|---|---|
| [arpanghosh8453/garmin-grafana](https://github.com/arpanghosh8453/garmin-grafana) | Vuelca datos a InfluxDB + dashboard Grafana, Docker/K8s, backfill histórico — el más completo |
| [tcgoetz/GarminDB](https://github.com/tcgoetz/GarminDB) | Descarga a SQLite + notebooks Jupyter — más simple |
| [cyberjunky/home-assistant-garmin_connect](https://github.com/cyberjunky/home-assistant-garmin_connect) | Integración Home Assistant, 130+ sensores |
| [the-momentum/open-wearables](https://github.com/the-momentum/open-wearables) | Plataforma self-hosted que unifica Garmin + otros wearables en una API "AI-ready" — muy relevante para este proyecto |

## 5. Arquitectura de sincronización recomendada

```
Cron diario (1x/día, ventana nocturna ~04:00)
  → python-garminconnect (reutiliza SIEMPRE el token cacheado)
  → try/except con backoff exponencial ante 429/403 (NUNCA reintentar login agresivamente)
  → Staging local (JSON crudo) en disco
  → ETL idempotente → Postgres/SQLite (tablas: actividades, hrv, sleep, body_battery, training_readiness, body_composition)
  → Dashboards/consumo desde la app

Redes de seguridad:
  1. Export GDPR trimestral (backup total)
  2. Descarga manual ocasional de .FIT de actividades críticas (carreras/eventos)
  3. Vigilar releases de cyberjunky/python-garminconnect
```

## Decisión para este proyecto

Empezar con `python-garminconnect` (ya clonado en `recursos/repos/`) integrado directamente en el backend Python, con sincronización 1x/día y almacenamiento propio (no depender de Grafana/InfluxDB salvo que se quiera un dashboard aparte). Es la opción de menor esfuerzo con mayor cobertura de datos para un proyecto de un solo usuario.

## 6. Causa real del rate-limiting sufrido en producción (2026) y vías descartadas hacia tiempo real

Investigación puntual tras un episodio real de rate-limiting al conectar una cuenta (login colgado ~5 min, luego bloqueo). **No era un problema de reintentos de login** (esa política ya estaba bien resuelta en `garmin_sync/client.py`: un solo intento, token cacheado, nunca relogin agresivo). La causa real: `garmin_onboarding_service.connect_new_user_via_garmin` disparaba `backfill_full_history` de 90 días **dentro de la misma petición HTTP síncrona** — 7 llamadas de recovery + 3 de intradía por día × 90 días ≈ 900 peticiones secuenciales en un solo login, justo el patrón de volumen que la sección 2 de este documento ya advertía como riesgo. Arreglado moviendo el backfill a una tarea en background (`api.routers.users._ejecutar_backfill_en_background`) que corre con su propia sesión de BD tras responder al cliente.

De paso, se investigaron las vías reales a tiempo real/quasi-tiempo real de un reloj Garmin, para no repetir la investigación:

- **Health API oficial de Garmin** (push a webhook, near-real-time tras cada sync del reloj con el móvil): la vía técnicamente correcta a largo plazo, pero el programa de desarrollador está **pausado para altas nuevas** — no viable hoy. Revisar periódicamente si reabre.
- **MCP de Garmin para Claude** (Taxuspt/garmin_mcp, Nicolasvegam/garmin-connect-mcp, etc.): **mito descartado** — son wrappers sobre la misma API no oficial (`python-garminconnect`) que ya usa Pulse, expuesta como herramientas a un LLM vía polling. No dan ninguna ventaja de latencia ni de volumen de llamadas; no hay nada reutilizable de ahí que Pulse no tenga ya.
- **App Connect IQ propia en el reloj** que empuje datos por BLE/wifi a un servidor propio (`makeWebRequest`): técnicamente posible, pero requiere desarrollar y mantener una app nativa del reloj, con desconexiones BLE documentadas en el foro de desarrolladores de Garmin bajo uso sostenido, coste de batería, y pérdida de otras funciones del reloj mientras corre. Desproporcionado para un proyecto personal de un solo usuario.
- **Conclusión**: sin el programa oficial (pausado), no hay tiempo real real accesible. Lo alcanzable y ya implementado: sync incremental frecuente del día en curso (job `sync_frecuente_garmin` cada 2h por defecto, más un endpoint `POST /users/{id}/garmin/sync` bajo demanda) — pocas llamadas por pasada (~10), sin repetir el histórico, dando datos con minutos-horas de retraso en vez del 1x/día anterior.
