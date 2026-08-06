"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, HeartPulse } from "lucide-react";
import { api, ApiError, type GarminHealthDay } from "@/lib/api";
import { AreaTrendChart } from "./ui/AreaTrendChart";
import { Card, CardTitle } from "./ui/Card";
import { CoachNarrativeBlock } from "./CoachNarrativeBlock";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { PALETA } from "@/lib/theme";

const DIAS_RESUMEN = 7;

/** Épica J del plan de expansión (02-roadmap/03-vision-produccion.md):
 * resumen CORTO de salud/recovery para el dashboard "Hoy" - el valor
 * de hoy + una micro-tendencia de 7 días por métrica, nunca el
 * histórico completo (eso vive en /salud, Épica E). Regla de diseño
 * "resumen vs. detalle" del plan: aquí solo entran las métricas más
 * accionables día a día (HRV, Body Battery, sueño, estrés) - resting
 * HR y VO2max cambian poco día a día y quedan solo en el detalle
 * completo, para no sobrecargar el dashboard principal. */
export function HealthSummaryCard({ userId }: { userId: number }) {
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthHistory(userId, DIAS_RESUMEN)
      .then((datos) => {
        if (cancelado) return;
        setHistorial(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el resumen de salud.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  const cronologico = historial ? [...historial].reverse() : [];
  // El backend devuelve más reciente primero (un punto por día, ya
  // deduplicado) - las mini-sparklines esperan orden ascendente
  // (pasado -> presente), mismo criterio que GarminHealthHistoryCard.

  return (
    <Card>
      <CardTitle>Salud</CardTitle>
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && historial === null && <LoadingState lines={3} />}
      {!error && historial !== null && historial.length === 0 && (
        <EmptyState icon={HeartPulse} message="Todavía no hay datos de recovery sincronizados." />
      )}
      {!error && historial && historial.length > 0 && (
        <div className="flex flex-col gap-3">
          <CoachNarrativeBlock userId={userId} />
          <MiniMetrica titulo="VFC" color={PALETA.recoveryHigh} datos={cronologico} campo="hrv_value" />
          <MiniMetrica titulo="Body Battery" color={PALETA.teal} datos={cronologico} campo="body_battery_am" />
          <MiniMetrica titulo="Sueño" color={PALETA.sleep} datos={cronologico} campo="sleep_score" />
          <MiniMetrica titulo="Estrés" color={PALETA.recoveryLow} datos={cronologico} campo="stress_avg" />
          <Link
            href="/salud"
            className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-white transition-colors"
          >
            Ver histórico completo
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </div>
      )}
    </Card>
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
  // últimos 7 días, se omite la fila entera en vez de mostrar un
  // valor inventado o una sparkline vacía.
  if (puntos.length === 0) return null;

  const hoy = puntos[puntos.length - 1].valor;

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-baseline gap-2">
        <span className="text-xs uppercase tracking-wide text-gray-400">{titulo}</span>
        <span className="font-display text-sm font-bold text-white">{hoy}</span>
      </div>
      <div className="w-20 shrink-0">
        <AreaTrendChart data={puntos} color={color} alto={28} decimales={0} />
      </div>
    </div>
  );
}
