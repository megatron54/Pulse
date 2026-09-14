/**
 * Lista de pares etiqueta/valor separados por un filete de 1px (Design
 * System v3, doctrinas 2 y 3: jerarquía por espacio y divisores, nunca
 * una tarjeta por cada dato).
 *
 * Es un `<dl>` real, no un grid de `<div>`: la relación entre "Altura"
 * y "176 cm" es semántica, y un lector de pantalla la anuncia como
 * término/definición sin que haya que inventar `aria-label`s.
 *
 * `items-baseline` + `gap-6` + valor alineado a la derecha en vez de
 * columnas fijas: así ninguna etiqueta se corta (doctrina 6, "nada
 * truncado" - era literalmente la queja del usuario), y si el valor es
 * largo baja de línea en vez de comerse la etiqueta.
 */
export function DataList({ children }: { children: React.ReactNode }) {
  return <dl className="divide-y divide-line">{children}</dl>;
}

export function DataRow({
  label,
  children,
  nota,
}: {
  label: string;
  children: React.ReactNode;
  /** Aclaración bajo el valor (de dónde sale, desde cuándo, etc.). */
  nota?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-6 py-3 first:pt-0 last:pb-0">
      <dt className="t-body shrink-0 text-ink-2">{label}</dt>
      <dd className="flex flex-col items-end gap-0.5 text-right">
        <span className="t-body text-ink">{children}</span>
        {nota && <span className="t-secondary text-ink-3">{nota}</span>}
      </dd>
    </div>
  );
}
