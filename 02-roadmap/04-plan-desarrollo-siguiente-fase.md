# Plan de desarrollo: siguiente fase

> Reescrito de cero el 2026-09-13 (la versión anterior de este documento
> quedó completada u obsoleta - en concreto, proponía construir el diario
> de nutrición sobre wger, que el usuario ya rechazó explícitamente en la
> Épica 4, ver `03-vision-produccion.md`). Este documento sigue sin repetir
> investigación ya hecha - cada punto enlaza a la sección correspondiente
> de [`03-vision-produccion.md`](03-vision-produccion.md) (fuente de
> verdad de estado/hallazgos). Actualizar la tabla de épicas de ese
> documento según se complete cada punto - este plan no la duplica, la
> ordena.

## Estado de partida (2026-09-13)

Backend: 708 tests en verde (1 fallo conocido y no relacionado: falta
`psycopg2` en el entorno de desarrollo local, el driver de Postgres no
hace falta para correr la suite contra SQLite). Frontend: 155 tests en
verde, `npx tsc --noEmit` y `npm run build` limpios. `ruff check` sin
hallazgos reales (solo variables de test intencionalmente sin usar).

Limpieza hecha en esta sesión: eliminado `Sparkline.tsx` (componente
huérfano, sin referencias reales, superseded por `AreaTrendChart`),
imports muertos en 6 archivos de test (`ruff --fix`). El resto del
repositorio está sano - sin routers/servicios huérfanos, sin
dependencias de `requirements.txt` sin usar.

Recién completado (ver Épica L de `03-vision-produccion.md`): el coach
(Capa 3) ya no depende de un cliente concreto. `coach/llm_client.py`
define `LlmClient`/`LlmError` genéricos; `coach/llm_factory.py` elige el
proveedor real por variable de entorno. Motivo: el SDK `google-generativeai`
que usaba el coach está deprecado por Google (confirmado por warning real
en los tests). Ollama (servidor local, gratis, sin enviar datos a
terceros) es ahora el proveedor preferido; Gemini se mantiene como
alternativa. **Falta la mitad de este trabajo: probarlo contra un
servidor Ollama real** - ver Fase 1 de este plan.

Añadido el 2026-09-13 (sesión de uso real, no planificada): rate-limiting
real de Garmin reportado por el usuario, causado por `garmin_connect`
creando siempre un `UserProfile` nuevo (sin detectar cuenta ya conectada)
- corregido con detección de reconexión por `garmin_email` +
profundización gradual del histórico (job nocturno, ver CHANGELOG). De
paso se encontró y corrigió un bug de producción real: `garmin_daily_
metrics.pasos` y las 4 columnas de fases de sueño existían en el modelo
pero nunca se migraron a Postgres, rompiendo toda consulta de métricas
diarias (incluida la página "Hoy" completa). Se añadió también el
formulario de conexión de Feelfit que faltaba en el frontend (el backend
ya existía, sin UI).

Actualizado el 2026-09-14: **Fase 0 hecha, pero no como estaba
planteada** - el usuario pidió rehacer el frontend desde cero en vez de
aplicarle los seis elementos visuales de la referencia fintech que
proponía el plan original. Ver Fase 0 para el porqué y para lo que se
hizo (Design System v3). Estado tras esa reconstrucción: backend 737
tests en verde (el mismo fallo conocido de `psycopg2`), frontend 242
tests en 43 archivos, `npx tsc --noEmit` y `npx eslint src` limpios.
Nota de arqueología, porque el párrafo de arriba se quedó desfasado:
`AreaTrendChart` - el sustituto por el que se borró `Sparkline.tsx` -
también se fue en v3, reemplazado por `TrendChart` (línea sin relleno).

## Cómo se ha priorizado este plan (criterio, no solo orden numérico)

1. **Terminar lo empezado antes de abrir algo nuevo**: el proveedor Ollama
   se implementó pero nunca se ejecutó contra un servidor real - eso es
   lo primero, no una épica nueva.
2. **No construir sobre una decisión de producto ya revertida**: el
   diario de nutrición NO se construye sobre wger (ver más arriba) - se
   necesita una decisión explícita del usuario sobre la alternativa antes
   de escribir código, no asumirla.
3. **Research ya cerrada > research pendiente**: fotos de progreso (Fase
   3) tiene una decisión técnica ya tomada y documentada (MediaPipe, sin
   %grasa desde foto) - ejecutable ya. El ayuno intermitente (Fase 5) y
   las integraciones externas (Fase 6) siguen bloqueadas por research
   dedicada que no se ha hecho.
4. **Deuda técnica real detectada, no solo "nice to have"**: ninguna se
   encontró de peso en esta sesión más allá de lo ya limpiado - se anota
   en la Fase 2 por si aparece más según se avance.

## Fase 0 — Reconstrucción del frontend (v3) — ✅ Hecha

Añadida el 2026-09-13, ejecutada el 2026-09-14. Historia corta y útil:
el plan original de esta fase era aplicar a v2.1 seis elementos
concretos tomados de una referencia de dashboard fintech que aportó el
usuario (fondo con tinte lavanda, chips de icono en círculo pastel, un
gauge/donut hero para el readiness, deltas con punto de color + flecha,
nav inferior en píldora negra, avatares circulares en fila). **Ese plan
queda derogado y no se retoma**, y merece la pena anotar por qué,
porque es el tercer ciclo del mismo error:

el usuario volvió a rechazar el resultado en los mismos términos con
los que había rechazado v1 y v2 - "hay aún mucho estilo con neón tipo
AI slop", "lo mismo con los emoticonos", "hay muchas palabras que se
cortan, no es un diseño de alto nivel" - y pidió explícitamente
**rehacer el frontend desde 0, "no solo el estilo y colores, TODO"**.
Aplicar una séptima capa de adorno visual encima (que es literalmente
lo que proponían los seis puntos: tintes, pastel, un donut, puntos de
color) habría reproducido la queja por cuarta vez. Cuatro de los seis
puntos eran decoración pura y hoy los prohíbe la doctrina 1 del
`05-design-system-v3.md` (*el color es información, nunca adorno*).

Lo que se hizo en su lugar:

1. ✅ **Doctrina escrita y numerada antes de tocar código**
   (`01-arquitectura/05-design-system-v3.md`), para poder citar cada
   regla por número desde los comentarios de los componentes y que una
   decisión de diseño sea discutible contra un documento en vez de
   contra el gusto de quien la escribió. `04-design-system-v2.md`
   marcado como derogado, no borrado.
2. ✅ **Tokens de rol y escala tipográfica con nombre**, en lugar de
   colores y tamaños elegidos caso por caso: se fue el neón, los
   degradados, los brillos y los bordes de color.
3. ✅ **Una pregunta por página.** "Hoy" pierde la tendencia de
   readiness (30 círculos sin eje, sin fechas y sin cifras, con el
   significado solo en el `title` del cursor: inexistente en móvil) y
   el objetivo nutricional, que allí era una tarjeta cuyo único
   contenido era un botón "calcular macros". Ambos por petición
   explícita del usuario.
4. ✅ **Página Perfil**, que no existía: datos propios, tema
   claro/oscuro/automático y el estado real de las conexiones a Garmin
   y Feelfit con su formulario de alta. Ocupa el hueco de nav que
   dejó "Coach", que gastaba un quinto de la navegación para decir
   "todavía no está construido".
5. ✅ **Cero texto cortado**, verificado por captura a 390px y 1280px
   en claro y oscuro: goteras en las cabeceras de tabla, tabla de
   sesiones de 4 columnas con la fecha bajo el nombre, etiquetas
   cortas propias en el nav móvil, desplegables del plan semanal a
   ancho real.
6. ✅ **Gráficas que no mienten**: el relleno de área con degradado se
   retiró (el eje del peso empieza en 75 kg, así que el área no
   representaba nada, y cerraba cada hueco de datos con una pared
   vertical falsa hasta la base), y con él el nombre del componente
   (`AreaTrendChart` → `TrendChart`). El donut y el gauge radial
   también se fueron.
7. ✅ **Sin jerga interna en pantalla**: el 502 de `/exercises` escribía
   "Fallo de conexión con wger: [Errno 111] Connection refused" tal
   cual en la pantalla de Entrenamiento, y el 404 de Feelfit "No existe
   UserProfile con id=5". Ahora el usuario lee texto escrito para una
   persona y el detalle técnico va al log del servidor, con test que lo
   fija.

**Lección para la próxima vez que aparezca una referencia visual**:
preguntar qué problema de lectura resuelve antes de copiar sus
elementos. Los seis puntos de esta fase venían de mirar una pantalla
bonita, no de mirar un dato que no se entendía - y los problemas reales
del frontend (una tendencia ilegible, cinco columnas en 390px, un
errno de sistema en pantalla) no estaban en esa lista.

## Fase 1 — Integración Ollama — ✅ Hecha y verificada contra un servidor real

Completada el 2026-09-13 (ver investigación #16 y Épica L de
`03-vision-produccion.md`):

1. ✅ Probado contra un servidor Ollama real ya instalado por el usuario
   (`llama3.2:latest` 3B, `qwen2.5:7b`) - narrativas coherentes en
   español, la barrera anti-alucinación numérica sigue rechazando cifras
   inventadas igual que con Gemini.
2. ✅ Latencia real medida: 1.3-6.5s por narrativa, aceptable dentro de
   la petición HTTP síncrona actual. `llama3.2:latest` recomendado como
   default (más ligero, más rápido, no mostró el hallazgo del punto 4).
3. ⬜ **Sigue pendiente, no bloqueante**: decidir si `docker-compose.yml`
   empaqueta su propio servicio `ollama` o se sigue asumiendo una
   instalación externa (lo verificado) - no bloquea nada más, la
   integración ya funciona contra cualquier `OLLAMA_HOST` accesible.
4. ✅ Fallback a plantilla determinista confirmado con servidor
   inaccesible, y hallazgo real corregido en el camino: `qwen2.5:7b` a
   veces mezclaba caracteres chinos no pedidos en una respuesta por lo
   demás correcta - nueva barrera de forma (`_PATRON_ALFABETO_NO_LATINO`
   en `narrative_service.py`) lo rechaza, cubierta con test de
   regresión.

## Fase 2 — Nutrición: decisión de producto pendiente antes de codificar

El diario de comidas NO se construye sobre wger (rechazado explícitamente
por el usuario, Épica 4 de `03-vision-produccion.md`). Antes de escribir
ningún modelo de datos nuevo, se necesita decidir con el usuario:

5. ¿Diario propio de Pulse con ingredientes vía Open Food Facts
   directamente (sin wger de por medio, solo su API pública de
   `ingredient`/`product` search, sin auth)? Es la alternativa más
   coherente con lo ya rechazado - reutiliza la misma fuente de datos de
   alimentos que ya se evaluó como buena (Open Food Facts), pero con
   modelo de datos y persistencia 100% de Pulse en vez de vía wger.
6. Si se confirma: modelo de datos (`Meal`/`MealItem`/`NutritionDiaryEntry`
   propios), motor de agregación diaria reutilizando `engine/nutrition.py`
   ya existente, y solo entonces recetas (lista de `MealItem` propios +
   instrucciones).
7. Exponer con más detalle en la UI la calculadora de calorías/macros que
   ya existe en `engine/nutrition.py` (hoy solo se ve el resultado final
   del día) - esto SÍ es ejecutable ya, sin esperar a la decisión de
   arriba, es trabajo de frontend puro sobre un motor que ya existe.

**Por qué no primero pese a ser una pieza grande de producto**: escribir
código sobre una arquitectura de datos no confirmada por el usuario
arriesga repetir el mismo ciclo de construir-y-revertir de la Épica 4.

## Fase 3 — Fotos de progreso (research ya cerrada, ejecutable ya)

Épica 9, investigación #3 de `03-vision-produccion.md` ya concluyente:
**nunca %grasa desde foto**, solo tendencia relativa de silueta (ratios
hombro/cintura/cadera) vía MediaPipe Pose Landmarker.

8. Captura de landmarks por foto (frontal/lateral/espalda, ya modelado en
   `ProgressPhoto.angulo`) - todo cliente (`"use client"`), assets WASM
   servidos desde `public/` propio, modelo cargado perezosamente.
9. Integrar como una señal más en `BodyGoalInsightCard`/insights de
   Cuerpo, nunca como número de %grasa.

**Por qué segundo**: no depende de ninguna decisión de producto
pendiente ni de investigación nueva - es la pieza de mayor impacto de
producto que se puede empezar hoy mismo sin bloqueos.

## Fase 4 — Motor de timing/ayuno intermitente (mayor riesgo, requiere investigación previa)

Épica 13. Bloqueada por Fase 2 (necesita datos reales de nutrición, no
solo el resultado agregado del motor) y por una sesión de investigación
científica dedicada (mismo patrón que
`00-research/06-periodizacion-ciencia-deportiva.md` y
`00-research/08-nutricion-recovery-ciencia.md`) sobre timing de
nutrientes/ayuno intermitente antes de fijar cualquier umbral.

## Fase 5 — Integraciones externas (necesitan research dedicada previa)

- **Épica 17 (intervals.icu)**: términos de uso, límites de rate, si
  requiere cuenta separada, si "Build Your Own Coach" es API pública o
  producto cerrado.
- **Épica 18 (`coach.md`)**: preferencias de coaching persistentes
  editables por el usuario, inyectadas en la plantilla de prompt de la
  Capa 3 - research menor (solo formato de archivo), barata de ejecutar.
- **Épica 19 (Telegram)**: bot vía `@BotFather` que empuja el resumen
  narrativo ya generado por la Capa 3 - sin chat conversacional nuevo
  (ya descartado como WON'T-HAVE-YET). Research menor, mayormente
  implementación directa.

De las tres, 18 y 19 son las más baratas y no dependen de negociar con un
tercero - candidatas a intercalarse en cualquier fase anterior si surge
tiempo libre entre piezas más grandes.

## Fase 6 — Baja prioridad / opcional

- **Épica 12 (HealthKit como fuente secundaria)**: solo iOS, resúmenes
  aproximados de MyFitnessPal sin desglose - prioridad baja explícita.
- **Épica 4 (sustituto del food log revertido)**: se resuelve de facto
  por la Fase 2 - no es una épica separada, márquese cerrada cuando la
  Fase 2 esté hecha.

## Cómo usar este documento

- Cada fase es secuencial por dependencia real o por criterio de
  priorización explicado arriba, no por orden numérico de la tabla de
  épicas.
- Dentro de una fase, las piezas listadas SÍ pueden paralelizarse si hay
  presupuesto de sesión para ello.
- Al completar cualquier punto: actualizar su fila en la tabla de épicas
  de `03-vision-produccion.md` (Estado + evidencia real de verificación),
  añadir entrada a `CHANGELOG.md`, y si introduce un hallazgo/decisión de
  diseño no obvio, documentarlo en la sección "Investigación ya
  realizada" del vision doc para que no se repita.
