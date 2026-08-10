/**
 * Gráfica de línea minimalista en SVG puro, sin dependencias externas
 * (Fase I del plan autónomo: UI de gráficas de tendencia). Se evitó
 * deliberadamente una librería como recharts/visx para no aumentar la
 * superficie de auditoría de dependencias del frontend por una gráfica
 * tan simple - ver decisión de "0 vulnerabilidades" del PR #26.
 *
 * Principio "unknown is not zero" aplicado a la UI: con 0 o 1 puntos no
 * hay tendencia que trazar, así que se muestra un mensaje explícito en
 * vez de una línea plana o un SVG vacío que parezca un bug.
 */
import { PALETA } from "@/lib/theme";

const ANCHO = 300;
const ALTO = 80;
const PADDING_VERTICAL = 8;

export function Sparkline({
  values,
  strokeColor = PALETA.accent,
  label = "Gráfica de tendencia",
}: {
  values: number[];
  strokeColor?: string;
  label?: string;
}) {
  if (values.length < 2) {
    return (
      <p className="text-sm text-text-secondary italic">
        Sin datos suficientes para mostrar una tendencia.
      </p>
    );
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const rango = max - min || 1; // evita división por cero si todos los valores son iguales

  const puntos = values
    .map((valor, i) => {
      const x = (i / (values.length - 1)) * ANCHO;
      const yNormalizado = (valor - min) / rango;
      const y = ALTO - PADDING_VERTICAL - yNormalizado * (ALTO - 2 * PADDING_VERTICAL);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${ANCHO} ${ALTO}`}
      width="100%"
      height={ALTO}
      role="img"
      aria-label={label}
    >
      <polyline points={puntos} fill="none" stroke={strokeColor} strokeWidth={2} />
    </svg>
  );
}
