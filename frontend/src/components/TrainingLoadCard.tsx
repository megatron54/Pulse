"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type TrainingLoad } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";

// Mismos umbrales que engine/guardrails.py (_ACWR_DELOAD_UMBRAL=1.5,
// engine/periodization.py _ACWR_YELLOW=1.3) - coloreado puramente
// informativo aquí, la decisión real de forzar deload la sigue
// tomando el motor de reglas del backend, esta tarjeta solo visualiza
// el mismo número que ya usa esa lógica. El guardrail real de deload
// exige 2 días CONSECUTIVOS >1.5 (ver engine/guardrails.py) - esta
// tarjeta muestra el ACWR de un solo día, así que "riesgo alto" aquí
// no implica por sí solo que el deload automático se haya disparado.
function colorPorAcwr(acwr: number): string {
  if (acwr > 1.5) return "text-recovery-low";
  if (acwr > 1.3) return "text-recovery-medium";
  return "text-recovery-high";
}

// Etiqueta textual del riesgo, independiente del color (WCAG 1.4.1 -
// mismo patrón ya aplicado en ReadinessTrendCard/RecoveryRing: el
// significado nunca debe depender solo del color).
function riesgoPorAcwr(acwr: number): string {
  if (acwr > 1.5) return "riesgo alto";
  if (acwr > 1.3) return "precaución";
  return "óptimo";
}

export function TrainingLoadCard({ userId }: { userId: number }) {
  const [resultado, setResultado] = useState<TrainingLoad | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getTrainingLoad(userId)
      .then((datos) => {
        if (!cancelado) setResultado(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar la carga de entrenamiento."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId]);

  return (
    <Card>
      <CardTitle>Carga de entrenamiento (ACWR)</CardTitle>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      {!error && resultado === null && (
        <p className="text-sm text-gray-400 italic">Cargando...</p>
      )}
      {!error && resultado && resultado.acwr === null && (
        <p className="text-sm text-gray-400 italic">
          Todavía no hay suficiente historial de sesiones para calcular tu carga de
          entrenamiento real.
        </p>
      )}
      {!error && resultado && resultado.acwr !== null && (
        <>
          <p
            className={`font-display text-4xl font-bold ${colorPorAcwr(resultado.acwr)}`}
            aria-label={`ACWR ${resultado.acwr.toFixed(2)}: ${riesgoPorAcwr(resultado.acwr)}`}
          >
            {resultado.acwr.toFixed(2)}
          </p>
          <p className="text-sm text-gray-300 mt-1">{riesgoPorAcwr(resultado.acwr)}</p>
          <p className="text-sm text-gray-400 mt-1">
            Agudo (7d): {resultado.acute_avg_7d?.toFixed(0)}% · Crónico (28d):{" "}
            {resultado.chronic_avg_28d?.toFixed(0)}%
          </p>
          {!resultado.datos_suficientes && (
            <p className="text-sm text-recovery-medium mt-3">
              Historial insuficiente ({resultado.dias_con_dato_cronico} de 28 días) - este
              número es informativo, todavía no muy fiable.
            </p>
          )}
        </>
      )}
    </Card>
  );
}
