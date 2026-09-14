"use client";

import { useEffect, useState } from "react";
import { api, ApiError, todayLocalDate, type GarminIntradayMetrica } from "@/lib/api";
import { plural } from "@/lib/fechas";
import { TrendChart } from "./ui/TrendChart";
import { SegmentedControl } from "./ui/SegmentedControl";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

const PESTANAS: readonly {
  valor: GarminIntradayMetrica;
  label: string;
  etiquetaSerie: string;
  unidad: string;
  /** Límites físicos de la métrica: el eje no debe rotular un Body
   *  Battery de 102 ni un estrés negativo. El pulso no los lleva - no
   *  hay un techo que tenga sentido dibujar. */
  rango?: readonly [number, number];
}[] = [
  { valor: "heart_rate", label: "Pulso", etiquetaSerie: "Pulso", unidad: " ppm" },
  { valor: "body_battery", label: "Body Battery", etiquetaSerie: "Body Battery", unidad: "", rango: [0, 100] },
  { valor: "stress", label: "Estrés", etiquetaSerie: "Estrés", unidad: "", rango: [0, 100] },
];

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
 * Si el scheduler todavía no ha sincronizado la serie de hoy se dice
 * así, en vez de dibujar una gráfica vacía.
 */
export function IntradayMetricCard({ userId }: { userId: number }) {
  const [metrica, setMetrica] = useState<GarminIntradayMetrica>("heart_rate");
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

  const pestanaActiva = PESTANAS.find((p) => p.valor === metrica)!;
  const datosGrafica = (puntos ?? []).map((p) => ({ fecha: p.timestamp_utc, valor: p.valor }));

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <h2 className="t-section text-ink">Minuto a minuto de hoy</h2>
        <SegmentedControl
          options={PESTANAS.map(({ valor, label }) => ({ value: valor, label }))}
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
            unidad={pestanaActiva.unidad}
            decimales={0}
            rango={pestanaActiva.rango}
            etiqueta={pestanaActiva.etiquetaSerie}
            alto={170}
            formatoEjeX="hora"
          />
          <p className="t-secondary text-ink-3">
            {plural(puntos.length, "medición registrada hoy", "mediciones registradas hoy")}.
          </p>
        </div>
      )}
    </Card>
  );
}
