import type { ReactNode } from "react";

/**
 * Tabla de datos (Design System v3, doctrina 3: "los datos tabulares van
 * en una tabla").
 *
 * Sustituye al patrón de v2 en el que cada registro era su propia
 * tarjeta con borde, sombra y su etiqueta repetida ("Duración",
 * "Distancia") en cada fila. Con 40 actividades eso son 40 contenedores
 * y 80 etiquetas para 80 cifras: la auditoría lo señaló como la fuente
 * principal de ruido de la pantalla de Entrenamiento.
 *
 * Aquí el contenedor es UNO, las cabeceras se escriben UNA vez, las
 * filas se separan con una línea de 1px y las cifras van a la derecha
 * con `tabular-nums` para que las unidades y los decimales queden
 * alineados en columna (que es lo que permite comparar de un vistazo).
 *
 * El contenedor conserva un scroll horizontal como ÚLTIMO recurso (una
 * tabla de 5 columnas a 390px puede no caber de ninguna forma), pero la
 * primera línea de defensa es dejar que las celdas de texto largo se
 * partan en dos líneas (`envolver` en `Td`): en la auditoría a 390px la
 * cabecera "DISTANCIA" quedaba medio fuera del borde de la tarjeta, y
 * aunque técnicamente fuese scroll y no recorte, se leía como texto
 * cortado - exactamente la queja del usuario. Partir una línea no es
 * cortarla (doctrina 4).
 */
export function Table({
  cabeceras,
  children,
  etiqueta,
}: {
  /** `numerica` alinea a la derecha toda la columna, cabecera incluida. */
  cabeceras: readonly { clave: string; label: string; numerica?: boolean }[];
  children: ReactNode;
  /** Nombre accesible de la tabla (`<caption>` visualmente oculto). */
  etiqueta: string;
}) {
  return (
    <div className="-mx-5 overflow-x-auto px-5">
      <table className="w-full border-collapse">
        <caption className="sr-only">{etiqueta}</caption>
        <thead>
          <tr className="border-b border-line">
            {cabeceras.map((c) => (
              <th
                key={c.clave}
                scope="col"
                // `pr-4 last:pr-0` igual que las celdas: sin esto las
                // cabeceras no tenían separación ninguna y a 390px se
                // leían pegadas, "DURACIÓN DISTANCIA FC MEDIA" como una
                // sola palabra. Era la queja de texto cortado del
                // usuario aunque el texto estuviera entero.
                className={`t-micro whitespace-nowrap pb-2 pr-4 text-ink-3 last:pr-0 ${
                  c.numerica ? "text-right" : "text-left"
                }`}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}

/** Celda de texto. `secundaria` para lo que acompaña (fecha, nota);
 *  `envolver` para la columna de texto libre, que es la que debe ceder
 *  ancho partiéndose en dos líneas cuando la tabla no cabe. */
export function Td({
  children,
  secundaria = false,
  envolver = false,
  className = "",
}: {
  children: ReactNode;
  secundaria?: boolean;
  envolver?: boolean;
  className?: string;
}) {
  return (
    <td
      className={`py-3 pr-4 align-top last:pr-0 ${envolver ? "text-pretty" : "whitespace-nowrap"} ${
        secundaria ? "t-secondary text-ink-3" : "t-body text-ink"
      } ${className}`}
    >
      {children}
    </td>
  );
}

/**
 * Celda numérica: derecha + `tabular-nums`.
 *
 * `children` nulo se renderiza como "—" y NO como 0 (doctrina 6, "lo
 * desconocido no es cero"): la auditoría encontró "0.0 km" en cada
 * sesión de fuerza, que hacía parecer que el usuario había recorrido
 * cero kilómetros cuando lo que ocurre es que la distancia no aplica.
 */
export function TdNum({
  children,
  clase = "text-ink",
}: {
  children: ReactNode;
  /** Tinta de la cifra cuando la cifra ES un estado: el desglose del
   *  semáforo de recuperación colorea el valor de cada señal con su
   *  estado (doctrina 1: ahí el color es el dato, no adorno). Por
   *  defecto, tinta normal. */
  clase?: string;
}) {
  const vacia = children === null || children === undefined || children === "";
  return (
    // `align-top` para que la cifra quede a la altura de la PRIMERA
    // línea de la celda de texto: cuando esa celda lleva dos líneas
    // (nombre de la sesión y su fecha debajo), centrada verticalmente la
    // cifra flotaba entre las dos y no se sabía a cuál pertenecía.
    <td className="tabular whitespace-nowrap py-3 pr-4 text-right align-top last:pr-0">
      {vacia ? (
        <span className="t-body text-ink-3" aria-label="sin dato">
          —
        </span>
      ) : (
        <span className={`t-body ${clase}`}>{children}</span>
      )}
    </td>
  );
}
