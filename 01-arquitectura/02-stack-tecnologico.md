# Stack tecnológico propuesto

| Capa | Elección | Alternativa considerada | Por qué |
|---|---|---|---|
| Cliente móvil+escritorio | **Flutter** | React Native+Expo, Tauri | wger ya tiene app Flutter oficial forkeable; una sola base para 6 plataformas; mejor control de gráficas |
| Backend API | **Python + FastAPI** | Node/NestJS | Ecosistema Python domina ML/IA (MediaPipe, LangGraph, pandas); wger es Django (mismo lenguaje) |
| Tracker base | **wger (Django, self-hosted, Docker)** | Construir tracker desde cero | Ahorra 60-70% del trabajo de tracking/BD de ejercicios/nutrición |
| Base de datos | **PostgreSQL** | SQLite | wger ya usa Postgres en producción; mejor para series temporales de wearables |
| Sync Garmin | **python-garminconnect** (cron diario) | API oficial Health API (partner) | Uso personal, sin necesidad de aprobación comercial |
| Análisis corporal foto | **MediaPipe Pose** (on-device) + fórmula Navy | SMPL-X, modelos propietarios | Licencia libre, gratis, sin dependencia de dataset DEXA propio |
| Análisis foto de comida | **LLM Vision** (GPT-4V/Gemini Vision) | Modelo propio de clasificación de alimentos | Patrón validado (Nutritheous), sin necesidad de entrenar modelo propio |
| Orquestación IA | **LangGraph** | CrewAI, AutoGen | Control fino de flujo, memoria nativa (Store+checkpointer), fuerza que la capa determinista sea un nodo del grafo |
| LLM conversacional | **GPT-4o-mini** (o Ollama local para $0) | Modelo grande siempre | Prompts cortos por diseño (capa 3 solo explica) — no necesita modelo caro |
| Nutrición | **Open Food Facts API** (+ USDA FDC fallback) | Solo USDA | OFF cubre productos españoles reales, Nutri-Score |
| BD de ejercicios | **wger DB + free-exercise-db** | ExerciseDB comercial | Gratis, licencias permisivas, ya en español |
| Contenerización | **Docker Compose** | — | wger ya lo soporta; facilita self-hosting |

## Notas de decisión pendientes de confirmar contigo

1. **¿Local LLM (Ollama, $0) o API cloud (GPT-4o-mini, ~$1-3/mes de uso personal)?** Recomendación: empezar con API cloud por calidad de respuesta, migrar a local si se quiere $0 coste y hay GPU disponible.
2. **¿Self-hosted en tu propio hardware (NAS/PC) o en un VPS barato?** Afecta a disponibilidad del cron de Garmin y de la API del coach cuando el móvil no está en la misma red.
3. **¿Forkear literalmente la app Flutter de wger, o construir una nueva UI desde cero usando wger solo como backend?** Recomendación: forkear para el MVP, iterar la UI progresivamente hacia el diseño de "coach conversacional".
