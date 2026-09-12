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
      <label htmlFor={htmlFor} className="text-sm font-medium text-text-secondary">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-text-secondary">{hint}</p>}
      {error && (
        <p role="alert" className="text-xs text-recovery-low">
          {error}
        </p>
      )}
    </div>
  );
}

export const fieldInputClass =
  "w-full rounded-lg border border-surface-border bg-surface-muted px-3 py-2.5 text-sm text-foreground placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent";
