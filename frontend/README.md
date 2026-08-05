# Frontend — Pulse

Dashboard visual (Next.js 16 / App Router / React 19 / TypeScript / Tailwind v4) estilo WHOOP/Apple Health/Samsung Health: gráficas reales, no listados de texto.

## Setup y arranque local

```powershell
cd frontend
npm install
npm run dev -- --webpack
```

> **Nota Windows**: `next dev`/`next build` por defecto usan Turbopack, que requiere bindings nativos no disponibles en algunos entornos Windows (cae a WASM y falla con *"Turbopack is not supported on this platform"*). Usa siempre `--webpack` en ese caso (nota el `--` extra: sin él, npm interpretaría el flag como propio, no como argumento para `next dev`).

Necesita el backend corriendo en `http://localhost:8000` (ver `../backend/README.md`) y `PULSE_FRONTEND_ORIGIN=http://localhost:3000` en el backend para CORS.

## Estructura

- `src/app/` — páginas (App Router): `page.tsx` (Hoy, dashboard principal), `entrenamiento/`, `nutricion/`, `cuerpo/`, `garmin/`.
- `src/components/` — un componente por tarjeta/formulario (`ReadinessCheckinForm`, `TrainingLoadCard`, `NutritionTargetCard`, `HabitJournalCard`, `PeriodicSummaryCard`, `GarminActivitiesCard`...).
- `src/components/ui/` — primitivas compartidas: `Button` (foco visible WCAG 2.4.7, feedback con springs físicos), `LoadingState`/`EmptyState`/`ErrorState` (con reintento), `Skeleton` (shimmer, no `animate-pulse` genérico), `AnimatedNumber` (contador imperativo), `AreaTrendChart`/`RadialGauge`/`DonutChart` (wrappers de `recharts`), `Card`, `FadeIn`.
- `src/lib/` — `api.ts` (cliente tipado), `theme.ts` (paleta centralizada), `motion-tokens.ts` (sistema de tokens de animación: duración/easing/springs), `useCurrentUser.ts`/`UserContext.tsx` (sesión mono-usuario vía `localStorage`, sin login real todavía).

## Librerías clave

- `motion` (framer-motion) para animación — springs físicos, nunca `hover:scale` de CSS suelto.
- `recharts` para gráficas (área con degradado, medidor radial, donut).
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
