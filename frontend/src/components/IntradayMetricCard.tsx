"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, todayLocalDate, type GarminIntradayMetrica } from "@/lib/api";
import { plural } from "@/lib/fechas";
import { SERIES_INTRADIA } from "@/lib/metricasSalud";
import { TrendChart } from "./ui/TrendChart";
import { SegmentedControl } from "./ui/SegmentedControl";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";


/**
 * Serie minuto a minuto del día en curso. Petición explícita del
 * usuario: "el ritmo cardiaco, body battery, etc son valores que
 * cambian cada minuto, quiero todo ese histórico, no me vale que cojas
 * la media del día".
 *
 * v3: un solo color de datos (antes rojo/azul/violeta según la
 * pestaña - color decorativo, porque las tres series son igual de
 * neutras), unidad correcta en el pulso (" ppm", no " bpm", que es la
 * sigla inglesa) y el recuento de puntos con su plural resuelto.
 *
 * Vive en "Hoy": es la única gráfica de la app cuyo eje es el día en
 * curso, así que responde a la pregunta de esa página ("cómo estoy hoy")
 * y no a la de Entrenamiento › Recuperación ("cómo ha ido el mes"),
 * donde estaba antes. Desde ella se llega al histórico de la misma
 * métrica, que es lo que uno quiere después de ver la forma del día.
 *
 * Las tres series, con su nombre, su unidad y su rango, salen de
 * `SERIES_INTRADIA` (el catálogo de métricas) y no de una lista propia:
 * la copia local era la que podía decir " bpm" donde el resto de la app
 * dice " ppm".
 *
 * Si el scheduler todavía no ha sincronizado la serie de hoy se dice
 * así, en vez de dibujar una gráfica vacía.
 */
export function IntradayMetricCard({ userId }: { userId: number }) {
  const [metrica, setMetrica] = useState<GarminIntradayMetrica>(SERIES_INTRADIA[0].serie);
  const [puntos, setPuntos] = useState<{ timestamp_utc: string; valor: number }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminIntradayHistory(userId, metrica, todayLocalDate())
      .then((datos) => {
        if (cancelado) return;
        setPuntos(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setPuntos(null);
        setError(err instanceof ApiError ? err.message : "No se pudo cargar la serie de hoy.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, metrica, intentos]);

  const serieActiva = SERIES_INTRADIA.find((s) => s.serie === metrica)!;
  const datosGrafica = (puntos ?? []).map((p) => ({ fecha: p.timestamp_utc, valor: p.valor }));

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <h2 className="t-section text-ink">Minuto a minuto de hoy</h2>
        <SegmentedControl
          options={SERIES_INTRADIA.map(({ serie, nombreSerie }) => ({
            value: serie,
            label: nombreSerie,
          }))}
          value={metrica}
          onChange={setMetrica}
          ariaLabel="Métrica intradía"
        />
      </div>

      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && puntos === null && <LoadingState lines={3} />}
      {!error && puntos !== null && puntos.length === 0 && (
        <EmptyState message="Garmin todavía no ha sincronizado la serie de hoy. Suele llegar tras la primera sincronización del reloj del día." />
      )}
      {!error && puntos !== null && puntos.length > 0 && (
        <div className="flex flex-col gap-2">
          <TrendChart
            data={datosGrafica}
            unidad={serieActiva.metrica.unidad}
            decimales={0}
            rango={serieActiva.metrica.rango}
            etiqueta={serieActiva.nombreSerie}
            alto={170}
            formatoEjeX="hora"
          />
          <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <p className="t-secondary text-ink-3">
              {serieActiva.leyenda}.{" "}
              {plural(puntos.length, "medición registrada hoy", "mediciones registradas hoy")}.
            </p>
            {/* La forma del día lleva a los días anteriores: sin este
                enlace, la gráfica se acababa en sí misma y comparar con
                ayer exigía volver a "Hoy" y pulsar la cifra. */}
            <Link
              href={`/salud/${serieActiva.metrica.slug}`}
              className="t-secondary text-ink-2 underline underline-offset-4 hover:text-ink"
            >
              Ver los días anteriores
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
}
