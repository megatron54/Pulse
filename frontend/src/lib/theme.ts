/**
 * Paleta de Pulse en un único módulo TS, para los contextos que no
 * pueden usar clases de Tailwind (atributos SVG `stroke`/`fill`,
 * estilos inline calculados dinámicamente como el ancho de una barra).
 * Espeja exactamente los tokens de `globals.css` (`--color-*`) - si
 * cambia un hex, solo hay que tocarlo aquí (code-review M1: antes
 * estaba duplicado como string crudo en 3-4 componentes distintos).
 *
 * Colores tomados de la guía oficial de marca de WHOOP ("WHOOP - Brand
 * & Design Guidelines"): zonas de recovery, strain, sleep y teal.
 */
export const PALETA = {
  recoveryHigh: "#16EC06",
  recoveryMedium: "#FFDE00",
  recoveryLow: "#FF0026",
  strain: "#0093E7",
  sleep: "#7BA1BB",
  teal: "#00F19F",
  recoveryBlue: "#67AEE6",
  surfaceTrack: "#2c3338",
  textPrimary: "#f2f4f5",
  textMuted: "#a9b2b8",
} as const;
