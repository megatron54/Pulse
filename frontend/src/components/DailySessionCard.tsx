"use client";

import { useEffect, useState } from "react";
import { CalendarClock } from "lucide-react";
import { api, ApiError, todayLocalDate, type DailySessionResult, type SessionTypeValue } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

const LABELS: Record<SessionTypeValue, string> = {
  rest: "Descanso",
  active_recovery: "Recuperación activa",
  strength_heavy: "Fuerza pesada",
  strength_hypertrophy: "Hipertrofia",
  endurance_intervals: "Intervalos de resistencia",
  endurance_long: "Resistencia larga",
  martial_arts_technical: "Artes marciales (técnica)",
  martial_arts_sparring: "Artes marciales (sparring)",
};

/**
 * Nivel 2 del dashboard "Hoy" (reconstrucción v2): se carga
 * automáticamente al montar - antes requería pulsar "Ver decisión del
 * coach" y elegir manualmente qué tocaba hoy, lo cual contradice el
 * principio de "cero pasos manuales para algo que el motor de reglas
 * ya puede derivar solo" del check-in. Deriva SIEMPRE de tu plan
 * semanal activo + tu recovery real de Garmin - si falta cualquiera de
 * los dos, se explica honestamente en vez de forzar un formulario.
 */
export function DailySessionCard({ userId }: { userId: number }) {
  const [resultado, setResultado] = useState<DailySessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Distinto de `error`: un 400 (sin recovery de hoy / sin plan
  // activo) es un estado VACÍO esperado, no un fallo del sistema - no
  // debe anunciarse como `role="alert"` a lectores de pantalla
  // (hallazgo de code-review, BAJO).
  const [sinDatos, setSinDatos] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getDailySession(userId, { target_date: todayLocalDate() })
      .then((r) => {
        if (cancelado) return;
        setError(null);
        setSinDatos(null);
        setResultado(r);
      })
      .catch((err) => {
        if (cancelado) return;
        if (err instanceof ApiError && err.status === 400) {
          setSinDatos(
            "Aún no hay recovery de hoy sincronizado de Garmin, o no tienes un plan semanal activo."
          );
        } else {
          setError(err instanceof ApiError ? err.message : "No se pudo calcular la sesión de hoy.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  return (
    <Card>
      <CardTitle>Sesión de hoy</CardTitle>
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && sinDatos && <EmptyState icon={CalendarClock} message={sinDatos} />}
      {!error && !sinDatos && resultado === null && <LoadingState lines={2} />}
      {!error && !sinDatos && resultado && (
        <div className="flex flex-col gap-3">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-3xl font-semibold text-accent">{resultado.volume_pct}%</span>
            <span className="text-lg font-semibold text-foreground">
              {LABELS[resultado.session_type as SessionTypeValue] ?? resultado.session_type}
            </span>
            {resultado.intensity_rpe_cap !== null && (
              <span className="text-sm text-text-secondary">RPE máx {resultado.intensity_rpe_cap}</span>
            )}
          </div>
          <div className="h-1.5 w-full rounded-full bg-surface-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-accent transition-all duration-700 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, resultado.volume_pct))}%` }}
            />
          </div>
          <p className="text-sm text-text-secondary">{resultado.narrative_text}</p>
        </div>
      )}
    </Card>
  );
}
