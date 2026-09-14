"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type GarminExerciseSet } from "@/lib/api";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

/** Nombres de ejercicio de Garmin (`categoria_ejercicio`) en español.
 *  Mostrar "BENCH_PRESS" en minúsculas ("bench press") era dejar el dato
 *  crudo del proveedor en la interfaz. */
const EJERCICIOS: Record<string, string> = {
  BENCH_PRESS: "Press de banca",
  SQUAT: "Sentadilla",
  DEADLIFT: "Peso muerto",
  SHOULDER_PRESS: "Press militar",
  ROW: "Remo",
  PULL_UP: "Dominadas",
  PUSH_UP: "Flexiones",
  LATERAL_RAISE: "Elevaciones laterales",
  BICEPS_CURL: "Curl de bíceps",
  TRICEPS_EXTENSION: "Extensión de tríceps",
  LEG_PRESS: "Prensa de piernas",
  LEG_CURL: "Curl femoral",
  LUNGE: "Zancadas",
  PLANK: "Plancha",
  CRUNCH: "Crunch",
  HIP_THRUST: "Empuje de cadera",
  CARDIO: "Cardio",
  UNKNOWN: "Sin identificar",
};

function nombreEjercicio(categoria: string | null): string {
  if (categoria === null) return "Sin identificar";
  const conocido = EJERCICIOS[categoria];
  if (conocido) return conocido;
  const legible = categoria.toLowerCase().replace(/_/g, " ");
  return legible.charAt(0).toUpperCase() + legible.slice(1);
}

/**
 * Desglose de series de una sesión de gimnasio, desplegado bajo su fila
 * en la tabla de sesiones.
 *
 * v3: fondo teñido y borde redondeado fuera (era una tarjeta dentro de
 * otra tarjeta, doctrina 2); en su lugar va indentado con una línea
 * vertical, que es lo que comunica "esto pertenece a la fila de arriba".
 *
 * Las series de tipo "REST" (descanso entre ejercicios) no traen
 * categoría, peso ni reps útiles: se muestra solo su duración y nunca un
 * "0 reps" inventado.
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
    <div className="border-l border-line pl-4">
      {error && <ErrorState message={error} />}
      {!error && series === null && <LoadingState lines={2} />}
      {!error && series !== null && series.length === 0 && (
        <EmptyState message="Esta sesión no tiene series detalladas sincronizadas." />
      )}
      {!error && series !== null && series.length > 0 && (
        <dl className="grid grid-cols-[auto_1fr_auto] items-baseline gap-x-6 gap-y-2">
          {series.map((s) => (
            <div key={s.numero_serie} className="col-span-3 grid grid-cols-subgrid">
              <dt className="t-secondary tabular text-ink-3">{s.numero_serie + 1}</dt>
              <dd className="t-body text-ink">
                {s.tipo_serie === "REST" ? "Descanso" : nombreEjercicio(s.categoria_ejercicio)}
              </dd>
              <dd className="t-body tabular text-right text-ink-2">
                {detalleSerie(s) ?? <span className="text-ink-3">—</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

/** "10 × 60 kg" / "10 reps" / "45 s" - nunca reps ni peso inventados. */
function detalleSerie(s: GarminExerciseSet): string | null {
  if (s.repeticiones != null && s.peso_kg != null) return `${s.repeticiones} × ${s.peso_kg} kg`;
  if (s.repeticiones != null) return `${s.repeticiones} reps`;
  if (s.duracion_seg != null) return `${s.duracion_seg} s`;
  return null;
}
