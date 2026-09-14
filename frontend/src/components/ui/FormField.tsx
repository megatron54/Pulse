import type { ReactNode } from "react";

/**
 * Envoltorio label+input+error consistente (v2.1): sustituye al patrón
 * `<label className="flex flex-col gap-1 text-sm...">` con un
 * `inputClass` duplicado que cada formulario (medidas corporales, plan
 * semanal, conexión Garmin) reimplementaba con pequeñas variaciones -
 * la causa concreta de los "formularios nefastos" señalados por el
 * usuario.
 */
export function FormField({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor?: string;
  error?: string | null;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="t-secondary font-medium text-ink-2">
        {label}
      </label>
      {children}
      {hint && !error && <p className="t-secondary text-ink-3">{hint}</p>}
      {error && (
        <p role="alert" className="t-secondary text-neg">
          {error}
        </p>
      )}
    </div>
  );
}

// El foco se marca con `ring-ink` (el propio color del texto), no con un
// azul de acento: Design System v3, doctrina 1 - el color comunica
// información, y "dónde estoy escribiendo" no es una categoría de dato.
export const fieldInputClass =
  "t-body w-full rounded-md border border-line bg-canvas px-3 py-2.5 text-ink placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-ink";
