/**
 * Reparto de macros del objetivo diario: barra proporcional + cifras
 * escritas (Design System v3).
 *
 * Dos cambios respecto a v2:
 *
 *  - **Un color por macro, elegido "por analogía visual"** (teal para
 *    proteína, azul para carbohidratos, azul de sueño para grasa) era
 *    color decorativo puro: no existe una semántica de color de los
 *    macros, y esos tres tonos saturados eran de los objetos más
 *    llamativos de la app (doctrina 1). Los tres macros son partes de
 *    una misma magnitud - las kcal del día - así que se representan con
 *    una escala del mismo color de datos, igual que las fases de sueño.
 *  - **El porcentaje se escribe.** La proporción era la única razón de
 *    ser de la barra y solo existía como longitud, imposible de leer
 *    con precisión y ausente para un lector de pantalla.
 *
 * Representa ÚNICAMENTE la composición del OBJETIVO diario, nunca un
 * progreso de consumo: no hay diario de comidas en Pulse, así que una
 * barra de "progreso" inventaría un dato que no existe.
 */
export function MacroBar({
  macros,
}: {
  macros: { label: string; gramos: number; kcal: number }[];
}) {
  const totalKcal = macros.reduce((acc, m) => acc + m.kcal, 0);
  if (totalKcal === 0) return null;

  // Escala de opacidad en el orden recibido (proteína, carbohidratos,
  // grasa): ordena los tres sin sugerir que sean magnitudes ajenas.
  const opacidad = [1, 0.62, 0.3];

  return (
    <div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-canvas">
        {macros.map((m, i) =>
          m.kcal > 0 ? (
            <div
              key={m.label}
              style={{
                width: `${(m.kcal / totalKcal) * 100}%`,
                backgroundColor: "var(--data)",
                opacity: opacidad[i] ?? 0.3,
              }}
            />
          ) : null
        )}
      </div>
      <dl className="mt-3 divide-y divide-line">
        {macros.map((m, i) => (
          <div key={m.label} className="flex items-baseline justify-between gap-6 py-2">
            <dt className="t-body flex items-center gap-2 text-ink-2">
              <span
                aria-hidden="true"
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: "var(--data)", opacity: opacidad[i] ?? 0.3 }}
              />
              {m.label}
            </dt>
            <dd className="flex items-baseline gap-3">
              <span className="t-body tabular text-ink">{m.gramos.toFixed(0)} g</span>
              <span className="t-secondary tabular w-12 text-right text-ink-3">
                {Math.round((m.kcal / totalKcal) * 100)} %
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
