# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado: [SemVer](https://semver.org/lang/es/) informal (proyecto personal,
mono-usuario - no hay compromiso de compatibilidad de API entre versiones).

## [Unreleased]

### Añadido
- **Cada cifra del reloj se puede pulsar y tiene su propia página.** El
  usuario lo pidió así: *"me gustaría poder pulsar la puntuación de
  sueño y ver el detalle de mi noche, o de otras noches grabadas en el
  reloj. Lo mismo con body battery, VFC, estrés, pulso en reposo,
  pasos"*. Antes cada métrica era un callejón sin salida: una cifra sin
  fecha, sin unidad comparable y sin ningún sitio al que ir. Ahora las
  seis de "Hoy" y las siete de Entrenamiento › Recuperación enlazan a
  `/salud/<métrica>`, y esa página responde tres preguntas: **cuánto
  es** (el último valor con su fecha real y a qué distancia está de tu
  propia media, teñido según hacia dónde es mejor que se mueva en esa
  métrica), **cómo va** (la tendencia de 7, 30 o 90 días dibujada con
  eje, unidad y rango, más media/mínimo/máximo de la ventana) y **qué
  guardó el reloj cada día** (tabla noche a noche o día a día, y cada
  fila se despliega en su sitio).
- El detalle de una fila enseña lo que el reloj registró de verdad ese
  día, no la misma cifra otra vez: las fases de la noche en el sueño, y
  la serie minuto a minuto con eje de horas en Body Battery, estrés y
  pulso. Cuando el reloj no guardó ni fases ni serie, se dice con esas
  palabras en vez de dejar un hueco mudo (doctrina 6 y 7).
- `lib/metricasSalud.ts`: el nombre, la unidad, los decimales, el rango
  y la explicación de cada métrica viven en un único sitio, y los usan
  las cuatro pantallas que las dibujan. Con la lista duplicada, la
  misma métrica acabaría llamándose de dos formas según desde dónde se
  mirara. De ahí salen también dos cosas que no son cosméticas: que el
  sueño se cuente por **noches** y no por días (la tabla dice "Noche" y
  el resumen "30 noches"), y que la gráfica del día diga qué dibuja -
  en "Pulso en reposo" la cifra es 52 ppm y la línea sube a 180, porque
  el reloj guarda el pulso de todo el día y el reposo es solo su tramo
  más bajo.
- **El semáforo de recuperación explica su veredicto.** "Recuperación
  baja" en rojo grande era todo lo que la aplicación contaba: seis
  cifras debajo sin ninguna relación visible con el rojo, y ni una
  palabra sobre cuál de ellas lo había decidido ni sobre qué hacer. El
  usuario preguntó literalmente *"¿qué significa? ¿estoy correctamente
  descansado o no? ¿por qué está en rojo, por qué está baja, cómo puedo
  ayudarlo?"*. Ahora la tarjeta de "Hoy" dice qué significa el veredicto
  en una frase (en qué estado está el cuerpo y qué hacer hoy con el
  entrenamiento), nombra las señales que lo están bajando, y las pone
  las siete en una tabla con su valor y la referencia a partir de la
  cual dejan de pesar ("Body Battery al despertar · 24 · ≥ 50"). Debajo,
  la palanca real de cada señal que hoy pesa - como mucho tres, porque
  una lista de seis acciones no se lee.
- `engine.periodization.assess_signals`: el motor devuelve cada señal
  por separado con su estado y sus umbrales, y `compute_readiness` ahora
  **cuenta sus flags sobre ese resultado** en vez de repetir las
  comparaciones. Así el veredicto y la explicación que se muestra salen
  del mismo cálculo y no pueden contradecirse, y los umbrales viajan con
  la señal hasta la interfaz: un `30` escrito a mano en un componente de
  React se queda atrás en el primer ajuste del motor.
- La VFC se desglosa en dos señales, "frente a tu media" y "tendencia de
  7 días", aunque el motor las siga contando como un único flag. Eran
  dos preguntas distintas colapsadas en una, y la que decidía era
  justamente la que no se dibujaba en ninguna pantalla: el día que
  provocó todo esto, la tarjeta mostraba una VFC un 16 % **por encima**
  de la media junto a un veredicto rojo.
- `readiness_log.hrv_trend_7d` (migración aditiva en
  `scripts/ensure_schema.py`): era la única entrada de
  `compute_readiness` que no se guardaba, o sea la única capaz de poner
  un día en rojo sin dejar rastro consultable. Las filas anteriores
  quedan a `NULL` y la interfaz las dibuja como "sin medir" - con una
  línea que aclara que un guion ni suma ni resta al veredicto.
- `GET` y `DELETE /users/{id}/training-blocks`: el mensaje de planes
  solapados le pedía al usuario "deja solo uno activo", algo que la
  aplicación no le dejaba hacer - ni listar sus planes ni borrar uno. El
  único camino era entrar a la base de datos a mano. El borrado limpia
  también las filas de `WeeklySchedule` (la FK no declara `ON DELETE
  CASCADE`) y filtra por `user_id`, para que otro id en la URL no borre
  un plan ajeno.
- `PlanesActivosCard` en Entrenamiento › Plan: los planes del usuario
  con su estado ("En curso" / "Aún no empieza" / "Terminado") y, cuando
  dos se pisan, el aviso marcado **en las filas implicadas** y no solo
  arriba (con cuatro planes, "tienes planes que se pisan" obliga a
  comparar fechas a ojo). Borrar es en dos pasos y la confirmación
  nombra el plan: se lleva por delante varias semanas de planificación y
  no hay deshacer.
- `?seccion=` en `/entrenamiento` para enlazar a una pestaña concreta;
  "Hoy" manda ahí cuando falta el plan o cuando hay planes solapados, en
  vez de dejar al usuario en "Sesiones" buscando dónde se hace lo que se
  le acaba de pedir.
- **Design System v3** (`01-arquitectura/05-design-system-v3.md`): doctrina
  numerada y citada por número desde el código, que deroga a v2
  (`04-design-system-v2.md`, conservado como histórico). El usuario real
  rechazó v2 en los mismos términos que v1 ("hay aún mucho estilo con
  neón tipo AI slop", "lo mismo con los emoticonos", "hay muchas
  palabras que se cortan, no es un diseño de alto nivel") y pidió
  rehacer el frontend entero, "no solo el estilo y colores, TODO". Las
  reglas: el color es información y nunca adorno; un solo nivel de
  elevación, filetes de 1px y cero tarjetas anidadas; los datos
  tabulares van en una tabla; nada se corta ni se parte; toda gráfica
  lleva eje y unidad; "unknown is not zero"; los estados vacíos dicen
  qué HACER; español y fechas humanas.
- Tokens de rol (`--canvas --surface --line --line-strong --ink --ink-2
  --ink-3 --action --action-ink` + `--pos --warn --neg --data`) y escala
  tipográfica con nombre (`.t-page-title .t-hero .t-section .t-metric
  .t-body .t-secondary .t-micro .tabular`), en lugar de colores y
  tamaños elegidos caso por caso en cada componente.
- Primitivos v3 en `components/ui/`: `Card`/`CardTitle`,
  `StatTile`/`MetricGrid`, `DataList`/`DataRow`, `Table`/`Td`/`TdNum`,
  `TrendChart`, `SegmentedControl`, `Disclosure`, `FormField`,
  `CredentialsForm`, `EmptyState`, `Button`.
- Página **Perfil** (`/perfil`), que faltaba: datos propios (altura,
  sexo, fase de peso) editables vía `PATCH /users/{id}`, tema
  claro/oscuro/automático persistido en `localStorage`, y el estado
  real de las conexiones a Garmin y Feelfit (conectada o no, desde
  cuándo, cuántos días/mediciones ha traído) con su formulario de alta.
  Las credenciales de báscula y reloj dejan de vivir sueltas en las
  páginas de datos.
- `GET /users/{id}/connections`: estado de las integraciones de un
  usuario para la página Perfil. Nunca devuelve `token_store_dir` ni
  ninguna contraseña (hay test que lo fija).
- `PATCH /users/{id}` para editar el perfil propio, con `extra: forbid`
  y validación por campo.
- `lib/fechas.ts`: fechas escritas como las diría una persona
  (`fechaRelativa` → "Hoy" / "Ayer" / "12 sep") en vez de ISO en
  pantalla.
- Formulario propio para conectar la báscula Feelfit, sin pasar por
  Samsung Health/Apple Health/Fitbit/Health Connect/Google Fit - el
  backend ya hablaba directo con la API en la nube de Feelfit pero no
  existía forma de usarlo desde el frontend. (Nació en la página Cuerpo
  como `FeelfitConnectForm`; v3 lo movió a Perfil › Conexiones, donde
  vive junto al de Garmin sobre el mismo `CredentialsForm`.)
- Detección de reconexión de una cuenta de Garmin ya vinculada (por
  `garmin_email`, no secreto) en `POST /users/garmin-connect`: perder el
  `pulse_user_id` de localStorage (nuevo navegador, caché borrada) ya no
  crea un `UserProfile` duplicado ni repite el backfill completo de 90
  días - causa real del rate-limiting de Garmin reportado por el usuario.
  Un email ya visto reconecta (`200 OK`, reutiliza el `token_store_dir`
  existente, dispara solo un sync ligero del día en curso) en vez de dar
  de alta una cuenta nueva (`201 Created`, backfill completo).
- Profundización gradual del histórico de Garmin más allá de los 90 días
  iniciales: job nocturno (`profundizacion_historial_garmin`) que retrocede
  hasta 30 días más por pasada (configurable vía
  `PULSE_GARMIN_HISTORIAL_DIAS_POR_NOCHE`) hasta un máximo de ~2 años
  (`PULSE_GARMIN_HISTORIAL_MAX_DIAS`), evitando el volumen de peticiones de
  un backfill único de años que dispararía el mismo rate-limit.
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
  (Cuerpo, Entrenamiento/Recuperación/Análisis). En v3 esto pasó a ser
  la norma sin excepciones: la variante minimalista sin ejes que se
  mantenía en el mini-trend de "Hoy" es justamente la que el usuario
  señaló como ilegible, y ya no existe.
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
  Gemini se mantiene como alternativa vía `GEMINI_API_KEY`. Verificado
  contra un servidor Ollama real (`llama3.2`/`qwen2.5`): narrativas
  coherentes, barrera anti-alucinación numérica intacta, latencia
  1.3-6.5s. Corregido en el camino un hallazgo real: una respuesta podía
  mezclar caracteres de un alfabeto no latino (ej. chino) no solicitados
  - nueva barrera de forma los rechaza.

### Corregido
- **"Recuperación baja" en rojo encima de "por eso el veredicto es
  verde".** Salió en una captura de verificación, literal. La frase de
  "Por qué" deducía el color del veredicto de su propia cuenta de
  señales cruzadas, así que con ninguna cruzada daba por hecho que el
  semáforo estaba verde - y en esas filas la señal que había decidido
  (la tendencia de VFC) llegaba a `null` y se dibujaba como "sin
  medir". Ahora la frase recibe el veredicto y, cuando no lo puede
  explicar con lo que tiene, lo dice: el dato que falta, no que todo
  esté bien. La causa de fondo era un contenedor del scheduler
  ejecutando una imagen anterior a la migración de
  `readiness_log.hrv_trend_7d`, que escribía filas sin la señal
  decisoria.
- La narrativa de respaldo del coach ya no se dibuja. Sin un modelo
  configurado, el texto era un listado mecánico de las mismas seis
  cifras que la tarjeta ya enseña justo encima, con los paréntesis a la
  vista y una unidad que no es la del resto de la aplicación ("lpm"
  contra "ppm"). Repetir un dato con peores palabras no es contenido
  (doctrina 8); el bloque solo aparece cuando hay un texto escrito por
  el coach.
- **"Recuperación baja" en rojo con todas las cifras buenas.** El
  semáforo de "Hoy" contradecía a las métricas que él mismo mostraba
  debajo: VFC un 16 % POR ENCIMA de la baseline de 28 días, Body Battery
  80, sueño 85, ACWR 1.0 y sin dolor articular, y aun así ROJO. El motor
  aplicaba bien sus reglas sobre datos corruptos: `GarminDailyMetrics`
  es append-only a propósito (permite resincronizar un día sin perder
  histórico), pero `_valores_hrv_en_rango` - que alimenta tanto
  `get_hrv_baseline_28d` como `get_hrv_trend_7d` - contaba CADA fila
  como un día distinto. Con 15 sincronizaciones del mismo día (job cada
  2h + manuales), un día malo repetido pesaba 15 veces en la ventana y
  hundía `hrv_trend_7d` hasta ≈ −0,19, por debajo del umbral rojo de
  −0,10. Ahora se deduplica por día al LEER (gana el `id` más alto = la
  sincronización más reciente), mismo criterio que
  `get_daily_metrics_history`; el arreglo no es un `UNIQUE(user_id,
  fecha)`, que rompería el append-only intencionado.
- El mismo defecto en `readiness_log_repository`, y ahí no era
  cosmético: `get_recent_readiness_levels` cuenta días RED
  **consecutivos** para decidir si pausa el déficit calórico, así que un
  único día rojo recalculado cinco veces se leía como cinco días rojos
  seguidos y disparaba un guardrail de seguridad que nadie había
  cumplido. Además, sin ordenar por `id` dentro de la fecha, cuál de las
  filas duplicadas ganaba era indeterminado. `get_readiness_history`
  (gráfica de tendencia) devolvía cinco puntos apilados en la misma
  fecha por el mismo motivo.
- Dos planes de entrenamiento solapados dejaban a "Hoy" sin poder
  decidir la sesión, y sin decir por qué ni cómo salir de ahí: el
  backend lanzaba "user_id=4 tiene múltiples TrainingBlock activos y
  solapados" (un id interno y el nombre de un modelo en pantalla,
  doctrina 8) con un `motivo` que el frontend no mapeaba, así que la
  tarjeta degradaba a "Falta algún dato para decidir la sesión de hoy"
  sin ninguna acción. Ahora hay un error tipado
  (`OverlappingTrainingBlocksError`, `motivo: "planes_solapados"`) con
  texto escrito para una persona, la tarjeta explica el conflicto y
  enlaza a la pestaña donde se resuelve.

- La narrativa de salud del día (página "Hoy") filtraba jerga interna en
  pantalla cuando caía a la plantilla de respaldo (sin LLM o tras
  fallarle la validación): "(hrv_hoy_ms: 69.0, hrv_baseline_28d_ms:
  59.3, body_battery: 80, sleep_score: 85...)" — nombres de campo en
  inglés y snake_case, no texto de interfaz (doctrina 8). La causa: el
  diccionario `datos` que arma `health_narrative_service.py` (y su
  hermano `sport_narrative_service.py`, mismo patrón) usaba las claves
  internas del modelo directamente como texto a mostrar, y la plantilla
  genérica de `narrative_service.py` solo cambia "_" por espacios, no
  traduce. Ahora ambos servicios arman `datos` ya con claves en español
  legible y su unidad ("VFC hoy (ms)", "Body Battery", "pulso en reposo
  (lpm)"...).
- Una actividad recién terminada en el reloj no aparecía en Pulse hasta
  el día siguiente: ni el job de sync frecuente (`sync_frecuente_garmin`,
  cada 2h) ni el botón "actualizar ahora" (`POST
  /users/{id}/garmin/sync`) sincronizaban actividades - solo recovery.
  Las actividades solo se traían en el job nocturno de una vez al día
  (`sync_actividades_garmin`, 04:15). Ahora ambos caminos también
  sincronizan actividades (ventana de los últimos 3 días, igual que el
  job nocturno, para no perder una que Garmin tardó en consolidar). El
  arreglo es barato porque `sync_activities` ya es idempotente
  (`save_activity_if_new`): repetirla en cada pasada no duplica nada.
- La gráfica de tendencia rellenaba el área bajo la curva con un
  degradado, y mentía dos veces: el relleno se lee como "cantidad desde
  cero" cuando ningún eje parte de cero (el del peso empieza en 75 kg),
  y con la línea partida por los huecos de datos cada tramo cerraba el
  relleno con un tajo vertical hasta la base - la captura de la
  auditoría mostraba tres losas grises con paredes rectas donde solo
  hay tres rachas de pesadas. Ahora es una línea sin relleno, y el
  componente se llama `TrendChart` y no `AreaTrendChart`.
- Cabeceras de tabla pegadas entre sí: los `th` no tenían gotera
  (`pr-4`) mientras las celdas sí, así que a 390px "DURACIÓN DISTANCIA
  FC MEDIA" se leía como una sola palabra. Las cifras además se alinean
  ahora con la PRIMERA línea de la celda de texto, no centradas entre
  sus dos líneas.
- Tabla de sesiones a 390px: cinco columnas no caben de ninguna manera
  (al nombre le quedaban 40px y "Natación en piscina" salía en tres
  líneas). La fecha pasa a ir bajo el nombre de la sesión - no es una
  línea partida, es otro dato - y "FC media" pasa a "Pulso", una
  cabecera de una palabra y del mismo vocabulario que el resto de la
  app.
- Franja muerta de 36px entre el título y la tabla en la pestaña
  "Todas" de sesiones, que se leía como un elemento que no había
  cargado: el hueco lo pone la narrativa del coach cuando existe, no el
  contenedor.
- Calendario de recuperación del mes: la altura de las barras crecía
  con lo bueno que fuera el día (óptima 16px, baja 1px), así que los
  días de recuperación baja - justo lo que hay que ver - eran rayas de
  un píxel indistinguibles del marcador de "sin datos". Ahora la altura
  crece con la gravedad, ninguna baja de 6px, y los días sin dato se
  marcan con un filete discontinuo que no compite en forma con una
  barra. Las muestras de la leyenda coinciden con las marcas de la
  rejilla.
- Desplegables del plan semanal: "Intervalos de resistencia" quedaba
  cortado por la flecha del `<select>` a 390px, y los siete días
  quedaban desalineados en escalera porque el borde de cada desplegable
  caía donde acabase su etiqueta.
- El `detail` de los 502 de `/exercises` era `str(exc)`, y la auditoría
  lo encontró escrito tal cual en la pantalla de Entrenamiento: "Fallo
  de conexión con wger: [Errno 111] Connection refused". Nombraba una
  dependencia interna que el usuario no conoce (y pidió no ver) y añadía
  un errno de sistema. Ahora el usuario lee un mensaje escrito para una
  persona y el texto real va al log del servidor. Mismo arreglo en el
  404 de `POST /users/{id}/feelfit-connect`, que mostraba "No existe
  UserProfile con id=5".
- Tope de `days` en `GET .../body-measurements/history` subido de 730
  días a 10 años: con 2 años el frontend recibía 65 de las 275 pesadas
  importadas de la báscula y no podía pedir el resto, en contra de la
  petición explícita del usuario de ver el histórico completo.
- Rate-limiting al conectar Garmin: el backfill de 90 días (~900 llamadas)
  corría de forma síncrona dentro de la petición HTTP de alta y podía
  dejarla colgada varios minutos. Ahora la petición devuelve el usuario en
  cuanto login+perfil tienen éxito y el backfill continúa en background.
- Página "Hoy" (y cualquier consulta a métricas diarias de Garmin) rota
  por columnas (`pasos`, fases de sueño) presentes en el modelo pero
  nunca creadas en Postgres (`UndefinedColumn`) - la migración aditiva
  de `ensure_schema.py` no se había actualizado al añadir esas columnas
  en una sesión anterior. Añadida la migración que faltaba.

### Cambiado
- Frontend rehecho sobre el Design System v3: fuera los degradados, los
  brillos, los bordes de color y los iconos decorativos que el usuario
  identificó como "AI slop". Ningún emoji en la interfaz.
- La pantalla "Hoy" responde a una sola pregunta ("cómo estoy hoy y qué
  hago hoy") y pierde dos bloques que el usuario señaló como inútiles
  ahí:
  - la tendencia de readiness, que eran 30 círculos de color sin eje,
    sin fechas y sin cifras, con el significado accesible solo al pasar
    el cursor (inexistente en móvil) y con `flex-wrap` partiendo la
    línea temporal. Una tendencia de 30 días no es "hoy": pasa a
    Entrenamiento › Recuperación, rehecha con eje y cifras.
  - el objetivo nutricional, cuyo único contenido en esa página era un
    botón "Calcular macros de hoy" - una tarjeta que no informaba de
    nada y exigía pulsar para calcular algo que el motor resuelve solo.
    El objetivo vive en Nutrición, ya calculado.
- "Coach" sale del nav principal y entra "Perfil": gastaba un quinto de
  la navegación para decir "todavía no está construido" (y su estado
  vacío exponía jerga interna del proyecto), mientras que su valor real
  ya se entrega como narrativa en contexto dentro de las páginas.
  Navegación final: Hoy, Cuerpo, Entrenamiento, Nutrición, Perfil.
- Etiqueta corta propia para cada destino del nav en móvil: a 390px
  cinco destinos dejan ~78px y "Entrenamiento" no cabe. Se acorta a
  "Entreno" en vez de truncar con elipsis.
- Credenciales de Garmin y Feelfit movidas a Perfil; las páginas de
  datos ya no piden contraseñas.
- `01-arquitectura/04-design-system-v2.md` marcado como **derogado**, con
  el motivo documentado, en lugar de borrado - para no volver a acumular
  capas de rediseño incrementales sin dirección única.
- Los 502 del catálogo de ejercicios se capturan por tipo
  (`WgerAuthError`/`WgerRequestError`) y no con un `except Exception`:
  un fallo inesperado del proxy sale como 500 y se ve, en vez de
  disfrazarse de "wger está caído".
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
