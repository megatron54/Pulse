/**
 * Paleta de Pulse en un único módulo TS, para los contextos que no
 * pueden usar clases de Tailwind (atributos SVG `stroke`/`fill`,
 * estilos inline calculados dinámicamente). Espeja los tokens de
 * `globals.css` (`--color-*`) - fuente de verdad única:
 * `01-arquitectura/04-design-system-v2.md`.
 *
 * Nota: como `globals.css` ahora soporta claro/oscuro reales vía
 * `prefers-color-scheme`, estos valores fijos son los de **modo
 * oscuro** (mismo criterio que antes de este módulo: los pocos
 * consumidores que necesitan un hex directo - gráficas SVG - siguen
 * viéndose bien en ambos modos porque son colores saturados de
 * estado, no dependen del fondo).
 */
export const PALETA = {
  recoveryHigh: "#30D158",
  recoveryMedium: "#FFD60A",
  recoveryLow: "#FF453A",
  accent: "#0A84FF",
  sleep: "#5E5CE6",
  surfaceTrack: "#2c2c2e",
  textPrimary: "#f2f2f7",
  textMuted: "rgba(235, 235, 245, 0.6)",
} as const;
