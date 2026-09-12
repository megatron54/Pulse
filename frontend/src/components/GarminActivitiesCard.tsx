"use client";

import { useEffect, useState } from "react";
import { Watch } from "lucide-react";
import { api, ApiError, type GarminActivity } from "@/lib/api";
import { formatDistancia, formatDuracion } from "@/lib/activityFormat";
import { iconForActivityType } from "@/lib/activityIcons";
import { ActivityListItem } from "./ui/ActivityListItem";
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
          message="Sin actividades sincronizadas todavía. El scheduler nocturno las trae automáticamente en cuanto haya alguna nueva en tu cuenta - no se inventa ninguna mientras tanto."
        />
      )}
      {!error && actividades !== null && actividades.length > 0 && (
        <div className="flex flex-col gap-2">
          {actividades.map((act) => (
            <ActivityListItem
              key={act.activity_id}
              icon={iconForActivityType(act.tipo)}
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
    </Card>
  );
}
