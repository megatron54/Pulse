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
Coach          — chat conversacional con IA
Nutrición      — (sin cambios de fondo, solo tema visual)
Cuerpo         — peso, composición (sin cambios de fondo, solo tema visual)
```

Se eliminan como páginas de primer nivel: `/running`, `/ciclismo`,
`/gimnasio` (pasan a ser un filtro `categoria=` dentro de
Entrenamiento → Sesiones) y `/garmin` (sus datos se reparten entre
Hoy/Recuperación/Análisis; el emparejamiento de cuenta pasa a Ajustes).

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
- **v2 (este documento):** reconstrucción completa de arquitectura de
  información + sistema visual + eliminación de inputs manuales
  redundantes. Fuente de verdad vigente.
