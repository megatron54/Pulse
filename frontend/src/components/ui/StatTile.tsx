"use client";

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
 */
export function StatTile({
  label,
  value,
  unit = "",
  decimals = 0,
  valueClassName = "text-ink",
}: {
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  valueClassName?: string;
}) {
  return (
    <div className="flex w-full flex-col gap-1">
      <span className="t-micro text-ink-3">{label}</span>
      <p className={`t-metric ${valueClassName}`}>
        <AnimatedNumber value={value} decimals={decimals} />
        {unit && <span className="t-body text-ink-2">{unit}</span>}
      </p>
    </div>
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
