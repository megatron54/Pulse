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
| LLM conversacional | **Google Gemini API (free tier)** | GPT-4o-mini, Ollama local | Coste $0 en el tier gratuito; suficiente porque la Capa 3 solo explica/conversa (prompts cortos, no calcula nada) |
| Nutrición | **Open Food Facts API** (+ USDA FDC fallback) | Solo USDA | OFF cubre productos españoles reales, Nutri-Score |
| BD de ejercicios | **wger DB + free-exercise-db** | ExerciseDB comercial | Gratis, licencias permisivas, ya en español |
| Contenerización | **Docker Compose** | — | wger ya lo soporta; facilita self-hosting |

## Notas de decisión pendientes de confirmar contigo

1. ~~¿Local LLM o API cloud?~~ **Resuelto: Google Gemini API (free tier)** — coste $0, calidad suficiente para explicar decisiones ya calculadas por la Capa 1.
2. **Hosting: 100% local por ahora.** Todo corre en local (Docker Desktop + Postgres propio). Si en el futuro se decide exponer esto online, la opción evaluada es **Vercel (frontend/API) + Supabase (Postgres gestionado + auth + storage)** — encaja bien porque Supabase es Postgres real (mismo motor que usamos ya en local) y Vercel tiene tier gratuito generoso. Migración futura, no ahora.
3. **¿Forkear literalmente la app Flutter de wger, o construir una nueva UI desde cero usando wger solo como backend?** Recomendación: forkear para el MVP, iterar la UI progresivamente hacia el diseño de "coach conversacional".
