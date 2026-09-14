import type { Signal } from "@/lib/api";
import { fechaRelativa, plural } from "@/lib/fechas";
import {
  CLASE_POR_ESTADO,
  COMO_AYUDARLO,
  ETIQUETA_SENAL,
  ORDEN_SENALES,
  etiquetaEstado,
  resumenDeSenales,
  senalesAAconsejar,
  textoReferencia,
  textoValor,
} from "@/lib/senalesRecuperacion";
import { Table, Td, TdNum } from "./ui/Table";

const CABECERAS_BASE = [
  { clave: "senal", label: "Señal" },
  { clave: "referencia", label: "Bien si es", numerica: true },
] as const;

/**
 * Por qué el semáforo dice lo que dice.
 *
 * Antes de esto, "Recuperación baja" en rojo grande era todo lo que la
 * aplicación contaba: seis cifras debajo, sin ninguna relación visible
 * con el veredicto, y ni una palabra sobre cuál de ellas lo había
 * decidido. El día que el usuario lo preguntó, la culpable era la
 * tendencia de VFC de 7 días - la única señal que no se dibujaba en
 * ninguna pantalla, con lo que la tarjeta parecía contradecirse sola
 * (VFC un 16 % POR ENCIMA de la media, veredicto rojo).
 *
 * Es una tabla de verdad y no una rejilla de tarjetitas (doctrina 3)
 * porque la pregunta es comparativa: el valor de hoy solo significa algo
 * al lado de su referencia, en la misma línea y en columna con el resto.
 *
 * Tres columnas y no cuatro: la columna "estado" sobraba, porque el
 * estado ya está dicho dos veces - por el color de la cifra y por la
 * comparación con la referencia de al lado, que es la pista que NO
 * depende del color (un `−19 %` frente a un `≥ −10 %` se lee igual en
 * escala de grises). Las dos señales que no tienen cifra escriben su
 * estado con palabras en la casilla del valor.
 */
export function DesgloseSenales({
  senales,
  fecha,
}: {
  senales: readonly Signal[];
  /** Fecha del cálculo, que titula la columna del valor. No se escribe
   *  "Hoy" a pelo: si el último veredicto es de ayer (el cálculo
   *  necesita el sueño y la VFC de la noche), la columna lo dice. */
  fecha: string;
}) {
  const filas = ORDEN_SENALES.map((codigo) => senales.find((s) => s.senal === codigo)).filter(
    (s): s is Signal => s !== undefined,
  );
  if (filas.length === 0) return null;

  const consejos = senalesAAconsejar(filas);
  const sinMedir = filas.filter((s) => s.estado === "unknown");
  const resumen = resumenDeSenales(filas);
  const cabeceras = [
    CABECERAS_BASE[0],
    { clave: "valor", label: fechaRelativa(fecha), numerica: true },
    CABECERAS_BASE[1],
  ];

  return (
    // Ancho acotado: a 1280px la tarjeta pasa de 950px y, sin límite, la
    // etiqueta de cada señal quedaba en el borde izquierdo con su cifra
    // en el derecho, medio metro de blanco en medio. Una fila de tabla
    // solo se lee como una fila si se abarca de un vistazo; y el párrafo
    // de explicación tampoco se lee bien a 900px de línea.
    <div className="flex max-w-[42rem] flex-col gap-4">
      <div>
        <h3 className="t-micro text-ink-3">Por qué</h3>
        <p className="t-secondary mt-2 text-pretty text-ink-2">
          {resumen ??
            "Ninguna de tus señales está por debajo de su referencia: por eso el veredicto es verde."}
        </p>
      </div>

      <Table cabeceras={cabeceras} etiqueta="Señales que deciden tu recuperación">
        {filas.map((senal) => (
          <tr key={senal.senal}>
            <Td envolver>{ETIQUETA_SENAL[senal.senal]}</Td>
            {/* `null` cuando la señal no se midió, para que `TdNum` la
                dibuje como "—" y no como un valor real (doctrina 6).
                Cuando sí hay estado pero no hay cifra (dolor articular,
                preparación del reloj), el estado ocupa la casilla. */}
            <TdNum clase={CLASE_POR_ESTADO[senal.estado]}>
              {senal.estado === "unknown" ? null : (textoValor(senal) ?? etiquetaEstado(senal))}
            </TdNum>
            <TdNum clase="text-ink-3">{textoReferencia(senal)}</TdNum>
          </tr>
        ))}
      </Table>

      {/* Qué hace un guion ahí. Sin esta línea, una señal sin medir se
          lee como una mala noticia oculta ("¿me está faltando algo que
          me perjudica?"), cuando lo que pasa es que queda fuera del
          cálculo: el motor no la cuenta como buena ni como mala. */}
      {sinMedir.length > 0 && (
        <p className="t-secondary text-pretty text-ink-3">
          {plural(sinMedir.length, "señal sin medir", "señales sin medir")}: el guion ni suma ni
          resta, el veredicto sale de las demás.
        </p>
      )}

      {consejos.length > 0 && (
        <div>
          <h3 className="t-micro text-ink-3">Cómo ayudarlo</h3>
          {/* Solo de las señales que hoy pesan, y como mucho tres (ver
              `senalesAAconsejar`): un consejo por cada una de las siete
              sería un muro de texto, y la mayoría hablaría de cosas que
              hoy están bien. */}
          <ul className="mt-2 flex flex-col gap-2">
            {consejos.map((senal) => (
              <li key={senal.senal} className="t-secondary text-pretty text-ink-2">
                {COMO_AYUDARLO[senal.senal]}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
