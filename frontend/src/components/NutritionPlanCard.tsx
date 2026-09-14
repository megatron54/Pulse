"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  todayLocalDate,
  type ActiveNutritionPlan,
  type NutritionPhaseRecommendation,
} from "@/lib/api";
import { FASES_NUTRICION, nombreFase } from "@/lib/fasesNutricion";
import { fechaCorta, plural } from "@/lib/fechas";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { DataList, DataRow } from "./ui/DataList";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

/**
 * Plan de fase de peso con duración determinada (petición explícita del
 * usuario: "planes de deficit, superhabit y mantenimiento dedicados,
 * con duración determinada, como tu nutricionista personal"). El
 * sistema RECOMIENDA (analizando duración y los guardrails de recovery
 * ya existentes), el usuario CONFIRMA - decisión explícita: nunca se
 * crea un plan automáticamente.
 *
 * v3: la recomendación era una caja teñida de acento con un icono de
 * "destellos" dentro de la tarjeta - tarjeta anidada (doctrina 2) y
 * color decorativo (doctrina 1), con el añadido de que el icono de
 * chispas sugiere "IA mágica" justo donde el valor es lo contrario:
 * una regla explicable que el usuario tiene que poder juzgar. Ahora es
 * una sección separada por una línea, con el motivo en texto normal y
 * el botón con su nombre completo.
 */
export function NutritionPlanCard({ userId }: { userId: number }) {
  const [activo, setActivo] = useState<ActiveNutritionPlan | null | undefined>(undefined);
  const [recomendacion, setRecomendacion] = useState<NutritionPhaseRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    Promise.all([
      api.getActiveNutritionPlan(userId),
      api.getNutritionPhaseRecommendation(userId),
    ])
      .then(([plan, rec]) => {
        if (cancelado) return;
        setActivo(plan);
        setRecomendacion(rec);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar tu plan nutricional.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  async function confirmarRecomendacion() {
    if (!recomendacion || recomendacion.semanas_sugeridas == null) return;
    setConfirmando(true);
    try {
      await api.createNutritionPlan(userId, {
        fase: recomendacion.fase_recomendada,
        semanas_duracion: recomendacion.semanas_sugeridas,
        fecha_inicio: todayLocalDate(),
        motivo: recomendacion.motivo,
      });
      setIntentos((n) => n + 1); // recarga el plan activo ya confirmado
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el plan.");
    } finally {
      setConfirmando(false);
    }
  }

  const encabezado = <h2 className="t-section text-ink">Plan nutricional</h2>;

  if (error) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      </Card>
    );
  }

  if (activo === undefined) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <LoadingState lines={2} />
      </Card>
    );
  }

  const sugerencia = recomendacion?.accion === "nuevo_plan_sugerido" ? recomendacion : null;

  return (
    <Card plano>
      <div className="flex flex-col gap-4 p-5">
        {encabezado}
        {activo ? (
          <>
            <div>
              <p className="t-page-title text-ink">{nombreFase(activo.plan.fase)}</p>
              <p className="t-secondary mt-1 max-w-prose text-pretty text-ink-3">
                {FASES_NUTRICION[activo.plan.fase]?.explicacion}
              </p>
            </div>
            <DataList>
              <DataRow
                label="Duración"
                nota={`${plural(activo.plan.semanas_duracion, "semana", "semanas")} desde el ${fechaCorta(activo.plan.fecha_inicio)}`}
              >
                {activo.expirado
                  ? "Terminado"
                  : `${plural(activo.dias_restantes, "día restante", "días restantes")}`}
              </DataRow>
              <DataRow label="Termina el">{fechaCorta(activo.fecha_fin)}</DataRow>
            </DataList>
          </>
        ) : (
          <p className="t-body max-w-prose text-pretty text-ink-2">
            Sin plan activo todavía. Un plan fija tu fase y su duración, y es lo que decide si el
            objetivo de calorías de cada día está en déficit, en mantenimiento o en superávit.
          </p>
        )}
      </div>

      {sugerencia && (
        <div className="border-t border-line px-5 py-4">
          <h3 className="t-micro mb-2 text-ink-3">Lo que sugiere Pulse</h3>
          <p className="t-body max-w-prose text-pretty text-ink">{sugerencia.motivo}</p>
          <p className="t-secondary mt-1 text-ink-3">
            {nombreFase(sugerencia.fase_recomendada)}
            {sugerencia.semanas_sugeridas != null &&
              ` durante ${plural(sugerencia.semanas_sugeridas, "semana", "semanas")}`}
            .
          </p>
          <div className="mt-3">
            <Button variant="secondary" onClick={confirmarRecomendacion} disabled={confirmando}>
              {confirmando ? "Activando…" : `Activar plan de ${nombreFase(sugerencia.fase_recomendada).toLowerCase()}`}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
