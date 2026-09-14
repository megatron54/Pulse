"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

/**
 * Sección plegable: agrupa campos secundarios que no hacen falta a la
 * primera (ej. cuello/cintura/cadera del método Navy en
 * `BodyMeasurementForm`, opcionales ahora que la báscula cubre el caso
 * automático de composición corporal).
 *
 * v3: tokens de rol y área táctil de 44px (WCAG 2.5.5), que con
 * `text-sm` a secas no se alcanzaba.
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
    <div className="border-t border-line pt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="t-body flex min-h-11 w-full items-center justify-between gap-4 font-medium text-ink-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
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
