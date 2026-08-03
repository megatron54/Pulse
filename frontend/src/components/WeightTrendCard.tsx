"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type BodyMeasurement } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { Sparkline } from "./Sparkline";

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
  }, [userId, refreshKey]);

  const diario = mediciones ? dedupeUltimaPorDia(mediciones) : [];
  const ultimo = diario.at(-1);

  return (
    <div className="border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Tendencia de peso (90 días)</h2>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!error && mediciones !== null && diario.length === 0 && (
        <p className="text-sm text-gray-400 italic">
          Todavía no hay mediciones registradas.
        </p>
      )}
      {!error && diario.length > 0 && (
        <>
          <Sparkline
            values={diario.map((m) => m.peso_kg)}
            label={`Tendencia de peso, ${diario.length} días, último registro ${ultimo?.peso_kg.toFixed(1)} kg`}
          />
          <p className="text-sm text-gray-500 mt-2">
            Último registro: {ultimo?.peso_kg.toFixed(1)} kg ({diario.length} días con
            dato)
          </p>
        </>
      )}
    </div>
  );
}
