"use client";

/**
 * Fila de chips de filtro independientes (a diferencia de
 * `SegmentedControl`, que es un único control agrupado): pensado para
 * listas de opciones que pueden crecer y hacer wrap (categorías de
 * deporte, métricas intradía) - mismo patrón visual ya usado de forma
 * ad-hoc en `SesionesEntrenamiento`/`IntradayMetricCard`, ahora
 * compartido.
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
            className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
              activa
                ? "bg-accent text-white"
                : "bg-surface-muted text-text-secondary hover:text-foreground"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
