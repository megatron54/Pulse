import type { ReactNode } from "react";

/**
 * Superficie de tarjeta compartida (rediseño estilo Apple: skill
 * `apple-design` §12 "Materials & depth - translucency conveys
 * hierarchy"). Antes era un panel opaco plano (`bg-surface` sólido,
 * estilo WHOOP); ahora es un material translúcido real
 * (`.material-surface`, definida en globals.css) sobre el fondo casi
 * negro de la página - el blur necesita algo detrás contra lo que
 * separar profundidad, por eso el cambio de paleta acompaña a este.
 * `prefers-reduced-transparency` se resuelve en la propia clase CSS
 * (fondo sólido, sin blur) - ningún componente que use `Card` necesita
 * saber de esa media query.
 */
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`material-surface rounded-2xl border border-surface-border p-6 shadow-xl shadow-black/40 ${className}`}
    >
      {children}
    </div>
  );
}

/** Título de sección: mismo patrón de "small caps" gris que usa iOS en
 * cabeceras de sección de Settings/Health (no es exclusivo de WHOOP) -
 * pero con tracking más contenido (apple-design §15: la tracking es
 * específica del tamaño, `tracking-widest` en texto pequeño ya es
 * demasiado abierto; `tracking-wide` es el punto correcto) y un gris
 * más neutro/tenue, coherente con la jerarquía discreta de Apple. */
export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-xs font-semibold uppercase tracking-wide text-white/50 mb-4">
      {children}
    </h2>
  );
}
