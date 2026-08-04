"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type PeriodicSummary } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";

/**
 * Resumen semanal de tendencias (Épica MUST-HAVE #4 de 02-roadmap/
 * 03-vision-produccion.md): agregación pura sobre datos ya existentes
 * (readiness, carga de entrenamiento, peso, actividades Garmin), sin
 * ninguna integración nueva. Nunca fabrica un delta de peso con una
 * sola medición ni una tendencia de carga sin historial suficiente -
 * refleja los mismos flags de "unknown is not zero" que ya devuelve el
 * backend (`peso_delta_kg`/`training_load.datos_suficientes`).
 */
export function PeriodicSummaryCard({ userId }: { userId: number }) {
  const [resumen, setResumen] = useState<PeriodicSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getPeriodicSummary(userId)
      .then((datos) => {
        if (!cancelado) setResumen(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el resumen.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId]);

  return (
    <Card>
      <CardTitle>Resumen de la semana</CardTitle>
      {error && (
        <p role="alert" className="text-red-400 text-sm">
          {error}
        </p>
      )}
      {!error && resumen === null && (
        <p role="status" className="text-sm text-gray-400 italic">
          Cargando...
        </p>
      )}
      {!error && resumen !== null && (
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-sm text-gray-400 mb-2">
              {resumen.dias_con_checkin_readiness} días con check-in de recuperación
            </p>
            <div className="flex gap-4 text-center">
              <div>
                <p className="font-display text-2xl font-bold text-recovery-high">
                  {resumen.distribucion_readiness.green}
                </p>
                <p className="text-xs text-gray-400 uppercase">Green</p>
              </div>
              <div>
                <p className="font-display text-2xl font-bold text-recovery-medium">
                  {resumen.distribucion_readiness.yellow}
                </p>
                <p className="text-xs text-gray-400 uppercase">Yellow</p>
              </div>
              <div>
                <p className="font-display text-2xl font-bold text-recovery-low">
                  {resumen.distribucion_readiness.red}
                </p>
                <p className="text-xs text-gray-400 uppercase">Red</p>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/10">
            <p className="text-sm text-gray-400 mb-1">Peso</p>
            {resumen.peso_delta_kg === null ? (
              <p className="text-sm text-gray-500 italic">
                Sin suficientes mediciones de peso esta semana para calcular una tendencia.
              </p>
            ) : (
              <p className="text-white">
                {resumen.peso_delta_kg > 0 ? "+" : ""}
                {resumen.peso_delta_kg.toFixed(1)} kg
                <span className="text-gray-400 text-sm ml-2">
                  ({resumen.peso_inicio_kg?.toFixed(1)} → {resumen.peso_fin_kg?.toFixed(1)} kg)
                </span>
              </p>
            )}
          </div>

          <div className="pt-4 border-t border-white/10">
            <p className="text-sm text-gray-400 mb-1">Actividades</p>
            <p className="text-white">
              {resumen.actividades_totales}{" "}
              {resumen.actividades_totales === 1 ? "actividad" : "actividades"}
              {resumen.duracion_actividades_total_seg > 0 && (
                <span className="text-gray-400 text-sm ml-2">
                  ({Math.round(resumen.duracion_actividades_total_seg / 60)} min totales)
                </span>
              )}
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}
