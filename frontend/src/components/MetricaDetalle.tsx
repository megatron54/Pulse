"use client";

import { Fragment, useEffect, useState } from "react";
import {
  api,
  ApiError,
  type GarminHealthDay,
  type GarminIntradayPoint,
  type GarminIntradayMetrica,
} from "@/lib/api";
import { fechaCorta, fechaRelativa, plural } from "@/lib/fechas";
import type { MetricaSalud } from "@/lib/metricasSalud";
import { formatNumero } from "@/lib/numeros";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { FasesSueno, horasYMinutos, segundosDormidos, tieneFases } from "./ui/FasesSueno";
import { LoadingState } from "./ui/LoadingState";
import { SegmentedControl } from "./ui/SegmentedControl";
import { Table, Td, TdNum } from "./ui/Table";
import { TrendChart } from "./ui/TrendChart";

const VENTANAS = [
  { dias: 7, label: "7 días" },
  { dias: 30, label: "30 días" },
  { dias: 90, label: "90 días" },
] as const;

type Dias = (typeof VENTANAS)[number]["dias"];

/**
 * Las formas del sustantivo con el que se nombra un registro. Existe
 * porque el género no se puede derivar de la palabra sin una regla que
 * falle: la primera versión componía "Pulsa una ${nombre}" y en las
 * métricas diarias salía "Pulsa una día" (visible en la captura de
 * verificación). Con las formas escritas, la concordancia no depende de
 * que nadie se acuerde.
 */
const PALABRAS = {
  noche: {
    columna: "Noche",
    titulo: "Noche a noche",
    invitacion: "Pulsa una noche",
    singular: "noche",
    plural: "noches",
    posesivo: "de la noche",
  },
  "día": {
    columna: "Día",
    titulo: "Día a día",
    invitacion: "Pulsa un día",
    singular: "día",
    plural: "días",
    posesivo: "del día",
  },
} as const;

/** Desviación mínima frente a la media para decir que el último dato se
 *  sale de lo normal. Sin un mínimo, "1 ms por encima de tu media"
 *  saldría teñido de verde cada día que el ruido de la medición apunte
 *  hacia arriba, y el color dejaría de significar nada (doctrina 1). */
const DESVIACION_RELEVANTE = 0.05;

/**
 * Detalle de una métrica del reloj: la pantalla a la que se llega
 * pulsando una cifra en "Hoy".
 *
 * Existe por una petición literal del usuario: *"me gustaría poder
 * pulsar en la puntuación de sueño y ver el detalle de mi noche, o de
 * las otras noches que ha registrado el reloj. Igual con el body
 * battery, la VFC, el estrés, el pulso en reposo, los pasos"*. Hasta
 * ahora la cifra del día era un callejón sin salida: se veía el 72 y no
 * había forma de saber si 72 era bueno, ni qué pasó esa noche, ni cómo
 * venía la semana.
 *
 * Responde tres preguntas, en este orden:
 *
 *  1. **¿Cómo voy?** La última cifra, de cuándo es, y cuánto se sale de
 *     tu propia media de la ventana - que es la única referencia
 *     honesta cuando la métrica no tiene un umbral universal (una VFC
 *     de 40 ms puede ser excelente o mala según la persona).
 *  2. **¿Qué forma tiene?** La tendencia, con eje, unidad y los huecos
 *     dibujados como huecos (doctrina 5).
 *  3. **¿Qué pasó un día concreto?** La tabla de registros, y al pulsar
 *     uno, lo que el reloj guardó de ese día: las fases de esa noche o
 *     su serie minuto a minuto. Sin esto la pantalla repetiría la misma
 *     cifra en tres tamaños distintos.
 */
export function MetricaDetalle({
  userId,
  metrica,
}: {
  userId: number;
  metrica: MetricaSalud;
}) {
  const [dias, setDias] = useState<Dias>(30);
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);
  /** Fecha del registro desplegado, o `null` si no hay ninguno. Uno
   *  solo: dos detalles abiertos a la vez separan la fila de su propio
   *  contenido y se pierde de quién es cada cosa. */
  const [abierto, setAbierto] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthHistory(userId, dias)
      .then((datos) => {
        if (cancelado) return;
        setHistorial(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError
            ? err.message
            : `No se pudo cargar el historial de ${metrica.titulo.toLowerCase()}.`
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, dias, intentos, metrica.titulo]);

  const { campo, unidad, decimales } = metrica;
  const palabras = PALABRAS[metrica.nombreDelRegistro];
  // Solo los registros en los que esta métrica existe: un día sin dato
  // no es un día a cero, así que no entra ni en la gráfica, ni en la
  // media, ni en la tabla (doctrina 6).
  const conDato = (historial ?? [])
    .filter((d) => d[campo] != null)
    .map((d) => ({ dia: d, valor: d[campo] as number }));
  // La gráfica necesita orden ascendente; la tabla, el último arriba,
  // que es por donde se empieza a leer.
  const ascendente = [...conDato].sort((a, b) => a.dia.fecha.localeCompare(b.dia.fecha));
  const descendente = [...ascendente].reverse();

  const selector = (
    <SegmentedControl
      options={VENTANAS.map((v) => ({ value: String(v.dias), label: v.label }))}
      value={String(dias)}
      onChange={(v) => {
        setDias(Number(v) as Dias);
        // La fila desplegada puede no existir en la ventana nueva: si se
        // queda abierta, el detalle sobrevive a su fila y se lee como el
        // detalle de otro día.
        setAbierto(null);
      }}
      ariaLabel="Ventana temporal"
    />
  );

  if (error) {
    return (
      <div className="flex flex-col gap-5">
        <Card>
          <div className="mb-4 flex justify-end">{selector}</div>
          <ErrorState
            message={error}
            onRetry={() => {
              setError(null);
              setIntentos((n) => n + 1);
            }}
          />
        </Card>
      </div>
    );
  }

  if (historial === null) {
    return (
      <Card>
        <div className="mb-4 flex justify-end">{selector}</div>
        <LoadingState lines={5} />
      </Card>
    );
  }

  if (ascendente.length === 0) {
    return (
      <Card>
        <div className="mb-4 flex justify-end">{selector}</div>
        <EmptyState
          message={`El reloj no ha registrado ${metrica.titulo.toLowerCase()} en esta ventana. Prueba con un rango más amplio, y si sigue vacío comprueba la conexión en Perfil › Conexiones.`}
        />
        <p className="t-secondary mt-4 max-w-prose text-pretty text-ink-2">
          {metrica.explicacion}
        </p>
      </Card>
    );
  }

  const ultimo = ascendente[ascendente.length - 1];
  const valores = ascendente.map((r) => r.valor);
  const media = valores.reduce((a, b) => a + b, 0) / valores.length;
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);

  const cifra = (valor: number) => `${formatNumero(valor, decimales)}${unidad}`;

  return (
    <div className="flex flex-col gap-5">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
          <div>
            {/* El espacio entre la cifra y su fecha es un espacio de
                verdad y no un margen: un lector de pantalla lee el
                texto, y con solo margen decía "ochenta y ocho hoy"
                pegado. */}
            <p className="t-hero text-ink">
              {cifra(ultimo.valor)}{" "}
              <span className="t-secondary text-ink-3">
                {fechaRelativa(ultimo.dia.fecha).toLowerCase()}
              </span>
            </p>
            <p className="t-body mt-2">
              <ComparacionConLaMedia metrica={metrica} valor={ultimo.valor} media={media} dias={dias} />
            </p>
          </div>
          {selector}
        </div>

        <p className="t-secondary mt-4 max-w-prose text-pretty text-ink-2">{metrica.explicacion}</p>

        {/* Con un solo registro no hay tendencia que dibujar: la cifra
            de arriba ya lo dice todo y una gráfica de un punto es una
            gráfica vacía con un lunar. */}
        {ascendente.length >= 2 && (
          <div className="mt-5">
            <TrendChart
              data={ascendente.map((r) => ({ fecha: r.dia.fecha, valor: r.valor }))}
              unidad={unidad}
              decimales={decimales}
              rango={metrica.rango}
              etiqueta={metrica.titulo}
              alto={200}
            />
          </div>
        )}

        <dl className="mt-5 grid grid-cols-[repeat(auto-fit,minmax(7rem,1fr))] gap-x-6 gap-y-3 border-t border-line pt-4">
          <Resumen etiqueta={`Media de ${dias} días`} valor={cifra(media)} />
          <Resumen etiqueta="Mínimo" valor={cifra(minimo)} />
          <Resumen etiqueta="Máximo" valor={cifra(maximo)} />
          <Resumen
            etiqueta="Registros"
            valor={plural(ascendente.length, palabras.singular, palabras.plural)}
          />
        </dl>
      </Card>

      <Card plano>
        <div className="p-5 pb-2">
          <h2 className="t-section text-ink">
            {palabras.titulo}
          </h2>
          <p className="t-secondary mt-1 text-pretty text-ink-3">
            {metrica.detalleDelRegistro
              ? `${palabras.invitacion} para ver lo que guardó el reloj.`
              : `Todo lo que el reloj ha registrado en estos ${dias} días.`}
          </p>
        </div>
        <div className="px-5 pb-1">
          <TablaRegistros
            userId={userId}
            metrica={metrica}
            registros={descendente}
            abierto={abierto}
            onAbrir={(fecha) => setAbierto((actual) => (actual === fecha ? null : fecha))}
          />
        </div>
      </Card>
    </div>
  );
}

function Resumen({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="t-micro text-ink-3">{etiqueta}</dt>
      <dd className="t-body tabular text-ink">{valor}</dd>
    </div>
  );
}

/** "8 ms por encima de tu media de 30 días", teñido según si eso es
 *  bueno o malo para ESTA métrica: más estrés no es lo mismo que más
 *  VFC, y una cifra sola nunca dice si subir está bien. */
function ComparacionConLaMedia({
  metrica,
  valor,
  media,
  dias,
}: {
  metrica: MetricaSalud;
  valor: number;
  media: number;
  dias: number;
}) {
  const diferencia = valor - media;
  const relevante =
    media !== 0 && Math.abs(diferencia) / Math.abs(media) >= DESVIACION_RELEVANTE;

  if (!relevante) {
    return <span className="text-ink-2">En tu media de los últimos {dias} días.</span>;
  }

  const arriba = diferencia > 0;
  const bueno = arriba === (metrica.mejorHacia === "arriba");
  return (
    <span className={bueno ? "text-pos" : "text-neg"}>
      {formatNumero(Math.abs(diferencia), metrica.decimales)}
      {metrica.unidad} por {arriba ? "encima" : "debajo"} de tu media de {dias} días.
    </span>
  );
}

/**
 * Los registros de la ventana, y bajo el que esté desplegado, lo que el
 * reloj guardó de ese día.
 *
 * El detalle se abre DENTRO de la tabla, en una fila propia pegada a la
 * que se ha pulsado, y no en un bloque fijo arriba: con 90 filas, un
 * bloque arriba obliga a subir a ver el efecto de cada clic y a bajar a
 * probar otro día.
 */
function TablaRegistros({
  userId,
  metrica,
  registros,
  abierto,
  onAbrir,
}: {
  userId: number;
  metrica: MetricaSalud;
  registros: readonly { dia: GarminHealthDay; valor: number }[];
  abierto: string | null;
  onAbrir: (fecha: string) => void;
}) {
  const conFases = metrica.detalleDelRegistro?.tipo === "fases-sueno";
  const cabeceras = [
    { clave: "fecha", label: PALABRAS[metrica.nombreDelRegistro].columna },
    { clave: "valor", label: metrica.tituloCorto, numerica: true },
    ...(conFases ? [{ clave: "dormido", label: "Dormido", numerica: true }] : []),
  ];
  const columnas = cabeceras.length;

  return (
    <Table cabeceras={cabeceras} etiqueta={`${metrica.titulo}, registro a registro`}>
      {registros.map(({ dia, valor }) => {
        const estaAbierto = abierto === dia.fecha;
        const dormido = segundosDormidos(dia);
        return (
          <Fragment key={dia.fecha}>
            <tr className={estaAbierto ? "bg-canvas" : undefined}>
              <Td>
                {metrica.detalleDelRegistro ? (
                  <button
                    type="button"
                    onClick={() => onAbrir(dia.fecha)}
                    aria-expanded={estaAbierto}
                    className="rounded underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
                  >
                    {fechaRelativa(dia.fecha)}
                    <span className="sr-only">
                      {`, ver el detalle ${
                        PALABRAS[metrica.nombreDelRegistro].posesivo
                      } del ${fechaCorta(dia.fecha)}`}
                    </span>
                  </button>
                ) : (
                  fechaRelativa(dia.fecha)
                )}
              </Td>
              <TdNum>{`${formatNumero(valor, metrica.decimales)}${metrica.unidad}`}</TdNum>
              {conFases && <TdNum>{dormido > 0 ? horasYMinutos(dormido) : null}</TdNum>}
            </tr>
            {estaAbierto && (
              <tr className="bg-canvas">
                <td colSpan={columnas} className="px-0 pb-4 pt-1">
                  {/* Ancho acotado (y no en el `<td>`, que en una tabla
                      lo ignora): a 1280px el desplegable ocupaba los
                      950px de la tabla y la leyenda de fases quedaba con
                      el nombre a la izquierda y su cifra a 600px, sin
                      forma de emparejarlos de un vistazo.
                      El rótulo dice de qué día es y qué se está mirando:
                      sin él, una barra suelta bajo una tabla de treinta
                      filas no se sabe de quién es. */}
                  <div className="max-w-[42rem]">
                    <p className="t-micro mb-3 text-ink-3">
                      {metrica.detalleDelRegistro?.tipo === "fases-sueno"
                        ? `Fases de la noche del ${fechaCorta(dia.fecha)}`
                        : `${metrica.detalleDelRegistro?.leyenda} del ${fechaCorta(dia.fecha)}`}
                    </p>
                    <DetalleDelDia userId={userId} metrica={metrica} dia={dia} />
                  </div>
                </td>
              </tr>
            )}
          </Fragment>
        );
      })}
    </Table>
  );
}

/** Lo que el reloj guardó de un día: las fases de esa noche, o su serie
 *  minuto a minuto. Ambas cosas son datos reales del reloj, no un
 *  resumen calculado aquí. */
function DetalleDelDia({
  userId,
  metrica,
  dia,
}: {
  userId: number;
  metrica: MetricaSalud;
  dia: GarminHealthDay;
}) {
  const detalle = metrica.detalleDelRegistro;
  if (!detalle) return null;

  if (detalle.tipo === "fases-sueno") {
    if (!tieneFases(dia)) {
      return (
        <p className="t-secondary text-pretty text-ink-3">
          Esa noche el reloj registró la puntuación pero no las fases. Suele pasar cuando se
          quita el reloj parte de la noche.
        </p>
      );
    }
    return <FasesSueno dia={dia} />;
  }

  return <SerieDelDia userId={userId} serie={detalle.serie} metrica={metrica} fecha={dia.fecha} />;
}

function SerieDelDia({
  userId,
  serie,
  metrica,
  fecha,
}: {
  userId: number;
  serie: GarminIntradayMetrica;
  metrica: MetricaSalud;
  fecha: string;
}) {
  const [puntos, setPuntos] = useState<GarminIntradayPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sin reinicio de estado al empezar: este bloque se monta y se
  // desmonta con la fila desplegada (solo hay una abierta a la vez), así
  // que nace siempre "cargando" y nunca hereda la serie de otro día.
  useEffect(() => {
    let cancelado = false;
    api
      .getGarminIntradayHistory(userId, serie, fecha)
      .then((datos) => {
        if (!cancelado) setPuntos(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar la serie de ese día."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, serie, fecha]);

  if (error) return <p className="t-secondary text-pretty text-ink-3">{error}</p>;
  if (puntos === null) return <LoadingState lines={2} />;
  if (puntos.length === 0) {
    return (
      <p className="t-secondary text-pretty text-ink-3">
        El reloj no guardó la serie minuto a minuto de ese día. El valor diario sigue siendo
        válido: es lo único que Garmin conserva pasado un tiempo.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <TrendChart
        data={puntos.map((p) => ({ fecha: p.timestamp_utc, valor: p.valor }))}
        unidad={metrica.unidad}
        decimales={0}
        rango={metrica.rango}
        etiqueta={`${metrica.titulo}, ${fechaCorta(fecha)}`}
        alto={170}
        formatoEjeX="hora"
      />
      <p className="t-secondary text-ink-3">
        {plural(puntos.length, "medición ese día", "mediciones ese día")}.
      </p>
    </div>
  );
}
