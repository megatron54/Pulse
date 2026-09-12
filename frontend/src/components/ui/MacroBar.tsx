/**
 * Barra apilada de proporción de macros (estilo cabecera de diario de
 * MyFitnessPal) + leyenda con gramos - sustituye al donut como
 * cabecera principal de la página Nutrición (el donut de
 * `NutritionTargetCard` se conserva para su propio detalle). Representa
 * ÚNICAMENTE la composición del OBJETIVO diario, nunca un progreso de
 * consumo: no existe diario de comidas en Pulse, así que fabricar una
 * barra de "progreso" sería inventar un dato que no existe
 * ("unknown is not zero").
 */
export function MacroBar({
  segments,
}: {
  segments: { label: string; grams: number; kcal: number; color: string }[];
}) {
  const totalKcal = segments.reduce((acc, s) => acc + s.kcal, 0);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-surface-muted">
        {segments.map((s) =>
          s.kcal > 0 ? (
            <div
              key={s.label}
              style={{ width: `${(s.kcal / totalKcal) * 100}%`, backgroundColor: s.color }}
            />
          ) : null
        )}
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-sm">
            <span
              aria-hidden="true"
              className="size-2.5 rounded-full"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-text-secondary">{s.label}</span>
            <span className="font-medium text-foreground tabular-nums">{s.grams.toFixed(0)}g</span>
          </div>
        ))}
      </div>
    </div>
  );
}
