"use client";

import { Skeleton } from "./Skeleton";

/**
 * Estado de carga estandarizado (auditoría UI/UX, hallazgo H2): antes,
 * cada tarjeta implementaba su propio "Cargando..." con markup
 * ligeramente distinto - algunas con `role="status"`, otras sin él;
 * `TrainingLoadCard` no lo tenía; `WeightTrendCard`/`ReadinessTrendCard`
 * no mostraban NINGÚN estado mientras cargaban (salto brusco de vacío
 * a contenido). Un único componente garantiza que todas las tarjetas
 * anuncien "cargando" a lectores de pantalla de la misma forma, y
 * reutiliza el mismo shimmer de `Skeleton` (barrido de gradiente) en
 * vez de reimplementar su propia animación - antes esto duplicaba la
 * misma lógica de `visibilitychange`/`prefers-reduced-motion` en dos
 * sitios (hallazgo MEDIUM de code-review).
 */
export function LoadingState({ lines = 2 }: { lines?: number }) {
  return (
    <div role="status" aria-label="Cargando" className="flex flex-col gap-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-4" style={{ width: i === 0 ? "60%" : "90%" }} />
      ))}
      <span className="sr-only">Cargando...</span>
    </div>
  );
}
