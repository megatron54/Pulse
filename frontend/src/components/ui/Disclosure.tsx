"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

/**
 * Sección plegable simple (v2.1): usada para agrupar campos
 * secundarios que no hacen falta a la primera (ej. cuello/cintura/
 * cadera del método Navy en `BodyMeasurementForm`, opcionales ahora que
 * la báscula Feelfit cubre el caso automático de composición corporal).
 */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
}: {
  summary: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-t border-surface-border pt-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between text-sm font-medium text-text-secondary hover:text-foreground"
      >
        {summary}
        <ChevronDown
          aria-hidden="true"
          size={16}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && <div className="mt-3 flex flex-col gap-3">{children}</div>}
    </div>
  );
}
