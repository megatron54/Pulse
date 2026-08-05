"use client";

import { useEffect, useState } from "react";
import { Scale } from "lucide-react";
import { api, ApiError, type BodyMeasurement } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { AreaTrendChart } from "./ui/AreaTrendChart";
import { AnimatedNumber } from "./ui/AnimatedNumber";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { PALETA } from "@/lib/theme";

/**
 * Dashboard de tendencia de peso (Fase I del plan autónomo) sobre
 * `GET /body-measurements/history`, que devuelve TODAS las filas de
 * cada día sin agregar (append-only). Se agrega aquí con
 * `dedupeUltimaPorDia` - ver ese módulo para el criterio exacto.
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

  useEffect(() => {
    let cancelado = false;
    api
      .getBodyMeasurementHistory(userId, 90)
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

  const diario = mediciones ? dedupeUltimaPorDia(mediciones) : [];
  const ultimo = diario.at(-1);

  return (
    <Card>
      <CardTitle>Tendencia de peso (90 días)</CardTitle>
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && mediciones === null && <LoadingState lines={1} />}
      {!error && mediciones !== null && diario.length === 0 && (
        <EmptyState icon={Scale} message="Todavía no hay mediciones registradas." />
      )}
      {!error && diario.length > 0 && (
        <>
          <p className="text-sm text-gray-400 mb-2">
            Último registro:{" "}
            <span className="font-display text-lg text-white">
              <AnimatedNumber value={ultimo?.peso_kg ?? 0} decimals={1} /> kg
            </span>{" "}
            ({diario.length} días con dato)
          </p>
          <AreaTrendChart
            data={diario.map((m) => ({ fecha: m.fecha, valor: m.peso_kg }))}
            color={PALETA.teal}
            unidad=" kg"
          />
        </>
      )}
    </Card>
  );
}
