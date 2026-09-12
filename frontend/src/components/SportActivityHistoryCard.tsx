"use client";

import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { api, ApiError, type GarminActivity } from "@/lib/api";
import { formatDistancia, formatDuracion } from "@/lib/activityFormat";
import { ActivityListItem } from "./ui/ActivityListItem";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { WeeklyVolumeChart } from "./WeeklyVolumeChart";

/** Épica G del plan de expansión (02-roadmap/03-vision-produccion.md):
 * histórico de actividades de UNA categoría de deporte (running,
 * ciclismo, gimnasio), reutilizando el mismo endpoint de `/activities`
 * ya construido (Épica D del backend añadió el filtro `categoria`).
 * Un único componente parametrizado en vez de 3 casi-duplicados
 * (`GarminActivitiesCard` sigue existiendo tal cual para la vista SIN
 * filtrar de la página `/garmin`).
 *
 * Nota de honestidad (Épica D del backend): la agrupación de `typeKey`
 * de Garmin bajo cada categoría (ej. "running" también incluye
 * "trail_running") no está verificada todavía contra una actividad
 * real del usuario - se documenta esa incertidumbre en
 * `services.garmin_query_service.CategoriaDeporte`, no aquí (este
 * componente solo consume el resultado ya filtrado por el backend).
 */
export function SportActivityHistoryCard({
  userId,
  categoria,
  titulo,
  icono,
  mensajeVacio,
}: {
  userId: number;
  categoria: "running" | "ciclismo" | "gimnasio";
  titulo: string;
  icono: LucideIcon;
  mensajeVacio: string;
}) {
  const [actividades, setActividades] = useState<GarminActivity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminActivities(userId, 90, undefined, categoria)
      .then((datos) => {
        if (cancelado) return;
        setActividades(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, categoria, intentos]);

  return (
    <Card>
      <div className="flex items-baseline justify-between mb-4">
        <CardTitle>{titulo}</CardTitle>
        {actividades && actividades.length > 0 && (
          <span className="text-xs text-text-secondary">
            {actividades.length} {actividades.length === 1 ? "sesión" : "sesiones"} (90 días)
          </span>
        )}
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
      {!error && actividades === null && <LoadingState lines={2} />}
      {!error && actividades !== null && actividades.length === 0 && (
        <EmptyState icon={icono} message={mensajeVacio} />
      )}
      {!error && actividades !== null && actividades.length > 0 && (
        <div className="flex flex-col gap-2">
          {actividades.map((act) => (
            <ActivityListItem
              key={act.activity_id}
              icon={icono}
              title={act.tipo.replace(/_/g, " ")}
              subtitle={act.fecha}
              metrics={[
                { label: "Duración", value: formatDuracion(act.duracion_seg) },
                { label: "Distancia", value: formatDistancia(act.distancia_m) },
              ]}
            />
          ))}
        </div>
      )}
      {!error && (
        <WeeklyVolumeChart
          userId={userId}
          categoria={categoria}
          metrica={categoria === "gimnasio" ? "duracion" : "distancia"}
        />
      )}
    </Card>
  );
}
