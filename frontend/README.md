# Frontend — Pulse

Dashboard visual (Next.js 16 / App Router / React 19 / TypeScript / Tailwind v4) construido sobre el **Design System v3** — `../01-arquitectura/05-design-system-v3.md` es la única fuente de verdad de diseño, y sus reglas están numeradas precisamente para poder citarlas por número desde los comentarios del código (v2 quedó derogado, se conserva como histórico).

Lo que eso significa en la práctica, si vas a tocar un componente:

1. **El color es información, nunca adorno.** No hay degradados, ni brillos, ni bordes de color decorativos. El estado activo se marca con contraste, no con acento.
2. **Un solo nivel de elevación.** Filetes de 1px, cero tarjetas dentro de tarjetas.
3. **Los datos tabulares van en una tabla** (`Table`/`Td`/`TdNum`), no en una rejilla de tarjetitas.
4. **Nada se corta ni se trunca.** Ni elipsis, ni palabras partidas, ni texto tapado por la flecha de un `<select>`. Si no cabe a 390px, se rediseña la columna o se acorta la etiqueta — no se recorta el dato.
5. **Toda gráfica lleva eje y unidad.** No hay mini-gráficas cuyo significado solo aparezca al pasar el cursor (en móvil no hay cursor).
6. **"Unknown is not zero".** La ausencia de dato se dibuja como ausencia (un filete discontinuo, un guion), nunca como un cero ni como una barra a cero.
7. **Los estados vacíos dicen qué HACER**, no "no hay datos".
8. **Español y fechas humanas** ("Hoy", "Ayer", "12 sep" — ver `lib/fechas.ts`), nunca ISO en pantalla ni jerga interna del proyecto.

Tokens de rol en `app/globals.css` (`--canvas --surface --line --line-strong --ink --ink-2 --ink-3 --action --action-ink` para superficie y texto; `--pos --warn --neg --data` para semántica) y escala tipográfica con nombre (`.t-page-title .t-hero .t-section .t-metric .t-body .t-secondary .t-micro .tabular`). Usa los tokens: no elijas un color ni un tamaño a mano en un componente nuevo. Ojo con `.t-micro`, que aplica `text-transform: uppercase` — no sirve para unidades.

## Setup y arranque local

```powershell
cd frontend
npm install
npm run dev -- --webpack
```

> **Nota Windows**: `next dev`/`next build` por defecto usan Turbopack, que requiere bindings nativos no disponibles en algunos entornos Windows (cae a WASM y falla con *"Turbopack is not supported on this platform"*). Usa siempre `--webpack` en ese caso (nota el `--` extra: sin él, npm interpretaría el flag como propio, no como argumento para `next dev`).

Necesita el backend corriendo en `http://localhost:8000` (ver `../backend/README.md`) y `PULSE_FRONTEND_ORIGIN=http://localhost:3000` en el backend para CORS.

## Estructura

Cinco páginas, y cada una responde a **una sola** pregunta:

| Ruta | Pregunta que responde |
| --- | --- |
| `src/app/page.tsx` | **Hoy** — cómo estoy hoy y qué hago hoy. Nada más. |
| `src/app/cuerpo/` | Cómo va mi cuerpo respecto a mi objetivo. |
| `src/app/entrenamiento/` | Qué he entrenado y cómo lo estoy tolerando (pestañas Sesiones / Plan / Recuperación / Análisis). |
| `src/app/nutricion/` | Qué tengo que comer. |
| `src/app/perfil/` | Mis ajustes: datos propios, apariencia y conexiones. |

`salud/` y `analisis/` siguen existiendo solo como `redirect()` a `entrenamiento/`, para no romper enlaces guardados.

- `src/components/` — un componente por tarjeta/formulario, cada uno con su test co-localizado: `RecoveryStatusCard`, `DailySessionCard`, `ActivitiesCard`, `SesionesEntrenamiento`, `WeeklyScheduleForm`, `ExercisePicker`, `ExerciseSetsDetail`, `HealthMetricsTodayCard`, `GarminHealthHistoryCard`, `IntradayMetricCard`, `ReadinessTrendCard`, `TrainingLoadCard`, `WeeklyVolumeChart`, `HabitJournalCard`, `PeriodicSummaryCard`, `NutritionTargetCard`, `NutritionPlanCard`, `WeightTrendCard`, `BodyCompositionTile`, `BodyGoalInsightCard`, `BodyMeasurementForm`, `CoachNarrativeBlock`, y los tres de Perfil: `ProfileCard`, `AppearanceCard`, `ConnectionsCard`.
- `src/components/ui/` — los primitivos. Construye con estos antes de escribir markup nuevo:
  - `Card`/`CardTitle` — el único contenedor. No se anidan.
  - `Table`/`Td`/`TdNum` — tabla real, con goteras y cifras alineadas a la derecha en `tabular`.
  - `DataList`/`DataRow` — pares etiqueta/valor cuando no son suficientes columnas para una tabla.
  - `StatTile`/`MetricGrid` — métrica suelta con su unidad, en rejilla.
  - `TrendChart` — serie temporal con eje X de tiempo real, eje Y con unidad y huecos dibujados como huecos (un dato aislado sale como punto, no como una línea inventada hasta el siguiente).
  - `SegmentedControl` (`role="tablist"`), `ChipFilter`, `Disclosure`, `PageHeader`, `Button`.
  - `FormField`/`fieldInputClass` (label+input+error consistente) y `CredentialsForm` (el formulario de email/contraseña compartido por Garmin y Feelfit — las contraseñas no se persisten nunca).
  - `MacroBar`, `AnimatedNumber`, `FadeIn`, `Skeleton`, `LoadingState`/`EmptyState`/`ErrorState`.
- `src/lib/` — `api.ts` (cliente tipado), `fechas.ts` (fechas como las diría una persona: `fechaRelativa`, `fechaCorta`, `diasDesdeHoy`, `plural`), `numeros.ts`, `useTheme.ts` (claro/oscuro/automático, persistido en `localStorage`), `motion-tokens.ts`, `dedupe.ts` (agregación "última fila del día gana" para históricos append-only), `fasesNutricion.ts`, `activityFormat.ts`, `useCurrentUser.ts`/`UserContext.tsx` (sesión mono-usuario vía `localStorage`, sin login real todavía).

## Librerías clave

- `motion` (framer-motion) para animación — springs físicos, nunca `hover:scale` de CSS suelto.
- `recharts` para gráficas. Solo líneas y barras con sus ejes: el relleno de área con degradado, el medidor radial y el donut se retiraron en v3 — el degradado además mentía sobre la magnitud (ninguna serie parte de cero) y cerraba cada hueco de datos con una pared vertical falsa hasta la base.
- `lucide-react` para iconos SVG (nunca emoji), y solo cuando el icono *identifica* algo — los destinos del nav, la categoría de un deporte. Un icono al lado de cada título es adorno, y el usuario lo señaló por su nombre.

## Tests

```powershell
npx vitest run
npx tsc --noEmit
npm run lint
```

`vitest.setup.mts` incluye polyfills de `ResizeObserver`/`getBoundingClientRect` para que los componentes de `recharts` rendericen en jsdom.

## Build de producción

```powershell
npx next build --webpack
```
