# Resumen ejecutivo de la investigación

## Objetivo del proyecto

Construir una app personal (móvil + escritorio) que actúe como entrenador y nutricionista, capaz de:
- Ingerir datos de un reloj Garmin (HRV, sueño, Body Battery, Training Readiness, actividades).
- Analizar fotos de progreso y medidas corporales (peso, altura, % graso).
- Entender y balancear múltiples objetivos simultáneos: fuerza, hipertrofia, running, natación, artes marciales, estética, cortes de peso, ganancia de masa, rendimiento general.
- Generar y adaptar planes de entrenamiento y nutrición de forma continua.

## Los 5 hallazgos más importantes

### 1. Hay un hueco de mercado real
Existen apps serias (IAM Coach, Level, TrainAsONE, Tredict) pero todas son "endurance-first" o "gym-first" — ninguna cubre bien fuerza + resistencia + artes marciales + estética a la vez con calidad real. Un proyecto personal a medida tiene sentido porque nadie ha resuelto exactamente este combo.

### 2. Garmin: viable para uso personal, con matices
La librería no oficial `python-garminconnect` es el estándar de facto de la comunidad hobbyist (miles de usuarios, sin bans documentados por uso personal). El riesgo real es técnico (bloqueos temporales), no legal/disciplinario. Ver detalle en `03-garmin-integracion.md`.

### 3. No hay que construir todo desde cero
**wger** (Django, open source, self-hosted) ya resuelve tracking de entrenamientos, base de datos de ejercicios en español, fotos de progreso y nutrición (vía Open Food Facts). Tiene app oficial en Flutter que se puede forkear. Esto cubre un 60-70% del trabajo de "tracker" típico. Ver `04-reutilizacion-open-source.md`.

### 4. El análisis corporal por foto debe ser honesto, no mágico
Los mejores modelos publicados (Nature/npj 2022, N=134) logran ~2% de error frente a DEXA, pero **solo en laboratorio controlado** y con modelos propietarios no disponibles. Para una app personal: MediaPipe Pose (gratis, on-device) + fórmula Navy calibrada, mostrando siempre un **rango**, nunca un número falso-preciso. Ver `05-analisis-corporal-foto.md`.

### 5. El coach de IA no debe "decidir" nada crítico
El patrón universal en todos los proyectos serios estudiados (incluyendo uno que se llamaba literalmente "AI Health Coach" y evolucionó lejos de la IA al madurar): **un motor de reglas determinista decide** (macros, progresión, seguridad); **el LLM solo redacta la explicación** en lenguaje natural. Esto permite modelos baratos/pequeños y evita alucinaciones peligrosas. Ver `07-arquitectura-coach-ia.md`.

## Ciencia aplicable a la periodización multi-objetivo

- El "interference effect" (fuerza vs. resistencia) es real pero manejable con buen diseño de volumen/secuencia — no es un impedimento serio.
- Modelo recomendado: **periodización conjugada-ondulante**, con bloques de 4-6 semanas donde un objetivo es prioritario y el resto están en modo mantenimiento (nunca maximizar todo a la vez).
- HRV/Body Battery/Training Readiness de Garmin tienen respaldo científico real como inputs de autorregulación diaria (usando tendencia de 3-7 días, no el valor de un solo día).
- Cortes de peso: 0.5-0.7% del peso corporal/semana preserva mucha más masa muscular que el clásico "1kg/semana" en atletas que combinan fuerza + resistencia.

Detalle completo con pseudocódigo del motor de reglas en `06-periodizacion-ciencia-deportiva.md`.

## Arquitectura recomendada (vista de alto nivel)

```
Capa 3 — Conversacional (LLM barato/pequeño, solo explica y conversa)
Capa 2 — Datos y memoria (perfil de usuario, historial inmutable, resúmenes periódicos)
Capa 1 — Motor de reglas determinista (macros, progresión, ACWR, guardrails de seguridad)
```

Detalle completo en `01-arquitectura/01-arquitectura-general.md`.

## Qué falta decidir contigo antes de construir

1. Confirmar alcance: ¿solo para ti, o contemplar multiusuario en el futuro?
2. Confirmar stack: propuesta es Flutter (móvil+escritorio) + backend Python (FastAPI, sobre/al lado de wger) + LLM vía API o local.
3. Prioridad de las primeras funcionalidades (¿empezamos por sync Garmin + tracking básico, o por el motor de periodización?).
