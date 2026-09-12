import type { LucideIcon } from "lucide-react";

/**
 * Fila de actividad estilo feed de Strava: icono de deporte + título +
 * fecha a la izquierda, métricas alineadas a la derecha - sustituye a
 * las filas planas `flex justify-between` de `GarminActivitiesCard`/
 * `SportActivityHistoryCard`, que no distinguían visualmente entre
 * actividades ni escalaban bien a más de 2 métricas.
 */
export function ActivityListItem({
  icon: Icon,
  title,
  subtitle,
  metrics,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  metrics: { label: string; value: string }[];
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-surface-border bg-surface px-4 py-3 transition-colors hover:bg-surface-muted">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent">
        <Icon aria-hidden="true" size={18} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-foreground capitalize">{title}</p>
        <p className="text-xs text-text-secondary">{subtitle}</p>
      </div>
      <div className="flex shrink-0 gap-4 text-right">
        {metrics.map((m) => (
          <div key={m.label}>
            <p className="text-sm font-medium text-foreground tabular-nums">{m.value}</p>
            <p className="text-[10px] uppercase tracking-wide text-text-secondary">{m.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
