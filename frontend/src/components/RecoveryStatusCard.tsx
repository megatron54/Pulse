"use client";

import { useEffect, useState } from "react";
import { HeartPulse } from "lucide-react";
import { api, ApiError, type GarminHealthDay, type ReadinessResult } from "@/lib/api";
import { AreaTrendChart } from "./ui/AreaTrendChart";
import { CoachNarrativeBlock } from "./CoachNarrativeBlock";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { PALETA } from "@/lib/theme";

const DIAS_MINI_TENDENCIA = 7;

const ZONA = {
  green: { label: "Recovery alta", clase: "bg-recovery-high/15 text-recovery-high" },
  yellow: { label: "Recovery media", clase: "bg-recovery-medium/15 text-recovery-medium" },
  red: { label: "Recovery baja", clase: "bg-recovery-low/15 text-recovery-low" },
} as const;

/**
 * Hero de la página "Hoy" (reconstrucción v2 -
 * 01-arquitectura/04-design-system-v2.md, Fase 2): sustituye por
 * completo al check-in manual (`ReadinessCheckinForm`, eliminado) y a
 * los anillos de `RecoveryRing` (eliminado). Los datos son 100%
 * automáticos de Garmin - CERO inputs manuales.
 *
 * Jerarquía (nivel 1 del dashboard "Hoy"): estado semáforo primero,
 * las 3-4 métricas que lo explican debajo, la narrativa del coach al
 * final. "Unknown is not zero": si el scheduler todavía no ha
 * sincronizado hoy, se comunica explícitamente - nunca un cero
 * inventado ni una zona por defecto.
 */
export function RecoveryStatusCard({ userId }: { userId: number }) {
  const [readinessHoy, setReadinessHoy] = useState<ReadinessResult[] | null>(null);
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    Promise.all([
      api.getReadinessHistory(userId, 1),
      api.getGarminHealthHistory(userId, DIAS_MINI_TENDENCIA),
    ])
      .then(([readiness, health]) => {
        if (cancelado) return;
        setReadinessHoy(readiness);
        setHistorial(health);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar tu estado de hoy.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  const cronologico = historial ? [...historial].reverse() : [];
  // .at(-1) en vez de [0]: getReadinessHistory devuelve orden
  // ascendente (más antiguo primero) - con days=1 da igual porque solo
  // puede haber 0 o 1 fila, pero .at(-1) es correcto también si algún
  // día se cambia el `days` de esta llamada (hallazgo de code-review).
  const zonaHoy = readinessHoy?.at(-1)?.resultado ?? null;
  const cargando = readinessHoy === null || historial === null;

  return (
    <section className="rounded-2xl border border-surface-border bg-surface p-6 shadow-sm">
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && cargando && <LoadingState lines={4} />}
      {!error && !cargando && (
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm text-text-secondary">Tu recovery de hoy</p>
              {zonaHoy ? (
                <span
                  className={`mt-1 inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${ZONA[zonaHoy].clase}`}
                >
                  {ZONA[zonaHoy].label}
                </span>
              ) : (
                <span className="mt-1 inline-flex items-center rounded-full bg-surface-muted px-3 py-1 text-sm font-medium text-text-secondary">
                  Aún sin datos de hoy
                </span>
              )}
            </div>
          </div>

          {historial && historial.length === 0 && (
            <EmptyState icon={HeartPulse} message="Todavía no hay datos de recovery sincronizados." />
          )}

          {historial && historial.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <MiniMetrica titulo="VFC" color={PALETA.recoveryHigh} datos={cronologico} campo="hrv_value" />
              <MiniMetrica
                titulo="Body Battery"
                color={PALETA.accent}
                datos={cronologico}
                campo="body_battery_am"
              />
              <MiniMetrica titulo="Sueño" color={PALETA.sleep} datos={cronologico} campo="sleep_score" />
              <MiniMetrica
                titulo="Estrés"
                color={PALETA.recoveryLow}
                datos={cronologico}
                campo="stress_avg"
              />
            </div>
          )}

          <CoachNarrativeBlock userId={userId} />
        </div>
      )}
    </section>
  );
}

function MiniMetrica({
  titulo,
  color,
  datos,
  campo,
}: {
  titulo: string;
  color: string;
  datos: GarminHealthDay[];
  campo: keyof Pick<GarminHealthDay, "hrv_value" | "body_battery_am" | "sleep_score" | "stress_avg">;
}) {
  const puntos = datos
    .filter((d) => d[campo] != null)
    .map((d) => ({ fecha: d.fecha, valor: d[campo] as number }));

  // "unknown is not zero": sin ningún dato de esta métrica en los
  // últimos 7 días, se omite en vez de mostrar un valor inventado.
  if (puntos.length === 0) return null;

  const hoy = puntos[puntos.length - 1].valor;

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-text-secondary">{titulo}</span>
      <span className="text-lg font-semibold text-foreground">{hoy}</span>
      <AreaTrendChart data={puntos} color={color} alto={24} decimales={0} />
    </div>
  );
}
