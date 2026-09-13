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

## Fase 1 — Cerrar la integración Ollama (empezada esta sesión, falta la mitad)

1. **Probar contra un servidor Ollama real**: instalar Ollama localmente
   (`ollama pull llama3.1` o un modelo más pequeño si la máquina no da
   para 8B), configurar `OLLAMA_HOST=http://localhost:11434` y verificar
   con una petición real a `GET /users/{id}/garmin/activities/narrative`
   (o cualquier endpoint que use la Capa 3) que el texto generado es
   coherente y la barrera anti-alucinación numérica (`_es_texto_llm_coherente_contexto`)
   sigue rechazando cifras inventadas con un modelo distinto a Gemini.
2. **Medir latencia real** y decidir el modelo recomendado por defecto
   documentándolo en `03-vision-produccion.md` (punto 16) - un modelo de
   8B en CPU puede tardar varios segundos, puede hacer falta un modelo
   más pequeño (`llama3.2:3b`, `qwen2.5:3b`) para que la respuesta HTTP
   no se perciba lenta.
3. **Decidir si `docker-compose.yml` levanta su propio servicio `ollama`**
   (más pesado - modelo de varios GB - pero "un solo comando", coherente
   con la filosofía de `start.ps1`) o si se documenta como requisito
   externo opcional (más ligero, un paso manual). Actualizar
   `.env.example`/README según la decisión.
4. Confirmar que el fallback a plantilla determinista se sigue
   ejecutando correctamente si el servidor Ollama configurado no responde
   (ya cubierto por test con dobles - falta la confirmación real).

**Por qué primero**: es trabajo ya empezado, de alcance pequeño y
acotado, y dejar una integración a medias (código listo pero nunca
probado contra el servicio real) sería exactamente el tipo de progreso
no verificado que este proyecto se ha comprometido a no fingir.

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
