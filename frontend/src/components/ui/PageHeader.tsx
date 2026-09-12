import type { ReactNode } from "react";

/**
 * Cabecera de página estandarizada (v2.1): antes cada página repetía a
 * mano `<header className="mb-6">` con un `<h1>` y un `<p>` sueltos, sin
 * ningún sitio consistente para acciones a la derecha (selector de
 * rango, pestañas...) - unas las metían dentro del `<header>`, otras
 * debajo, sin criterio único.
 */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {subtitle && <p className="mt-1 text-text-secondary">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
