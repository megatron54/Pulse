"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type GarminExerciseSet } from "@/lib/api";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { Dumbbell } from "lucide-react";

/**
 * Épica G del plan de desarrollo (04-plan-desarrollo-siguiente-fase.md,
 * Fase 1, punto 2): desglose de series/reps/peso de una sesión de
 * gimnasio, expandible bajo la fila de la actividad en
 * `SportActivityHistoryCard`. Series de tipo "REST" (descanso entre
 * ejercicios) no traen categoría/peso/reps útiles - se muestran solo
 * la duración, nunca "0 reps" inventado.
 */
export function ExerciseSetsDetail({ userId, activityId }: { userId: number; activityId: string }) {
  const [series, setSeries] = useState<GarminExerciseSet[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminExerciseSets(userId, activityId)
      .then((datos) => {
        if (!cancelado) setSeries(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudieron cargar las series.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, activityId]);

  return (
    <div className="ml-4 mb-2 rounded-xl border border-surface-border bg-surface-muted/50 px-4 py-3">
      {error && <ErrorState message={error} />}
      {!error && series === null && <LoadingState lines={2} />}
      {!error && series !== null && series.length === 0 && (
        <EmptyState icon={Dumbbell} message="Esta sesión no tiene series detalladas sincronizadas." />
      )}
      {!error && series !== null && series.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-text-secondary">
              <th className="pb-1 font-medium">Serie</th>
              <th className="pb-1 font-medium">Ejercicio</th>
              <th className="pb-1 font-medium text-right">Reps</th>
              <th className="pb-1 font-medium text-right">Peso</th>
            </tr>
          </thead>
          <tbody>
            {series.map((s) => (
              <tr key={s.numero_serie} className="border-t border-surface-border/60">
                <td className="py-1 tabular-nums text-text-secondary">{s.numero_serie + 1}</td>
                <td className="py-1 capitalize">
                  {s.tipo_serie === "REST"
                    ? "Descanso"
                    : (s.categoria_ejercicio ?? "—").toLowerCase().replace(/_/g, " ")}
                </td>
                <td className="py-1 text-right tabular-nums">{s.repeticiones ?? "—"}</td>
                <td className="py-1 text-right tabular-nums">
                  {s.peso_kg != null ? `${s.peso_kg} kg` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
