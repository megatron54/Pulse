/**
 * Paleta de Pulse en un único módulo TS, para los contextos que no
 * pueden usar clases de Tailwind (atributos SVG `stroke`/`fill`,
 * estilos inline calculados dinámicamente como el ancho de una barra).
 * Espeja exactamente los tokens de `globals.css` (`--color-*`) - si
 * cambia un hex, solo hay que tocarlo aquí (code-review M1: antes
 * estaba duplicado como string crudo en 3-4 componentes distintos).
 *
 * Rediseño estilo Apple (skill `apple-design`): colores de sistema de
 * Apple en modo oscuro (systemGreen/Yellow/Red/Blue/Indigo/Teal),
 * mismo significado semántico que la paleta WHOOP anterior. Hallazgo
 * de code-review: este archivo se había quedado desincronizado del
 * repintado de `globals.css` (los hex viejos seguían aquí, y
 * `RecoveryRing.test.tsx` los asserteaba) - unica fuente de verdad de
 * verdad ahora en ambos sitios a la vez.
 */
export const PALETA = {
  recoveryHigh: "#30D158",
  recoveryMedium: "#FFD60A",
  recoveryLow: "#FF453A",
  strain: "#0A84FF",
  sleep: "#5E5CE6",
  teal: "#64D2FF",
  recoveryBlue: "#64D2FF",
  surfaceTrack: "#2c3338",
  textPrimary: "#f2f4f5",
  textMuted: "#a9b2b8",
} as const;
