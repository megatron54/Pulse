"use client";

import { useEffect, useState } from "react";
import { Activity, BatteryCharging, Heart, HeartPulse, Moon, Wind } from "lucide-react";
import { api, ApiError, type GarminHealthDay } from "@/lib/api";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { StatTile } from "./ui/StatTile";

/**
 * Rail de tiles con el valor de HOY de cada métrica de recovery
 * (mismo patrón que el hero de "Hoy" en `RecoveryStatusCard`, pero con
 * las 6 métricas completas que sí caben en el detalle de
 * "Recuperación": VFC, Body Battery, sueño, estrés, pulso en reposo y
 * VO2max). El detalle intradía vive debajo en `IntradayMetricCard`, y
 * el histórico completo en `GarminHealthHistoryCard` - este rail es
 * solo el resumen "de un vistazo" antes de esos dos detalles.
 */
export function HealthMetricsSummaryRow({ userId }: { userId: number }) {
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthHistory(userId, 1)
      .then((datos) => {
        if (cancelado) return;
        setHistorial(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar tu estado de hoy.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          setError(null);
          setIntentos((n) => n + 1);
        }}
      />
    );
  }

  if (historial === null) return <LoadingState lines={1} />;

  const diaHoy = historial.at(-1) ?? null;
  // "unknown is not zero": sin ningún dato de hoy todavía (el
  // scheduler nocturno no ha sincronizado), no se muestra el rail en
  // absoluto - el histórico de abajo sigue disponible igualmente.
  if (!diaHoy) return null;

  return (
    <div className="scroll-rail -mx-1 flex gap-3 px-1">
      {diaHoy.hrv_value != null && (
        <StatTile icon={HeartPulse} label="VFC" value={diaHoy.hrv_value} unit=" ms" />
      )}
      {diaHoy.body_battery_am != null && (
        <StatTile icon={BatteryCharging} label="Body Battery" value={diaHoy.body_battery_am} />
      )}
      {diaHoy.sleep_score != null && <StatTile icon={Moon} label="Sueño" value={diaHoy.sleep_score} />}
      {diaHoy.stress_avg != null && <StatTile icon={Activity} label="Estrés" value={diaHoy.stress_avg} />}
      {diaHoy.resting_hr != null && (
        <StatTile icon={Heart} label="FC reposo" value={diaHoy.resting_hr} unit=" ppm" />
      )}
      {diaHoy.vo2max != null && <StatTile icon={Wind} label="VO2max" value={diaHoy.vo2max} />}
    </div>
  );
}
