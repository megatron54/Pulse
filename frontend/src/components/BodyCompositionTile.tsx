"use client";

import { useEffect, useState } from "react";
import { Bone, Droplet, Dumbbell, Percent, Ruler } from "lucide-react";
import { api, ApiError, type BodyMeasurement } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { Card, CardTitle } from "./ui/Card";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { StatTile } from "./ui/StatTile";

/**
 * Composición completa de bioimpedancia (báscula Feelfit): antes se
 * descartaba todo salvo peso y % de grasa (ver services/
 * feelfit_sync_service.py), pese a que la báscula la reporta en cada
 * medición. Solo se muestra si el registro más reciente trae al menos
 * un campo de composición - "unknown is not zero", una medición manual
 * de solo peso no debe mostrar un tile vacío.
 */
export function BodyCompositionTile({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  /** Ver docstring de `ReadinessTrendCard` para el mismo patrón: el
   * padre incrementa esto tras guardar una medición nueva en el
   * formulario hermano. */
  refreshKey?: number;
}) {
  const [mediciones, setMediciones] = useState<BodyMeasurement[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getBodyMeasurementHistory(userId, 90)
      .then((datos) => {
        if (!cancelado) setMediciones(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar tu composición corporal."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey, intentos]);

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

  if (mediciones === null) return <LoadingState lines={1} />;

  const ultimo = dedupeUltimaPorDia(mediciones).at(-1);
  if (!ultimo) return null;

  const grasaEsRango =
    ultimo.bodyfat_pct_rango_min != null &&
    ultimo.bodyfat_pct_rango_max != null &&
    ultimo.bodyfat_pct_rango_min !== ultimo.bodyfat_pct_rango_max;

  const tieneComposicion =
    ultimo.bodyfat_pct_rango_min != null ||
    ultimo.muscle_kg != null ||
    ultimo.bone_kg != null ||
    ultimo.water_pct != null ||
    ultimo.bmi != null;
  if (!tieneComposicion) return null;

  return (
    <Card>
      <CardTitle>Composición corporal</CardTitle>
      <div className="scroll-rail -mx-1 mt-3 flex gap-3 px-1">
        {ultimo.bodyfat_pct_rango_min != null &&
          (grasaEsRango ? (
            <div className="flex min-w-[7.5rem] shrink-0 flex-col gap-1.5 rounded-xl border border-surface-border bg-surface px-4 py-3">
              <div className="flex items-center gap-1.5 text-text-secondary">
                <Percent aria-hidden="true" size={14} />
                <span className="text-xs font-medium uppercase tracking-wide">% Grasa</span>
              </div>
              <p className="text-xl font-semibold tabular-nums text-foreground">
                {ultimo.bodyfat_pct_rango_min.toFixed(1)}-{ultimo.bodyfat_pct_rango_max!.toFixed(1)}%
              </p>
            </div>
          ) : (
            <StatTile
              icon={Percent}
              label="% Grasa"
              value={ultimo.bodyfat_pct_rango_min}
              unit="%"
              decimals={1}
            />
          ))}
        {ultimo.muscle_kg != null && (
          <StatTile icon={Dumbbell} label="Músculo" value={ultimo.muscle_kg} unit=" kg" decimals={1} />
        )}
        {ultimo.bone_kg != null && (
          <StatTile icon={Bone} label="Hueso" value={ultimo.bone_kg} unit=" kg" decimals={1} />
        )}
        {ultimo.water_pct != null && (
          <StatTile icon={Droplet} label="Agua" value={ultimo.water_pct} unit="%" decimals={1} />
        )}
        {ultimo.bmi != null && <StatTile icon={Ruler} label="BMI" value={ultimo.bmi} decimals={1} />}
      </div>
    </Card>
  );
}
