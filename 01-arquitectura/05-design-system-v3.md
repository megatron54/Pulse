# Design System v3 — reconstrucción completa del frontend

> **Esta es la única fuente de verdad de diseño.** Sustituye por completo a
> `04-design-system-v2.md` (y a la iteración "v2.1"), que quedan como
> histórico. Cualquier decisión de diseño anterior que contradiga este
> documento está derogada, incluidos los comentarios que sigan vivos en
> componentes no migrados.

## Por qué se rehace (auditoría real, 2026-09-13)

No es una queja de gusto. Se auditaron las 5 páginas con capturas reales
(Playwright, 390px y 1280px) y los problemas son estructurales:

**Fallos de datos, no de estilo:**

1. **La pantalla "Hoy" mostraba datos de hace 7 días etiquetados como de
   hoy.** `GET /garmin/health-history` devuelve orden descendente (su
   propio docstring: "más reciente primero") pero `RecoveryStatusCard` y
   `HealthMetricsSummaryRow` leían `historial.at(-1)` — el elemento más
   ANTIGUO de la ventana. Con `days=7`, el hero de la app mostraba el día
   de hace una semana. Visible en la captura: las tarjetas decían VFC
   65 ms / sueño 83 mientras la narrativa del coach (que sí usa el día
   correcto) decía 50 ms / 51 en la misma tarjeta.
2. **`0.0 km` en toda sesión de gimnasio.** El principio "unknown is not
   zero" se respeta en el motor pero se violaba en la UI: una sesión de
   fuerza no tiene distancia, y renderizar `0.0 km` es afirmar un dato
   falso.
3. **`(1 días con dato)`** — concordancia de singular/plural sin resolver.
4. **Gráficas con un solo punto** renderizadas como gráfica completa con
   ejes, en vez de estado vacío.

**Fallos de arquitectura de información:**

5. **`Coach` ocupaba un quinto de la navegación principal para mostrar
   "Todavía no está construido"** — y el texto del estado vacío exponía
   jerga interna del proyecto ("es la Fase 6 del plan de reconstrucción -
   requiere un endpoint nuevo en el backend").
6. **No existía página de Perfil/Ajustes.** No había forma de ver ni
   gestionar las conexiones (Garmin, Feelfit), ni de elegir tema — el
   modo claro/oscuro dependía solo del sistema operativo, sin control.
7. **Rutas huérfanas** `/analisis` y `/salud` seguían servidas, fuera del
   nav, con contenido duplicado.
8. **"Objetivo nutricional de hoy" era una tarjeta que solo contenía un
   botón** ("Calcular macros de hoy") — en la pantalla principal y otra
   vez en Nutrición. Una tarjeta que no informa de nada y exige una
   acción manual para calcular algo que el motor puede calcular solo.
9. **"Tendencia de readiness (30 días)" era ilegible**: 30 círculos de
   color sin eje, sin fechas, sin cifras, con `flex-wrap` (el día 27
   aparece debajo del día 1, así que se rompe la lectura de línea
   temporal) y con el significado accesible solo por `title` al pasar el
   cursor — inexistente en móvil.

**Fallos de ejecución visual:**

10. **Texto cortado por todas partes**: `Strength T...` en cada fila de
    actividad, `BODY BATTERY` desbordando el círculo del medidor, railes
    horizontales que cortan la tercera tarjeta a media cifra (`3.2`,
    `24`).
11. **Color decorativo en todas partes** (el "neón"): botones azul
    saturado, chips de icono de colores por métrica, puntos azules
    repetidos en cada fila de una lista de 12. El color dejó de
    significar nada porque estaba en todo.
12. **Tarjeta dentro de tarjeta** como patrón por defecto: borde + sombra
    + radio grande, anidados dos y tres niveles.
13. **Espacio horizontal desperdiciado en desktop**: filas de 900px con
    el contenido pegado a los dos extremos y un vacío en medio.
14. **Nombres de actividad en inglés** (`Strength Training`,
    `Treadmill Running`) y fechas en ISO (`2026-09-12`) en una UI por
    lo demás en español.

## Corriente de diseño elegida (y la que se rechaza)

Se rechaza explícitamente la estética dominante en galerías de
inspiración (Dribbble/Behance) y en los artículos de "tendencias 2026":
glassmorphism, fondos degradados, tarjetas flotantes translúcidas, neón
sobre oscuro cinematográfico, un color distinto por métrica. **Esa es
exactamente la estética que el usuario identifica como "AI slop"**, y no
es casual: es lo que se optimiza para una captura bonita en una galería,
no para leer datos propios todos los días durante años.

La referencia es el diseño de producto de herramientas de datos
profesionales — la escuela de Linear, Stripe, Vercel, y la de diseño de
información editorial (Economist/FT para gráficas). Principios, no
imitación:

### 1. El color es información, nunca decoración

La interfaz es ~95% neutra. El color aparece **solo** cuando codifica un
estado que el usuario necesita distinguir (zona de recovery, señal de
desviación). Consecuencias directas:

- **Las acciones primarias no son azules.** Son de alto contraste neutro
  (casi negro en claro, casi blanco en oscuro). Un botón azul saturado
  compite con los datos.
- **Se prohíben los chips de icono de color por métrica.** Un icono es
  orientación, no ornamento; va en el color del texto secundario.
- Si dos elementos de la misma pantalla usan color sin codificar estados
  distintos, uno de los dos está mal.

### 2. La jerarquía la hacen el tipo y el espacio, no los bordes

Un solo nivel de elevación. **Prohibida la tarjeta dentro de tarjeta.**
Para separar dentro de un contenedor se usa espacio o una línea de 1px,
nunca otro contenedor con borde y sombra. En modo claro las tarjetas no
llevan sombra: llevan una línea. La sombra se reserva para lo que
realmente flota sobre el contenido (nav flotante, overlays).

Radios contenidos: 10px en contenedores, 6px en controles. El radio
grande generalizado (16px+) es un marcador de la estética que se
rechaza.

### 3. Los datos tabulares van en tablas

Una lista de 12 actividades con duración y distancia es una tabla:
cabecera de columna **una vez** (no `DURACIÓN`/`DISTANCIA` repetido en
cada fila), cifras alineadas a la derecha, `tabular-nums`, filas
separadas por línea de 1px dentro de un único contenedor. En móvil
colapsa a filas de dos líneas, pero sigue siendo una tabla, no 12
tarjetas.

### 4. Nada se corta

El texto tiene sitio o se ajusta en dos líneas. **Ninguna elipsis en
contenido primario** (el nombre de una actividad es contenido primario).
Los railes con scroll horizontal que dejan una tarjeta cortada a la
mitad se sustituyen por rejillas que caben.

### 5. "Unknown is not zero" también en la interfaz

Si un dato no existe, no se renderiza — no se renderiza un cero. Una
sesión de fuerza no muestra distancia. Una gráfica con menos de 2 puntos
no es una gráfica: es un estado vacío que dice qué falta.

### 6. Toda gráfica lleva eje y unidad, o no es una gráfica

Un conjunto de puntos de color sin eje temporal ni cifras no comunica:
decora. Si el dato es categórico (semáforo de recovery), se comunica con
cifras y una línea temporal etiquetada, no con 30 círculos que se
envuelven en dos filas.

### 7. Los estados vacíos hablan al usuario

Dicen qué falta y qué hacer, en el idioma del usuario. **Nunca** exponen
jerga interna del proyecto (nombres de fase, endpoints que faltan,
números de épica).

### 8. La densidad es una virtud

Es una app de datos personales de uso diario, no una landing. El objetivo
es leer mucho de un vistazo con calma tipográfica — no una tarjeta
gigante por dato con aire de sobra.

### 9. Idioma y formato consistentes

Todo en español, incluidos los datos que llegan en inglés de Garmin
(`Strength Training` → `Fuerza`). Fechas humanas (`Hoy`, `Ayer`,
`12 sep`), nunca ISO en la interfaz. Concordancia de plurales resuelta.

## Tokens

Neutros de base cálida-neutra, control estricto del contraste. Nombres
semánticos por rol, no por color.

| Rol | Claro | Oscuro |
| --- | --- | --- |
| `--canvas` (fondo de página) | `#f6f6f5` | `#0c0c0d` |
| `--surface` (contenedor) | `#ffffff` | `#17171a` |
| `--line` (hairline) | `#e4e4e2` | `#27272b` |
| `--line-strong` (divisor con peso) | `#d2d2cf` | `#35353b` |
| `--ink` (texto primario) | `#18181a` | `#f4f4f5` |
| `--ink-2` (secundario) | `#62626a` | `#a0a0a8` |
| `--ink-3` (terciario/micro) | `#97979e` | `#6e6e76` |
| `--action` / `--action-ink` | `#18181a` / `#fff` | `#f4f4f5` / `#18181a` |

Semánticos, deliberadamente desaturados (nada de `#30d158`/`#ff453a`):

| Rol | Claro | Oscuro |
| --- | --- | --- |
| `--pos` (óptimo) | `#1a7f43` | `#54b97a` |
| `--warn` (precaución) | `#96650a` | `#cfa14e` |
| `--neg` (alerta) | `#ab2b23` | `#d9807a` |
| `--data` (dato neutro: sueño, series) | `#3f4a73` | `#8e97bd` |

### Tema claro/oscuro/sistema

Tres modos reales con control explícito del usuario en Perfil, no solo
`prefers-color-scheme`. `data-theme` en `<html>`, resuelto por un script
inline antes del primer paint (sin destello), persistido en
`localStorage` (`pulse_theme`). El valor `system` sigue al sistema
operativo en vivo.

### Escala tipográfica

Una sola escala, con `tabular-nums` obligatorio en toda cifra:

| Uso | Tamaño/línea | Peso | Tracking |
| --- | --- | --- | --- |
| Título de página | 28/34 | 600 | -0.02em |
| Cifra hero | 44/48 | 500 | -0.03em |
| Título de sección | 15/20 | 600 | -0.01em |
| Cifra de métrica | 22/28 | 500 | -0.01em |
| Cuerpo | 14/20 | 400 | 0 |
| Secundario | 13/18 | 400 | 0 |
| Micro (cabecera de columna) | 11/14 | 500 | 0.04em, mayúsculas |

## Arquitectura de información

Cinco destinos reales. `Coach` sale de la navegación principal hasta que
exista de verdad (su valor ya se entrega hoy como narrativa en contexto
dentro de las páginas); su sitio lo ocupa **Perfil**, que faltaba.

| Destino | Responsabilidad | Qué NO va aquí |
| --- | --- | --- |
| **Hoy** | Cómo estoy hoy y qué hago hoy. Nada más. | Tendencias de 30 días, botones de cálculo, histórico |
| **Cuerpo** | Peso y composición, y su evolución | Nada de entrenamiento |
| **Entrenamiento** | Sesiones (tabla), plan, carga y recuperación | Composición corporal |
| **Nutrición** | Objetivo de hoy (calculado, no a botón) y plan de fase | — |
| **Perfil** | Datos propios, apariencia (tema), conexiones (Garmin/Feelfit) y estado real de sincronización | Datos de salud |

Se eliminan las rutas huérfanas `/analisis` y `/salud`.

## Verificación obligatoria

Ningún cambio visual se considera terminado sin capturas reales de
Playwright en **claro y oscuro × 390px y 1280px**, revisadas de verdad
(fue así como se encontraron el texto cortado, el `0.0 km` y el desfase
de datos del hero — ninguno salía en los tests). Además: `tsc --noEmit`
limpio y la suite de `vitest` en verde.
