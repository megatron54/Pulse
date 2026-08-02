# Arquitectura del coach conversacional con IA

## Hallazgo central

Todos los proyectos serios estudiados separan estrictamente **decisión (código determinista)** de **explicación (LLM)**. El ejemplo más claro es [drplatforms/health-fitness-platform](https://github.com/drplatforms/health-fitness-platform) (antes llamado literalmente "AI Health Coach"), que evolucionó deliberadamente **lejos** de la IA al madurar. Cita textual de su README:

> "the backend owns truth. Calculations, validation, persistence, historical state, and decision logic remain explicit and inspectable. AI/provider integrations may assist with selected workflows or experimentation, but the core product does not depend on a model to function and does not hand authoritative health decisions to one."

## Ejemplo didáctico: "AI Marathon Coach" (Caskey Coding)

Blog: https://caskeycoding.com/blog/building-an-ai-marathon-coach-deterministic-rules-llm-narratives-2026-nyc-marathon

Arquitectura de dos capas:
1. **Rules engine determinista**: calcula ACWR, volumen, fatiga desde datos Garmin. Evalúa 14 guardrails codificados a mano → salida tipada cerrada: `PROCEED | REDUCE_INTENSITY | REDUCE_VOLUME | CROSS_TRAIN_OR_REST | FULL_REST | RECOVERY_RUN | NEEDS_MORE_DATA`.
2. **LLM narrative engine**: recibe la salida tipada y **solo redacta** 2-4 frases explicativas. Nunca elige el tipo de recomendación.

Cita clave: *"Language models are not deterministic... Deterministic code has none of these problems. You can test it. You can audit it."*

Riesgo residual honesto: *"The failure I watch for is a guardrail I wrote badly, delivered in fluent, convincing prose."* — el riesgo se traslada de "¿alucinó el modelo?" a "¿escribí bien la regla?", mucho más auditable.

## Patrones de memoria/contexto

- **Corto plazo**: estado de la conversación activa (checkpointer, ej. `MemorySaver` de LangGraph).
- **Largo plazo**: perfil de usuario estructurado (objetivos, lesiones, preferencias) en un Store persistente, recuperado bajo demanda — nunca inyectar todo el historial en el prompt.
- **Resúmenes periódicos (batch, no en el hot path)**: digest semanal/mensual del estado del usuario (tendencia de volumen, adherencia, cambios de objetivo).
- **RAG vectorial solo para lo cualitativo** (notas libres, contexto conversacional) — nunca para datos numéricos estructurados.

Patrón de prompt recomendado:
```
system prompt (rol + reglas)
+ user_profile_summary (JSON corto, generado periódicamente)
+ datos deterministas del día/semana (calculados, no generados por el LLM)
+ top-k recuerdos relevantes (RAG, opcional)
+ últimos N turnos de conversación
```

## Frameworks de orquestación

| Framework | Recomendación |
|---|---|
| **LangGraph** | ✅ Elegido — grafo de estados explícito, memoria corto/largo plazo nativa (Store + checkpointer), permite forzar que la lógica determinista sea un nodo del grafo |
| CrewAI | Descartado como núcleo — da demasiada libertad al LLM para un coach con guardrails estrictos |
| AutoGen | Descartado — overhead innecesario para un solo usuario |
| Function calling simple | Alternativa válida si el alcance del MVP es pequeño |

## Guardrails contra alucinaciones

1. El LLM nunca es fuente de verdad numérica — todos los cálculos vienen ya resueltos del motor determinista.
2. Guardrails con salida tipada (enum cerrado), nunca texto libre.
3. **"Unknown is not zero"**: si falta un dato crítico, se devuelve `NEEDS_MORE_DATA` explícito, nunca se extrapola.
4. Reglas duras no anulables (ej. dolor → descanso total, sin excepción del LLM ni del usuario).
5. Auditoría completa: cada recomendación guarda inputs, guardrails disparados, prompt y respuesta.
6. Validación post-generación: el texto del LLM se valida contra los datos estructurados antes de mostrarse (no debe contradecir el número calculado).
7. **IA opcional y no autoritativa**: el producto debe funcionar sin LLM.

## Coste y modelo económico

- `zen-apps/ai-fitness-planner` usa GPT-4o-mini/o3-mini explícitamente por coste — no top-tier para tareas rutinarias.
- `drplatforms` soporta Ollama (modelo local) junto a OpenAI — permite correr sin coste de API.
- Como el LLM solo redacta y conversa (nunca calcula), el prompt es corto → modelos baratos/pequeños son suficientes. El 90% del tráfico no necesita un modelo grande.

## Arquitectura de 3 capas para Pulse

```
CAPA 3 — Conversacional (LLM barato/pequeño o local vía Ollama)
  Responsabilidad única: explicar, motivar, responder preguntas abiertas.
  Nunca calcula números ni decide progresión/dieta.
  Validador post-output antes de mostrar al usuario.

CAPA 2 — Datos y memoria
  DB relacional (historial inmutable, append-only): entrenamientos, sets,
  food logs, check-ins de recuperación, lesiones.
  Perfil de usuario estructurado + resumen periódico (batch).
  RAG vectorial solo para contenido cualitativo libre.

CAPA 1 — Motor de reglas determinista
  Macros/TDEE, progresión de carga, ACWR, periodización (ver doc 06).
  Guardrails duros con salida ENUM cerrada.
  100% testeable con unit tests. Funciona SIN LLM.
  Registro de auditoría de cada ejecución.
```

## Principios rectores (para el código de esta app)

1. El backend es dueño de la verdad — ninguna decisión de salud sale del LLM sin pasar por la capa 1.
2. Lo desconocido no es cero.
3. La IA es opcional y no autoritativa.
4. Si no se puede auditar, no se puede confiar.
5. Coste bajo por diseño — LLM solo para explicar/conversar.

## Fuentes
- https://github.com/zen-apps/ai-fitness-planner
- https://github.com/drplatforms/health-fitness-platform
- https://caskeycoding.com/blog/building-an-ai-marathon-coach-deterministic-rules-llm-narratives-2026-nyc-marathon
- https://docs.langchain.com/oss/python/langgraph/add-memory
- https://docs.langchain.com/oss/python/langchain/long-term-memory
