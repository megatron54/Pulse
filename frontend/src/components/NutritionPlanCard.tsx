"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import {
  api,
  ApiError,
  todayLocalDate,
  type ActiveNutritionPlan,
  type NutritionPhaseRecommendation,
} from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

const ETIQUETA_FASE: Record<string, string> = {
  cut: "Déficit",
  maintenance: "Mantenimiento",
  recomp: "Recomposición",
  surplus: "Superávit",
};

/**
 * Plan de fase de peso con duración determinada (petición explícita
 * del usuario: "planes de deficit, superhabit y mantenimiento
 * dedicados, con duración determinada, como tu nutricionista
 * personal"). El sistema RECOMIENDA (analizando duración/guardrails de
 * recovery ya existentes), el usuario CONFIRMA - decisión explícita:
 * "recomienda, tú confirmas". Nunca se crea un plan automáticamente.
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

  const cargando = activo === undefined;

  return (
    <Card>
      <CardTitle>Plan nutricional</CardTitle>
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && cargando && <LoadingState lines={2} />}
      {!error && !cargando && (
        <div className="flex flex-col gap-3">
          {activo ? (
            <div>
              <p className="text-lg font-semibold text-foreground">
                {ETIQUETA_FASE[activo.plan.fase] ?? activo.plan.fase}
              </p>
              <p className="text-sm text-text-secondary">
                {activo.expirado
                  ? "Plan finalizado."
                  : `${activo.dias_restantes} días restantes (hasta ${activo.fecha_fin})`}
              </p>
            </div>
          ) : (
            <p className="text-sm text-text-secondary">Sin plan activo todavía.</p>
          )}

          {recomendacion?.accion === "nuevo_plan_sugerido" && (
            <div className="flex items-start gap-2 rounded-xl border border-accent/20 bg-accent/5 px-4 py-3">
              <Sparkles aria-hidden="true" size={16} className="mt-0.5 shrink-0 text-accent" />
              <div className="flex-1">
                <p className="text-sm text-foreground">{recomendacion.motivo}</p>
                <p className="text-xs text-text-secondary mt-1">
                  Sugerencia: {ETIQUETA_FASE[recomendacion.fase_recomendada]}
                  {recomendacion.semanas_sugeridas != null &&
                    ` durante ${recomendacion.semanas_sugeridas} semanas`}
                  .
                </p>
                <Button
                  variant="secondary"
                  className="mt-2 text-xs px-3 py-1.5"
                  onClick={confirmarRecomendacion}
                  disabled={confirmando}
                >
                  {confirmando ? "Confirmando..." : "Confirmar"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
