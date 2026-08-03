import type { ReactNode } from "react";

/**
 * Superficie de tarjeta oscura compartida (rediseño estilo WHOOP): fondo
 * ligeramente más claro que el degradado de la página, borde sutil,
 * esquinas redondeadas generosas. Reemplaza el `border rounded-lg p-6`
 * plano en blanco que usaban todas las tarjetas antes del rediseño.
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
      className={`rounded-2xl border border-surface-border bg-surface p-6 shadow-lg shadow-black/20 ${className}`}
    >
      {children}
    </div>
  );
}

/** Título de sección: mayúsculas + letter-spacing, como los headlines
 * de la guía de marca de WHOOP (Proxima Nova Bold, 10% tracking). */
export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-300 mb-4">
      {children}
    </h2>
  );
}
