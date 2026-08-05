"use client";

import { useEffect, useState } from "react";
import { Watch } from "lucide-react";
import { api, ApiError, type GarminActivity } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

/**
 * Historial de actividades Garmin ya ingeridas (Épica 2 de
 * 02-roadmap/03-vision-produccion.md). El scheduler nocturno
 * (`services.scheduler_service.run_daily_activity_sync_for_all_users`)
 * es quien sincroniza de verdad - este componente solo lee lo que ya
 * está en la base de datos. Sin credenciales reales de Garmin (Fase H
 * bloqueada), la lista viene vacía para todo usuario real - se muestra
 * ese estado con honestidad (mismo principio que el resto de la app),
 * nunca una maqueta de actividades fabricadas.
 */
function formatDuracion(seg: number | null): string {
  if (seg === null) return "—";
  const minutos = Math.round(seg / 60);
  return `${minutos} min`;
}

function formatDistancia(m: number | null): string {
  if (m === null) return "—";
  return `${(m / 1000).toFixed(1)} km`;
}

export function GarminActivitiesCard({ userId }: { userId: number }) {
  const [actividades, setActividades] = useState<GarminActivity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminActivities(userId)
      .then((datos) => {
        if (!cancelado) setActividades(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  return (
    <Card>
      <CardTitle>Actividades</CardTitle>
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
        <EmptyState
          icon={Watch}
          message="No hay actividades sincronizadas todavía - necesita credenciales reales de Garmin, no vamos a inventar ninguna mientras tanto."
        />
      )}
      {!error && actividades !== null && actividades.length > 0 && (
        <div className="flex flex-col gap-2">
          {actividades.map((act) => (
            <div
              key={act.activity_id}
              className="flex items-center justify-between rounded-lg bg-black/30 px-3 py-2 text-sm"
            >
              <div>
                <p className="text-white capitalize">{act.tipo.replace(/_/g, " ")}</p>
                <p className="text-gray-400 text-xs">{act.fecha}</p>
              </div>
              <div className="text-right text-gray-300">
                <p>{formatDuracion(act.duracion_seg)}</p>
                <p className="text-xs text-gray-400">{formatDistancia(act.distancia_m)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
