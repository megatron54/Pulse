"use client";

import Link from "next/link";
import { AnimatedNumber } from "./AnimatedNumber";

/**
 * Métrica suelta (Design System v3). Tres cambios respecto a v2.1, los
 * tres por hallazgos concretos de la auditoría:
 *
 *  - **Sin icono.** El icono era ornamento puro: la etiqueta ya dice
 *    "Sueño". Y en su versión con chip de color (un color por métrica)
 *    era una de las fuentes directas del aspecto "neón" que v3 rechaza
 *    (doctrina 1: el color es información, nunca decoración).
 *  - **Sin `min-w` ni rail horizontal.** El rail dejaba la tercera
 *    métrica cortada a media cifra en móvil (`3.2`, `24`). Ahora es
 *    `w-full` y vive en una rejilla que cabe (doctrina 4: nada se
 *    corta) - ver `MetricGrid`.
 *  - **Sin tarjeta propia.** Iba dentro de otra tarjeta, que v3 prohíbe
 *    (doctrina 2). La separación la hacen espacio y tipografía.
 *
 * `href` convierte la métrica en la puerta a su detalle. La cifra era un
 * callejón sin salida - se veía "Sueño 72" y no había forma de saber qué
 * pasó esa noche ni cómo venía la semana -, y el usuario pidió
 * explícitamente poder pulsarla. La pista de que se puede pulsar es el
 * subrayado de la etiqueta al enfocar o pasar por encima, no un color de
 * acento: el color aquí sigue reservado para el estado del dato
 * (doctrina 1).
 */
export function StatTile({
  label,
  value,
  unit = "",
  decimals = 0,
  valueClassName = "text-ink",
  href,
}: {
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  valueClassName?: string;
  /** Destino del detalle de esta métrica, si lo tiene. */
  href?: string;
}) {
  const contenido = (
    <>
      <span className="t-micro text-ink-3 group-hover:text-ink-2 group-hover:underline underline-offset-4">
        {label}
      </span>
      <p className={`t-metric ${valueClassName}`}>
        <AnimatedNumber value={value} decimals={decimals} />
        {unit && <span className="t-body text-ink-2">{unit}</span>}
      </p>
    </>
  );

  if (!href) {
    return <div className="flex w-full flex-col gap-1">{contenido}</div>;
  }

  return (
    <Link
      href={href}
      // El objetivo táctil es toda la casilla, cifra incluida: en móvil
      // una etiqueta de 11px es un blanco imposible.
      className="group flex w-full flex-col gap-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
    >
      {contenido}
    </Link>
  );
}

/**
 * Rejilla de métricas: sustituye al rail con scroll horizontal de v2.1.
 * `auto-fit` con un mínimo garantiza que nunca quede una columna
 * cortada - si no caben 4, pasan a 2 filas de 2, que es legible; un
 * rail que corta la tercera tarjeta a la mitad no lo es.
 */
export function MetricGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(6.5rem,1fr))] gap-x-6 gap-y-5">
      {children}
    </div>
  );
}
