"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type BodyMeasurement } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { diasDesdeHoy, fechaCorta, fechaRelativa, plural } from "@/lib/fechas";
import { TrendChart } from "./ui/TrendChart";
import { Card } from "./ui/Card";
import { DataList, DataRow } from "./ui/DataList";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { SegmentedControl } from "./ui/SegmentedControl";

/**
 * Ventanas que el usuario puede pedir. "Todo" son 10 años de días: el
 * historial corporal es una fila por pesada, así que pedir una década
 * son unos pocos miles de filas en el peor caso - no hace falta un modo
 * "sin límite" en la API, que es lo que obliga a paginar.
 *
 * `cambio` es la etiqueta de la fila del delta, escrita para cada
 * ventana en vez de interpolar el número de días: "Cambio en 365 días"
 * se lee peor que "Cambio en 12 meses", y "Cambio en 3650 días" no se
 * lee en absoluto.
 */
const VENTANAS = [
  { value: "90d", label: "90 días", dias: 90, subtitulo: "Últimos 90 días.", cambio: "Cambio en 90 días" },
  { value: "1a", label: "1 año", dias: 365, subtitulo: "Últimos 12 meses.", cambio: "Cambio en 12 meses" },
  { value: "todo", label: "Todo", dias: 3650, subtitulo: "Todo tu historial.", cambio: "Cambio total" },
] as const;

type Ventana = (typeof VENTANAS)[number]["value"];

const OPCIONES = VENTANAS.map(({ value, label }) => ({ value, label }));

/** Se pide el historial completo una vez y las ventanas se recortan en
 *  el cliente: son unos cientos de filas, y así cambiar de ventana es
 *  instantáneo en vez de un viaje al servidor con su esqueleto de
 *  carga. */
const DIAS_MAXIMOS = VENTANAS[VENTANAS.length - 1].dias;

/** Ventana con la que abrir la tarjeta: la más corta que contenga al
 *  menos dos días con dato, o el historial completo si ninguna llega.
 *
 *  Antes abría siempre en 90 días y este usuario, con 275 pesadas
 *  importadas de Feelfit pero ninguna de los últimos dos meses, veía
 *  "Días con dato: 1 día" y ninguna gráfica: la ventana por defecto
 *  escondía años de datos detrás de un clic que nadie sabía que había
 *  que dar. La ventana se ancla a los datos, no al calendario. */
function ventanaPorDatos(diario: readonly { fecha: string }[]): Ventana {
  const suficientes = VENTANAS.find(
    (v) => diario.filter((m) => diasDesdeHoy(m.fecha) < v.dias).length >= 2
  );
  return suficientes?.value ?? "todo";
}

/**
 * Tendencia de peso (Cuerpo), sobre `GET /body-measurements/history`,
 * que devuelve TODAS las filas de cada día sin agregar (append-only).
 * Se agrega aquí con `dedupeUltimaPorDia` - ver ese módulo para el
 * criterio exacto.
 *
 * Rehecha para v3. Defectos concretos que tenía:
 *
 *  - "(1 días con dato)": plural sin resolver, en la primera línea de
 *    la primera tarjeta de la página. Ahora pasa por `plural()`.
 *  - Con una sola pesada dibujaba una gráfica: un punto no es una
 *    tendencia, y el área con dos vértices inventaba una pendiente que
 *    no existe. Ahora la gráfica necesita dos días con dato y, si no
 *    los hay, la tarjeta lo dice.
 *  - El número grande era el peso de hoy, que el usuario ya sabe porque
 *    acaba de pesarse. Lo que esta tarjeta puede contarle y él no sabe
 *    es el CAMBIO en la ventana, así que ese es el dato que ahora se
 *    escribe con signo explícito.
 *  - **La ventana era fija de 90 días.** Con 275 mediciones importadas
 *    de Feelfit (de 2024 a 2026), la tarjeta decía "Días con dato: 1
 *    día" y "Hace falta una segunda pesada" mientras Perfil presumía de
 *    275: el dato estaba en la base, la pantalla lo escondía. Ahora la
 *    ventana se elige, y cuando la elegida se queda corta la tarjeta
 *    ofrece ampliarla en vez de dar a entender que no hay historial.
 *  - **Y por defecto seguía abriendo en 90 días**, que para ese mismo
 *    historial es una ventana vacía: la tarjeta arrancaba muerta y
 *    dependía de que el usuario adivinara que el selector tenía algo
 *    detrás. Ahora abre en la ventana más corta que tenga datos de
 *    verdad (`ventanaPorDatos`), y el historial se pide entero una sola
 *    vez para que cambiar de ventana no recargue nada.
 */
export function WeightTrendCard({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  /** Al cambiar (p.ej. tras guardar una medición nueva en un formulario
   * hermano), fuerza a recargar el historial. Ver docstring de
   * `ReadinessTrendCard` para el mismo patrón - las tarjetas de
   * tendencia no saben por sí solas cuándo hay datos nuevos, así que el
   * padre (`page.tsx`) se lo comunica incrementando este valor. */
  refreshKey?: number;
}) {
  const [mediciones, setMediciones] = useState<BodyMeasurement[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);
  /** `null` = todavía no ha elegido: manda la ventana que sugieren los
   *  datos. En cuanto toca el selector, su elección se respeta aunque
   *  esté vacía (que la ventana esté vacía también es información). */
  const [ventanaElegida, setVentanaElegida] = useState<Ventana | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getBodyMeasurementHistory(userId, DIAS_MAXIMOS)
      .then((datos) => {
        if (!cancelado) setMediciones(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial de peso.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey, intentos]);

  // Orden explícito: el endpoint entrega cronológico ascendente, pero
  // `dedupeUltimaPorDia` devuelve el orden de inserción del Map y no
  // promete nada. La gráfica y el delta dependen del orden, así que se
  // ordena aquí en vez de confiar en él.
  const historial = mediciones
    ? dedupeUltimaPorDia(mediciones).sort((a, b) => a.fecha.localeCompare(b.fecha))
    : [];

  const ventana = ventanaElegida ?? ventanaPorDatos(historial);
  const rango = VENTANAS.find((v) => v.value === ventana) ?? VENTANAS[0];
  const diario = historial.filter((m) => diasDesdeHoy(m.fecha) < rango.dias);

  const encabezado = (
    <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div>
        <h2 className="t-section text-ink">Peso</h2>
        <p className="t-secondary mt-1 text-ink-3">{rango.subtitulo}</p>
      </div>
      <SegmentedControl
        options={OPCIONES}
        value={ventana}
        onChange={setVentanaElegida}
        ariaLabel="Ventana del historial de peso"
      />
    </div>
  );

  /** Botón para ampliar la ventana, cuando la elegida se queda corta.
   *  No se ofrece si ya estamos en "Todo" (ahí no hay nada que ampliar:
   *  el historial entero es lo que hay). */
  const botonVerTodo =
    ventana === "todo" ? undefined : (
      <button
        type="button"
        onClick={() => setVentanaElegida("todo")}
        className="t-body inline-flex min-h-11 items-center rounded-md border border-line px-4 text-ink hover:bg-canvas focus:outline-none focus-visible:ring-2 focus-visible:ring-ink"
      >
        Ver todo el historial
      </button>
    );

  if (error) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      </Card>
    );
  }

  if (mediciones === null) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <LoadingState lines={2} />
      </Card>
    );
  }

  if (diario.length === 0) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <EmptyState
          message={
            historial.length === 0
              ? "Todavía no hay mediciones registradas. Apunta tu peso en “Registrar medición” y aquí verás su evolución."
              : // Aquí sí se sabe que hay historial fuera de la ventana,
                // así que se dice cuándo fue en vez de insinuar un "puede
                // que" (doctrina 7: decir qué HACER, con el dato en la
                // mano).
                `Ninguna pesada en esta ventana: la última es del ${fechaCorta(
                  historial[historial.length - 1].fecha
                )}.`
          }
          accion={botonVerTodo}
        />
      </Card>
    );
  }

  const primera = diario[0];
  const ultima = diario[diario.length - 1];
  const delta = diario.length >= 2 ? ultima.peso_kg - primera.peso_kg : null;

  return (
    <Card plano>
      <div className="flex flex-col gap-5 p-5">
        {encabezado}

        <div>
          <p className="t-hero tabular text-ink">
            {ultima.peso_kg.toFixed(1)}
            <span className="t-body text-ink-2"> kg</span>
          </p>
          <p className="t-secondary mt-1 text-ink-3">{fechaRelativa(ultima.fecha)}</p>
        </div>

        <DataList>
          <DataRow
            label={rango.cambio}
            nota={
              delta === null
                ? undefined
                : `de ${primera.peso_kg.toFixed(1)} a ${ultima.peso_kg.toFixed(1)} kg`
            }
          >
            {delta === null ? (
              <span className="text-ink-3">
                {/* Corto a propósito: a 390px es el valor de una fila,
                    y el detalle ya lo da el botón de debajo. */}
                {ventana === "todo" ? "Hace falta una segunda pesada" : "Solo una pesada"}
              </span>
            ) : (
              // Signo explícito también en positivo: "0.4 kg" a secas no
              // dice si ha subido o bajado, y aquí el signo ES el dato.
              <span className="tabular">{`${delta > 0 ? "+" : delta < 0 ? "−" : ""}${Math.abs(delta).toFixed(1)} kg`}</span>
            )}
          </DataRow>
          <DataRow label="Días con dato">{plural(diario.length, "día", "días")}</DataRow>
        </DataList>

        {/* Con un solo día no hay tendencia que dibujar, y el motivo
            más probable no es que falten pesadas sino que la ventana no
            las alcanza (doctrina 7: decir qué HACER). */}
        {diario.length < 2 && botonVerTodo}
      </div>

      {diario.length >= 2 && (
        <div className="border-t border-line px-5 py-4">
          <TrendChart
            data={diario.map((m) => ({ fecha: m.fecha, valor: m.peso_kg }))}
            unidad=" kg"
            etiqueta="Peso"
          />
        </div>
      )}
    </Card>
  );
}
