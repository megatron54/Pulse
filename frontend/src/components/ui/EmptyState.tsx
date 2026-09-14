import type { LucideIcon } from "lucide-react";

/**
 * Estado vacío (Design System v3, doctrina 7: "los estados vacíos
 * hablan al usuario").
 *
 * v2 centraba un icono grande y un texto en cursiva - mucho peso visual
 * para decir "no hay nada", y con el icono como ornamento. v3 lo deja
 * alineado a la izquierda como un párrafo normal: un estado vacío es
 * información, no un cartel.
 *
 * `icon` se mantiene opcional y solo por compatibilidad con las páginas
 * aún no migradas a v3; los llamadores nuevos no deberían pasarlo.
 * Cuando no quede ninguno, quitar el parámetro.
 *
 * `accion` permite decir QUÉ HACER y no solo qué falta, que era el otro
 * fallo del patrón anterior.
 */
export function EmptyState({
  message,
  accion,
}: {
  icon?: LucideIcon;
  message: string;
  accion?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-3 py-1">
      <p className="t-body text-pretty text-ink-2">{message}</p>
      {accion}
    </div>
  );
}
