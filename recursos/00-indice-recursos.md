# Índice de recursos

## Repos clonados localmente (`recursos/repos/`)

| Carpeta | Repo original | Uso previsto |
|---|---|---|
| `python-garminconnect/` | https://github.com/cyberjunky/python-garminconnect | Sincronización de datos Garmin (Fase 0) |
| `free-exercise-db/` | https://github.com/yuhonas/free-exercise-db | Complemento de BD de ejercicios (Fase 0) |
| `python-fitparse/` | https://github.com/dtcooper/python-fitparse | Parseo offline de .FIT como fallback (Fase 0) |

## Repos de referencia (no clonados, consultar online cuando toque)

| Repo | Para qué fase |
|---|---|
| https://github.com/wger-project/wger | Fase 0 — backend base (desplegar con Docker, no clonar código a modificar) |
| https://github.com/wger-project/flutter (app oficial) | Fase 3 — fork de la app cliente |
| https://github.com/arpanghosh8453/garmin-grafana | Referencia arquitectura sync Garmin |
| https://github.com/tcgoetz/GarminDB | Referencia arquitectura sync Garmin (alternativa simple) |
| https://github.com/the-momentum/open-wearables | Referencia esquema multi-wearable |
| https://github.com/vishnugt/nutritheous | Fase 5 — patrón foto de comida → macros con LLM Vision |
| https://github.com/H1an1/health-coach | Fase 4 — prompts/lógica de coaching a adaptar |
| https://github.com/zen-apps/ai-fitness-planner | Fase 4 — referencia orquestación LangGraph multi-agente |
| https://github.com/drplatforms/health-fitness-platform | Fase 1 y 4 — filosofía "backend owns truth" |
| https://huggingface.co/ChanMeng666/bodyfat-estimation-mlp | Fase 2 — modelo de regresión %grasa sobre medidas |
| https://github.com/frankbigshuai/BodyFatEstimator | Fase 2 — referencia alternativa (ResNet-50+U2Net) |

## Papers científicos citados (ver `06-periodizacion-ciencia-deportiva.md` y `05-analisis-corporal-foto.md` para contexto completo)

- Majmudar et al. 2022, npj Digital Medicine — https://www.nature.com/articles/s41746-022-00628-3
- Estudio brasileño 2025 (AI-2D-foto vs DEXA) — https://pmc.ncbi.nlm.nih.gov/articles/PMC11743147/
- Wilson et al. 2012 — https://pubmed.ncbi.nlm.nih.gov/22002517/
- Lundberg et al. 2022 — https://pubmed.ncbi.nlm.nih.gov/35476184/
- Held et al. 2026 — https://pubmed.ncbi.nlm.nih.gov/41762427/
- Garthe et al. 2011 — https://pubmed.ncbi.nlm.nih.gov/21558571/
- Campbell et al. 2020 — https://pubmed.ncbi.nlm.nih.gov/33467235/
- Di, Hongye & Donglin 2025 — https://pmc.ncbi.nlm.nih.gov/articles/PMC12859854/

## Bases de datos / APIs a usar en producción (no descargables como repo, son servicios)

- Open Food Facts API — https://world.openfoodfacts.org/data (España: ~359k productos)
- USDA FoodData Central API — https://fdc.nal.usda.gov/api-guide (fallback para whole-foods)
- MediaPipe Pose (Google) — https://developers.google.com/mediapipe (librería, se instala vía pip/pub.dev, no repo a clonar)

## Pendiente de descargar cuando se necesite (no urgente ahora)

- Dump completo de Open Food Facts España (si se quiere caché local en vez de API en vivo).
- Pesos del modelo `frankbigshuai/BodyFatEstimator` si se decide usarlo en vez de solo Navy+MediaPipe.
- App Flutter oficial de wger (clonar en Fase 3, no antes, para evitar desactualización).
