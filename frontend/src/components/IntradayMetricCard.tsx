"use client";

import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { api, ApiError, todayLocalDate, type GarminIntradayMetrica } from "@/lib/api";
import { AreaTrendChart } from "./ui/AreaTrendChart";
import { SegmentedControl } from "./ui/SegmentedControl";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { PALETA } from "@/lib/theme";

const PESTANAS: { valor: GarminIntradayMetrica; label: string; color: string; unidad: string }[] = [
  { valor: "heart_rate", label: "Ritmo cardíaco", color: PALETA.recoveryLow, unidad: " bpm" },
  { valor: "body_battery", label: "Body Battery", color: PALETA.accent, unidad: "" },
  { valor: "stress", label: "Estrés", color: PALETA.sleep, unidad: "" },
];

/**
 * Serie minuto a minuto de un día (petición explícita del usuario:
 * "el ritmo cardiaco, body battery, etc son valores que cambian cada
 * minuto, quiero todo ese histórico, no me vale que cojas la media
 * del día"). Complementa a `GarminHealthHistoryCard` (que muestra UN
 * valor agregado por día) con el detalle real dentro de un día.
 *
 * "Unknown is not zero": si el scheduler todavía no ha sincronizado
 * la serie de ese día (o Garmin no tenía suficientes datos), se
 * comunica honestamente en vez de mostrar una gráfica vacía sin
 * explicación.
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
      <CardTitle>Minuto a minuto (hoy)</CardTitle>
      <div className="mb-4">
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
        <EmptyState
          icon={Activity}
          message="Todavía no hay datos minuto a minuto sincronizados hoy."
        />
      )}
      {!error && puntos !== null && puntos.length > 0 && (
        <div className="flex flex-col gap-2">
          <AreaTrendChart
            data={datosGrafica}
            color={pestanaActiva.color}
            unidad={pestanaActiva.unidad}
            alto={140}
            decimales={0}
          />
          <p className="text-xs text-text-secondary">{puntos.length} puntos hoy</p>
        </div>
      )}
    </Card>
  );
}
