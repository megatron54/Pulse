import type { LucideIcon } from "lucide-react";

/**
 * Estado vacío estandarizado (auditoría UI/UX, hallazgo M2): antes,
 * cada tarjeta mostraba un `<p className="italic">` con texto
 * variable, y `GarminActivitiesCard` rompía el patrón con 3-4 líneas
 * en vez de las 1-2 del resto - ninguna usaba un icono, así que el
 * momento "todavía no hay datos" (la primera vez que un usuario nuevo
 * ve cada tarjeta) tenía la jerarquía visual más débil de toda la app.
 * Un icono `lucide-react` (coherente con el resto de iconografía SVG
 * ya establecida en `Nav.tsx`) da a ese momento algo de peso visual
 * sin necesitar una ilustración custom.
 */
export function EmptyState({ icon: Icon, message }: { icon: LucideIcon; message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-3 text-center">
      <Icon aria-hidden="true" size={28} className="text-gray-600" />
      <p className="text-sm text-gray-400 text-pretty">{message}</p>
    </div>
  );
}
