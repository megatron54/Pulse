# Frontend — Pulse

Dashboard visual (Next.js 16 / App Router / React 19 / TypeScript / Tailwind v4), tema único Apple-clean (fuente de sistema, claro/oscuro real vía `prefers-color-scheme`) con patrones de layout/interacción inspirados en Garmin Connect, Strava y MyFitnessPal — ver `../01-arquitectura/04-design-system-v2.md` para la fuente de verdad de diseño.

## Setup y arranque local

```powershell
cd frontend
npm install
npm run dev -- --webpack
```

> **Nota Windows**: `next dev`/`next build` por defecto usan Turbopack, que requiere bindings nativos no disponibles en algunos entornos Windows (cae a WASM y falla con *"Turbopack is not supported on this platform"*). Usa siempre `--webpack` en ese caso (nota el `--` extra: sin él, npm interpretaría el flag como propio, no como argumento para `next dev`).

Necesita el backend corriendo en `http://localhost:8000` (ver `../backend/README.md`) y `PULSE_FRONTEND_ORIGIN=http://localhost:3000` en el backend para CORS.

## Estructura

- `src/app/` — páginas (App Router): `page.tsx` (Hoy), `entrenamiento/`, `salud/` (Recuperación), `analisis/`, `nutricion/`, `cuerpo/`, `coach/`.
- `src/components/` — un componente por tarjeta/formulario (`RecoveryStatusCard`, `DailySessionCard`, `GarminActivitiesCard`, `SesionesEntrenamiento`, `WeeklyScheduleForm`, `ExercisePicker`, `HealthMetricsSummaryRow`, `GarminHealthHistoryCard`, `IntradayMetricCard`, `HabitJournalCard`, `PeriodicSummaryCard`, `NutritionTargetCard`, `NutritionPlanCard`, `WeightTrendCard`, `BodyCompositionTile`, `BodyMeasurementForm`...), cada uno con su test co-localizado.
- `src/components/ui/` — kit de UI compartido: `StatTile` (métrica compacta en rail horizontal), `SegmentedControl`/`ChipFilter` (selección agrupada/filtros, `role="tablist"`), `ActivityListItem` (fila de feed estilo Strava), `MacroBar` (barra de proporción de macros estilo MyFitnessPal), `FormField`/`fieldInputClass` (label+input+error consistente), `Disclosure` (sección plegable), `PageHeader` (cabecera título+subtítulo+acciones), además de `Button`, `Card`, `DonutChart`, `RadialGauge`, `AreaTrendChart`, `Sparkline`, `AnimatedNumber`, `Skeleton`, `LoadingState`/`EmptyState`/`ErrorState`.
- `src/lib/` — `api.ts` (cliente tipado), `theme.ts` (paleta centralizada), `motion-tokens.ts` (sistema de tokens de animación), `dedupe.ts` (agregación "última fila del día gana" para históricos append-only), `activityFormat.ts`/`activityIcons.ts`, `useCurrentUser.ts`/`UserContext.tsx` (sesión mono-usuario vía `localStorage`, sin login real todavía).

## Librerías clave

- `motion` (framer-motion) para animación — springs físicos, nunca `hover:scale` de CSS suelto.
- `recharts`/SVG propio para gráficas (área con degradado, medidor radial, donut).
- `lucide-react` para iconos SVG (nunca emoji).

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
