import type { ReactNode } from "react";

/**
 * Superficie base (Design System v3 - 01-arquitectura/05-design-system-v3.md).
 *
 * Cambios respecto a v2, los dos por hallazgos de la auditoría:
 *  - Sin sombra: en claro la separación la hace una línea de 1px
 *    (doctrina 2, "un solo nivel de elevación"). La sombra se reserva
 *    para lo que de verdad flota sobre el contenido.
 *  - Radio 10px en vez de 16px: el radio grande generalizado es un
 *    marcador de la estética que v3 rechaza.
 *
 * `plano` sirve para cuando esta superficie contiene una tabla o una
 * lista con divisores, que necesitan llegar hasta el borde: el padding
 * lo pone entonces cada fila, no el contenedor. Es la alternativa a
 * anidar otra tarjeta dentro, que v3 prohíbe.
 */
export function Card({
  children,
  className = "",
  plano = false,
}: {
  children: ReactNode;
  className?: string;
  plano?: boolean;
}) {
  return (
    <div
      className={`rounded-[10px] border border-line bg-surface ${plano ? "" : "p-5"} ${className}`}
    >
      {children}
    </div>
  );
}

/** Título de sección. Usa la escala tipográfica única (`.t-section`) en
 * vez de componer `text-sm font-semibold` a mano, que es de donde venía
 * la deriva tipográfica de v2. */
export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className="t-section mb-4 text-ink">{children}</h2>;
}
