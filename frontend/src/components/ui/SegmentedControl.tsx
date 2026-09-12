"use client";

/**
 * Control segmentado tipo iOS: un único contenedor con la opción activa
 * resaltada (fondo propio + sombra sutil) - sustituye a los selectores
 * de rango/pestaña que antes cada componente reimplementaba a mano con
 * botones sueltos y estilos ligeramente distintos entre sí (ej. el
 * rango 7d/30d/90d de `GarminHealthHistoryCard` vs. las pestañas
 * Sesiones/Plan de la página Entrenamiento).
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="inline-flex items-center gap-0.5 rounded-full bg-surface-muted p-1"
    >
      {options.map((option) => {
        const activa = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={activa}
            onClick={() => onChange(option.value)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              activa
                ? "bg-surface text-foreground shadow-sm"
                : "text-text-secondary hover:text-foreground"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
