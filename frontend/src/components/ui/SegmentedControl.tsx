"use client";

/**
 * Control segmentado: un único contenedor con la opción activa
 * resaltada - sustituye a los selectores de rango/pestaña que antes
 * cada componente reimplementaba a mano con estilos ligeramente
 * distintos entre sí (ej. el rango 7d/30d/90d de
 * `GarminHealthHistoryCard` vs. las pestañas Sesiones/Plan de la
 * página Entrenamiento).
 *
 * Design System v3: la opción activa se distingue por CONTRASTE de
 * superficie (`bg-surface` sobre `bg-canvas`) y peso de texto, no por
 * un color de acento ni por una sombra. El estado activo nunca se
 * comunica solo con color (doctrina 1: el color es información, y aquí
 * la información es "cuál está seleccionada", que ya la lleva el
 * `aria-selected` y el fondo).
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
      className="inline-flex items-center gap-1 rounded-md border border-line bg-canvas p-1"
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
            className={`t-secondary min-h-8 rounded px-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink ${
              activa ? "bg-surface font-medium text-ink" : "text-ink-2 hover:text-ink"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
