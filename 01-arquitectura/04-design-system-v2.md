# Design System v2 — única fuente de verdad (Fase 0 de la reconstrucción del frontend)

> **Este documento sustituye a cualquier decisión de diseño previa.** El
> rediseño WHOOP (`02-roadmap/03-vision-produccion.md`) y el rediseño
> Apple posterior quedan **derogados** — no se sigue ninguna skill de
> diseño externa (`apple-design`, `emil-design-eng`, etc.) como
> autoridad; se usan solo como caja de herramientas de referencia
> puntual. Motivo: capas de rediseño incrementales sin una única
> dirección produjeron una app percibida por el usuario real como
> "cajas sueltas sin cohesión" (queja explícita, ver conversación que
> originó esta reconstrucción).
>
> Decisión del usuario: **tema único Apple-clean** (no dark deportivo
> tipo WHOOP/Garmin/Strava).

## Principios (en orden de prioridad, si compiten unos con otros gana el de arriba)

1. **Nunca inventar datos.** "Unknown is not zero": si un dato no ha
   llegado aún de Garmin, se muestra como ausente explícito ("Aún sin
   datos de hoy — última sync: hace 12 min"), nunca un 0/vacío
   silencioso ni un valor placeholder que parezca real.
2. **Cero formularios de datos que Garmin ya provee.** El check-in
   manual de recovery queda eliminado por completo (incluido el
   toggle de dolor articular — decisión explícita del usuario:
   eliminar, no mantener ni siquiera un micro-control).
3. **Jerarquía visual real, no "grid bento".** Cada vista tiene un
   elemento hero claro y 2-3 niveles de importancia decreciente. Nunca
   N tarjetas del mismo tamaño flotando en el mismo nivel visual.
4. **Sin scroll forzado en desktop** para las vistas principales (Hoy).
   Las vistas de listas/histórico (Sesiones, Análisis) sí pueden
   necesitar scroll — eso es correcto, lo que no es correcto es que una
   vista de "resumen de hoy" obligue a desplazarse para ver contenido
   que cabría con mejor jerarquía.
5. **Responsive real, verificado por redimensionado, no solo por
   breakpoint teórico.** Ninguna vista puede cortar contenido entre
   320px y 4K. Esto se verifica manualmente (Playwright/redimensionado
   real), no se asume.

## Tema visual: Apple-clean

- **Fuente:** pila de sistema (`-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, ...`).
  Sin fuentes de Google Fonts para texto/headings (solo monoespaciada
  si hace falta para código/cifras tabulares).
- **Superficies:** sin degradados de marca ni translucidez decorativa
  "porque sí". Fondo neutro (blanco en claro / gris muy oscuro neutro
  en oscuro), tarjetas con **un solo nivel de separación** (borde sutil
  O sombra suave, no ambos a la vez a menos que la jerarquía lo pida).
- **Color:** paleta de sistema de Apple para semántica (verde/amarillo/
  rojo de recovery, azul de acción primaria), usada con moderación —
  el color comunica estado, no decora.
- **Modo claro/oscuro:** a diferencia de la iteración anterior
  (dark-only forzado), Apple-clean soporta ambos modos, siguiendo
  `prefers-color-scheme` del sistema operativo. Esto es un cambio de
  comportamiento respecto a versiones anteriores — antes la app era
  dark-first sin más.
- **Motion:** springs físicos sutiles ya existentes en
  `lib/motion-tokens.ts` se conservan y auditan, no se reescriben desde
  cero (son independientes del tema visual).

## Tokens (a implementar en Fase 1)

Pendiente de valores exactos en la implementación de Fase 1, pero con
estas reglas:

- Espaciado y tipografía en `rem`/`em`, nunca `px` fijos que rompan con
  el zoom/Dynamic Type del usuario.
- Contenedor de contenido: ancho fluido con `max-width` generoso
  (no un `max-w-6xl mx-auto` que dejé "cajas flotando" en el centro de
  pantallas anchas) — el contenido debe ocupar el espacio disponible
  con proporciones pensadas, no quedar como una isla centrada.
- Breakpoints: móvil (<768px, tab bar inferior), tablet/desktop
  (≥768px, sidebar), desktop ancho (≥1280px, layouts de 2-3 columnas
  donde la jerarquía lo permita).

## Arquitectura de información (aprobada por el usuario)

```
Hoy            — dashboard compuesto, jerarquía de 3 niveles, sin scroll forzado
Entrenamiento  — Sesiones (actividades Garmin reales, filtro por categoría) + Plan (bloque activo, calendario)
Recuperación   — HRV, sueño, body battery, estrés — 100% automático de Garmin
Análisis       — tendencias históricas (HRV, sueño, carga, peso, volumen)
Coach          — chat conversacional con IA (placeholder honesto, Fase 6 pendiente)
Nutrición      — objetivo de macros del día (hero) + plan de fase
Cuerpo         — tendencia de peso (hero) + composición Feelfit + medida manual
```

Se eliminan como páginas de primer nivel: `/running`, `/ciclismo`,
`/gimnasio` (pasan a ser un filtro `categoria=` dentro de
Entrenamiento → Sesiones) y `/garmin` (sus datos se reparten entre
Hoy/Recuperación/Análisis; el emparejamiento de cuenta pasa a Ajustes).

## Composición y layout (v2.1)

Tras cerrar la Fase 1-5 originales, feedback directo del usuario aclaró
que el problema visual real nunca fue la paleta ni el tema (el
Apple-clean de la sección anterior sigue vigente sin cambios), sino la
**composición**: ubicación de cajas, tamaños, jerarquía y formularios
pobres. El objetivo pasó a ser explícitamente un híbrido de UX/layout
con **Garmin Connect, Strava y MyFitnessPal** — esto es una referencia
de **patrones de interacción y organización de contenido** (rails de
métricas, feed de actividades, diario de macros con barras), **no** una
petición de volver a un tema oscuro de marca deportiva. Ambas cosas se
confundieron una vez en esta misma conversación; queda anotado aquí
para no repetir el error.

Primitivos de UI nuevos en `components/ui/`, reutilizados en todas las
páginas en vez de markup ad-hoc repetido por componente:

- **`StatTile`** — tile compacto icono+etiqueta+valor animado, en un
  rail horizontal con scroll en móvil (`.scroll-rail`, sin scrollbar
  visible) y en grid en desktop. Sustituye a las tarjetas apiladas a
  ancho completo por cada métrica suelta (HRV, Body Battery, sueño...).
- **`SegmentedControl<T extends string>`** — control agrupado
  (`role="tablist"`/`aria-selected`) para elegir una única opción entre
  pocas (rango temporal, pestaña Sesiones/Plan). Sustituye a los grupos
  de botones con estilos de "radio" reimplementados a mano en cada
  componente.
- **`ChipFilter<T extends string>`** — pastillas independientes
  (`role="tablist"`/`aria-selected`) para filtros tipo Strava (filtro
  de categoría de actividad).
- **`ActivityListItem`** — fila de actividad estilo feed de Strava
  (icono de deporte + título + subtítulo + métricas alineadas a la
  derecha), usada tanto en el feed de sesiones Garmin como en el
  histórico de actividades manuales.
- **`MacroBar`** — barra de proporción apilada + leyenda para
  proteína/carbohidratos/grasa, estilo diario de MyFitnessPal. Solo
  muestra el objetivo (nunca inventa consumo real que no se registra
  todavía) — el anillo (`DonutChart`) original queda como vista
  secundaria dentro de un `Disclosure`, no desaparece.
- **`FormField` + `fieldInputClass`** — envoltorio label+input+error/
  hint consistente. Sustituye al patrón `<label className="flex
  flex-col gap-1...">` con un `inputClass` duplicado y ligeramente
  distinto en cada formulario, la causa concreta de los "formularios
  nefastos" señalados por el usuario.
- **`Disclosure`** — sección plegable simple, usada para agrupar campos
  secundarios que no hacen falta a la primera (cuello/cintura/cadera del
  método Navy, ahora opcional porque la báscula Feelfit cubre el caso
  automático de composición corporal; vista de anillo de macros).
- **`PageHeader`** — cabecera título+subtítulo+acciones única para las
  7 páginas, sustituye al `<header>` manual repetido con pequeñas
  variaciones de spacing en cada una.

Composición corporal completa de la báscula Feelfit (hallazgo de esta
misma fase, no solo layout): la báscula reporta `bmi`, `muscle_kg`,
`bone_kg`, `water_pct` en cada medición, pero antes se descartaban en
el backend (`services/feelfit_sync_service.py` solo persistía
`peso_kg`/`bodyfat_pct`). Ahora se persisten (columnas nullable,
migración aditiva) y se exponen en `GET .../body-measurements/history`;
el frontend los muestra en `BodyCompositionTile` — con el mismo
criterio "unknown is not zero" que el resto del proyecto: el tile entero
no se renderiza si la medición más reciente no trae ningún campo de
composición (p. ej. una entrada manual de solo peso).

## Estado de las skills de diseño instaladas

`~/.config/opencode/skills/{apple-design,emil-design-eng,animate,...}`
se **conservan** (son herramientas genéricas del entorno, útiles para
otros proyectos), pero **no se siguen como autoridad de diseño de
Pulse**. Este documento es la única fuente de verdad para Pulse.

## Historial (para trazabilidad, no para seguir)

- v0: diseño inicial sin dirección explícita.
- v1 (WHOOP): paleta de marca WHOOP, Inter+Oswald, dark-only. **Derogado.**
- v1.5 (Apple parcial): fuente de sistema + colores de sistema Apple,
  pero conservando estructura de layout heredada de v1 (grid bento,
  `max-w-6xl` centrado). **Derogado** — fue un repintado de superficie,
  no una reconstrucción de la arquitectura de información.
- **v2:** reconstrucción completa de arquitectura de información +
  sistema visual + eliminación de inputs manuales redundantes.
- **v2.1 (este documento):** reconstrucción de composición/layout de
  las 7 páginas (kit de UI nuevo en `components/ui/`) sin tocar el tema
  visual Apple-clean, más persistencia completa de la composición
  corporal de la báscula Feelfit. Fuente de verdad vigente.
