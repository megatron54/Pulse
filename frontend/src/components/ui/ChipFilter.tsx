"use client";

/**
 * Fila de filtros que puede crecer y hacer wrap (deportes, métricas
 * intradía). Se diferencia de `SegmentedControl` en eso: aquel es un
 * único control agrupado de 2-4 opciones fijas que nunca salta de línea.
 *
 * Design System v3: el chip activo se distingue por contraste
 * (`bg-action`, el neutro de alto contraste) y no por un azul de acento
 * sobre gris; los inactivos son texto con línea de 1px en vez de
 * pastillas rellenas de gris. Altura mínima de 36px para que sigan
 * siendo cómodos de pulsar sin convertirse en botones enormes.
 */
export function ChipFilter<T extends string>({
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
    <div role="tablist" aria-label={ariaLabel} className="flex flex-wrap gap-2">
      {options.map((option) => {
        const activa = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={activa}
            onClick={() => onChange(option.value)}
            className={`t-body min-h-9 whitespace-nowrap rounded-md border px-3.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas ${
              activa
                ? "border-action bg-action font-medium text-action-ink"
                : "border-line bg-surface text-ink-2 hover:text-ink"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
