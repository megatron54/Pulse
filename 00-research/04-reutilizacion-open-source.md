# Reutilización de proyectos open source

## 1. Backend/tracker base

| Proyecto | Stack | Veredicto |
|---|---|---|
| **[wger](https://github.com/wger-project/wger)** | Django + DRF, apps Flutter oficiales | **Elegido como columna vertebral.** AGPL-3.0, Docker-first, 6.5k★, muy activo. Ya trae: rutinas con progresión automática, BD de ejercicios en español (CC-BY-SA), fotos de progreso, nutrición vía Open Food Facts, API REST completa |
| FitTrackee | Flask+Vue, PostgreSQL/PostGIS | Solo cardio/GPX, no cubre fuerza ni nutrición — descartado como base, revisar solo si se quiere mapas OSM |
| SparkyFitness | "AI-native" self-hosted | Revisar como referencia de arquitectura IA, menos maduro que wger |

## 2. Bases de datos de ejercicios

- **wger exercise database** (integrada, CC-BY-SA 4.0): ~845 ejercicios, imágenes+vídeos, 30 idiomas incluido español.
- **[free-exercise-db](https://github.com/yuhonas/free-exercise-db)** (clonado en `recursos/repos/`): 800+ ejercicios, Unlicense (dominio público), JSON plano listo para seed data — complemento sin restricciones de licencia.

## 3. Bases de datos de nutrición

| Fuente | Cobertura | Licencia | Para España |
|---|---|---|---|
| USDA FoodData Central | ~420k entradas, EEUU-céntrica | CC0 | Débil — poca cocina española/mediterránea |
| **Open Food Facts** | 359k productos solo España, ~4M globales | ODbL | **Elegida** — Mercadona, marcas reales, Nutri-Score/Eco-Score, ya integrada en wger |

## 4. Framework multiplataforma

**Flutter** elegido sobre React Native/Tauri/Electron por:
1. wger ya tiene su app oficial en Flutter, open source, publicada (Android/iOS/F-Droid/Flathub) — forkeable como punto de partida.
2. Una sola base de código para 6 plataformas (iOS/Android/Win/Mac/Linux/Web).
3. Mejor control de renderizado para gráficas de progreso (peso, fuerza, macros).

## 5. Proyectos "AI coach" de referencia (no para clonar completos, sí para estudiar patrones)

| Proyecto | Relevancia |
|---|---|
| [H1an1/health-coach](https://github.com/H1an1/health-coach) | Skill de IA con prompts/lógica de coaching ya redactados — reutilizar como base de conocimiento del agente |
| [Nutritheous](https://github.com/vishnugt/nutritheous) | Foto de comida → análisis nutricional con GPT-4 Vision, Spring Boot+Flutter+Postgres — patrón directo a imitar para "foto de comida" |
| [zen-apps/ai-fitness-planner](https://github.com/zen-apps/ai-fitness-planner) | Arquitectura multi-agente LangGraph con USDA — referencia de orquestación |
| [drplatforms/health-fitness-platform](https://github.com/drplatforms/health-fitness-platform) | Filosofía "backend owns truth, AI is optional" — referencia arquitectónica clave (ver `07-arquitectura-coach-ia.md`) |

## 6. Librerías de cálculo

- `tdee-calculator-library` (npm, TS, MIT) — TDEE/macros, cero dependencias.
- Fórmulas 1RM (Epley, Brzycki): copiar directo, no requieren librería.
- **Periodización**: no existe librería open source madura — hueco real, hay que construirlo (ver `06-periodizacion-ciencia-deportiva.md`).

## 7. Wearables además de Garmin

- Apple HealthKit: `react-native-health` (si se usa RN) o paquete equivalente Flutter (`health` en pub.dev).
- Android Health Connect: `react-native-health-connect` o `health` (Flutter).
- Multi-wearable unificado: [the-momentum/open-wearables](https://github.com/the-momentum/open-wearables) como referencia de esquema de datos normalizado.

## Lista priorizada final

### ✅ Reutilizar directamente
1. wger como backend (Docker) + su BD de ejercicios/nutrición.
2. App Flutter oficial de wger como base de UI a forkear.
3. free-exercise-db como complemento de ejercicios.
4. Open Food Facts (ya integrado en wger).
5. `python-garminconnect` para sync.
6. `tdee-calculator-library` para cálculos base.
7. Patrones de Nutritheous (foto de comida) y health-coach (prompts) como plantillas.

### 🔨 Construir a medida
1. Motor de periodización multi-objetivo (fuerza+hipertrofia+resistencia+artes marciales+cortes).
2. Capa de orquestación del coach IA (3 capas, ver doc 07).
3. UI conversacional del coach (wger es tracker, no chat).
4. Integración unificada de wearables con capa de inteligencia.
5. Reglas España-específicas (Nutri-Score, alimentos locales no cubiertos).
