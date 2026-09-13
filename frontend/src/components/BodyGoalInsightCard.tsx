"use client";

import { useEffect, useState } from "react";
import { Target } from "lucide-react";
import { api, ApiError, type BodyMeasurement, type User } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

const DIAS_VENTANA = 30;
// Por debajo de este umbral relativo el cambio de peso se trata como
// "estable" - una fluctuación de agua/comida de un día a otro no debe
// leerse como progreso o retroceso real.
const UMBRAL_ESTABLE_PCT = 1;

const _FASE_LABEL: Record<User["fase_peso_actual"], string> = {
  cut: "Definición (bajar peso)",
  surplus: "Volumen (subir peso)",
  recomp: "Recomposición (peso estable, cambiar composición)",
  maintenance: "Mantenimiento (peso estable)",
};

type Alineacion = "en_linea" | "desviado" | "sin_señal";

function evaluarAlineacion(
  fase: User["fase_peso_actual"],
  deltaPct: number
): Alineacion {
  const estable = Math.abs(deltaPct) < UMBRAL_ESTABLE_PCT;
  if (fase === "cut") return deltaPct < -UMBRAL_ESTABLE_PCT / 2 ? "en_linea" : estable ? "sin_señal" : "desviado";
  if (fase === "surplus") return deltaPct > UMBRAL_ESTABLE_PCT / 2 ? "en_linea" : estable ? "sin_señal" : "desviado";
  // maintenance / recomp: el objetivo es la estabilidad de peso.
  return estable ? "en_linea" : "desviado";
}

/**
 * Compara la tendencia de peso real (báscula Feelfit, vía
 * `WeightTrendCard`/`getBodyMeasurementHistory`) contra la fase de
 * peso objetivo del usuario (`UserProfile.fase_peso_actual`) -
 * petición explícita del usuario: "que muestre insights de las fotos y
 * datos de la báscula Feelfit comparado con mis objetivos". No hay
 * ningún objetivo numérico de peso en el backend (ni se inventa uno
 * aquí) - la comparación es honesta: dirección observada vs. dirección
 * esperada por la fase activa, con al menos `DIAS_VENTANA` días de
 * separación real entre mediciones para no leer ruido de un solo día
 * como progreso ("unknown is not zero").
 */
export function BodyGoalInsightCard({ userId }: { userId: number }) {
  const [usuario, setUsuario] = useState<User | null>(null);
  const [mediciones, setMediciones] = useState<BodyMeasurement[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    Promise.all([api.getUser(userId), api.getBodyMeasurementHistory(userId, DIAS_VENTANA)])
      .then(([u, m]) => {
        if (cancelado) return;
        setUsuario(u);
        setMediciones(m);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar tu objetivo de composición corporal.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  const cargando = usuario === null || mediciones === null;
  const diario = mediciones ? dedupeUltimaPorDia(mediciones) : [];
  const primero = diario.at(0);
  const ultimo = diario.at(-1);
  const hayVentanaSuficiente = !!primero && !!ultimo && primero.fecha !== ultimo.fecha;

  const deltaPct =
    hayVentanaSuficiente && primero
      ? ((ultimo!.peso_kg - primero.peso_kg) / primero.peso_kg) * 100
      : null;

  const alineacion = usuario && deltaPct != null ? evaluarAlineacion(usuario.fase_peso_actual, deltaPct) : null;

  return (
    <Card>
      <CardTitle>Objetivo de composición corporal</CardTitle>
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
      {!error && !cargando && usuario && (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-text-secondary">
            Fase activa: <span className="font-medium text-foreground">{_FASE_LABEL[usuario.fase_peso_actual]}</span>
          </p>

          {!hayVentanaSuficiente && (
            <EmptyState
              icon={Target}
              message="Todavía no hay suficientes mediciones de peso en días distintos para comparar la tendencia contra tu objetivo."
            />
          )}

          {hayVentanaSuficiente && deltaPct != null && alineacion && (
            <div
              className={`rounded-xl px-4 py-3 text-sm ${
                alineacion === "en_linea"
                  ? "bg-recovery-high/10 text-recovery-high"
                  : alineacion === "desviado"
                    ? "bg-recovery-low/10 text-recovery-low"
                    : "bg-surface-muted text-text-secondary"
              }`}
            >
              {alineacion === "en_linea" && <>Tu peso va en línea con tu objetivo de {_FASE_LABEL[usuario.fase_peso_actual].toLowerCase()}.</>}
              {alineacion === "desviado" && (
                <>
                  Tu peso no está siguiendo la dirección esperada para {_FASE_LABEL[usuario.fase_peso_actual].toLowerCase()}
                  {" "}
                  ({deltaPct > 0 ? "+" : ""}
                  {deltaPct.toFixed(1)}% en los últimos días medidos).
                </>
              )}
              {alineacion === "sin_señal" && (
                <>
                  El peso se ha mantenido prácticamente estable ({deltaPct > 0 ? "+" : ""}
                  {deltaPct.toFixed(1)}%) - normal en un cut/surplus lento, sigue el histórico completo para
                  confirmar la tendencia.
                </>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
