import type { GarminHealthDay } from "@/lib/api";

/**
 * Las fases de una noche: una barra apilada con su leyenda escrita.
 *
 * Una barra y no una tendencia porque lo que importa es la PROPORCIÓN
 * entre fases de una noche concreta. Los cuatro colores independientes
 * de v2 (índigo, violeta, lila, gris) se sustituyen por una escala del
 * mismo color de datos: las fases son una sola magnitud dividida en
 * partes, y una escala lo dice; cuatro colores sin relación sugieren
 * cuatro cosas sin relación (doctrina 1).
 *
 * La leyenda lleva la cifra escrita al lado: la barra sola obligaba a
 * pasar el cursor por encima (`title`), imposible en un móvil, que es
 * donde se usa la app (doctrina 5).
 *
 * Se extrajo de `GarminHealthHistoryCard`, donde era privada, al
 * aparecer el segundo sitio que la necesita: la página de detalle del
 * sueño, que además deja elegir QUÉ noche mirar. Copiarla habría dejado
 * dos barras de fases con escalas distintas a la primera vez que alguien
 * tocara una de las dos.
 */
export const FASES_SUENO = [
  { campo: "deep_sleep_seg", label: "Profundo", opacidad: 1 },
  { campo: "rem_sleep_seg", label: "REM", opacidad: 0.7 },
  { campo: "light_sleep_seg", label: "Ligero", opacidad: 0.42 },
  { campo: "awake_sleep_seg", label: "Despierto", opacidad: 0.18 },
] as const;

export function horasYMinutos(segundos: number): string {
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`;
}

/** Segundos de sueño de una noche, sin contar el tiempo despierto: la
 *  suma de las cuatro fases es tiempo EN la cama, y "he dormido 7 h 40"
 *  no incluye los despertares. */
export function segundosDormidos(dia: GarminHealthDay): number {
  return (dia.deep_sleep_seg ?? 0) + (dia.rem_sleep_seg ?? 0) + (dia.light_sleep_seg ?? 0);
}

/** Si esa noche tiene fases que dibujar. Lo pregunta quien necesita
 *  decir otra cosa en su lugar: `FasesSueno` devuelve `null` y un `null`
 *  no se puede distinguir desde fuera. */
export function tieneFases(dia: GarminHealthDay): boolean {
  return FASES_SUENO.some((fase) => (dia[fase.campo] ?? 0) > 0);
}

/** `null` si esa noche no tiene fases registradas: la ausencia se dibuja
 *  como ausencia, nunca como cuatro fases a cero. */
export function FasesSueno({ dia }: { dia: GarminHealthDay }) {
  const segundos = FASES_SUENO.map((fase) => dia[fase.campo] ?? 0);
  const total = segundos.reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  return (
    <div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-canvas">
        {FASES_SUENO.map((fase, i) => {
          const valor = segundos[i];
          if (valor === 0) return null;
          return (
            <div
              key={fase.campo}
              style={{
                width: `${(valor / total) * 100}%`,
                backgroundColor: "var(--data)",
                opacity: fase.opacidad,
              }}
            />
          );
        })}
      </div>
      <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(7rem,1fr))] gap-x-6 gap-y-2">
        {FASES_SUENO.map((fase, i) => {
          const valor = segundos[i];
          if (valor === 0) return null;
          return (
            <div key={fase.campo} className="flex items-baseline gap-2">
              <span
                aria-hidden="true"
                className="size-2 shrink-0 translate-y-[-1px] rounded-full"
                style={{ backgroundColor: "var(--data)", opacity: fase.opacidad }}
              />
              <dt className="t-secondary text-ink-2">{fase.label}</dt>
              <dd className="t-secondary tabular ml-auto text-ink">{horasYMinutos(valor)}</dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
