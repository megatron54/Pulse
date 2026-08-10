import type { ReactNode } from "react";

/**
 * Superficie de tarjeta compartida (Design System v2 -
 * 01-arquitectura/04-design-system-v2.md): un solo nivel de
 * separación (borde sutil + sombra suave), sin materiales
 * translúcidos decorativos. Funciona en claro/oscuro vía las
 * variables de `globals.css`.
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
      className={`rounded-2xl border border-surface-border bg-surface p-6 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

/** Título de sección: jerarquía discreta (tamaño pequeño, peso medio,
 * color secundario) - no "small caps" agresivo, coherente con el resto
 * de la tipografía de sistema. */
export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-sm font-semibold text-foreground mb-4">{children}</h2>;
}
