"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type ReadinessResult } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { Card, CardTitle } from "./ui/Card";

// Colores exactos de la guía de marca de WHOOP para zonas de recovery
// ("WHOOP - Brand & Design Guidelines"), vía los tokens de tema
// definidos una sola vez en globals.css (--color-recovery-*) - no
// arbitrary values `bg-[#hex]` duplicados por componente (code-review
// M1: evita que el mismo hex viva repetido en N archivos).
const COLOR_POR_RESULTADO: Record<string, string> = {
  green: "bg-recovery-high",
  yellow: "bg-recovery-medium",
  red: "bg-recovery-low",
};

// Etiqueta legible independiente del color, para que el significado no
// dependa SOLO del color (WCAG 2.2 AA 1.4.1 "Use of Color" - hallazgo
// de code-review: el atributo `title` nativo no es fiable para lectores
// de pantalla ni accesible en táctil, por eso también se usa
// `aria-label` explícito más abajo).
const ETIQUETA_POR_RESULTADO: Record<string, string> = {
  green: "óptimo",
  yellow: "precaución",
  red: "alerta",
};

/**
 * Dashboard de tendencia de readiness (Fase I) sobre
 * `GET /readiness/history`. A diferencia del peso, el resultado es
 * categórico (rojo/amarillo/verde) - una línea continua sería engañosa
 * (implicaría un orden/magnitud entre semáforos que no existe), así que
 * se representa como una fila de bloques de color, un día = un bloque,
 * mismo patrón visual que un "commit heatmap".
 */
export function ReadinessTrendCard({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  /** Ver docstring del mismo parámetro en `WeightTrendCard`. */
  refreshKey?: number;
}) {
  const [historial, setHistorial] = useState<ReadinessResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getReadinessHistory(userId, 30)
      .then((datos) => {
        if (!cancelado) setHistorial(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar el historial de readiness."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey]);

  const diario = historial ? dedupeUltimaPorDia(historial) : [];

  return (
    <Card>
      <CardTitle>Tendencia de readiness (30 días)</CardTitle>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      {!error && historial !== null && diario.length === 0 && (
        <p className="text-sm text-gray-400 italic">Todavía no hay check-ins registrados.</p>
      )}
      {!error && diario.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5"
          role="list"
          aria-label="Historial de readiness por día"
        >
          {diario.map((dia) => (
            <div
              key={dia.id}
              role="listitem"
              data-testid="readiness-dia"
              aria-label={`${dia.fecha}: ${ETIQUETA_POR_RESULTADO[dia.resultado] ?? dia.resultado}`}
              title={`${dia.fecha}: ${dia.resultado}`}
              className={`w-4 h-4 rounded-full transition-transform hover:scale-125 ${COLOR_POR_RESULTADO[dia.resultado] ?? "bg-gray-600"}`}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
