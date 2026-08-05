"use client";

import { useEffect, useState } from "react";
import { CalendarClock } from "lucide-react";
import { motion } from "motion/react";
import { api, ApiError, type ReadinessResult } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { springs } from "@/lib/motion-tokens";

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
  const [intentos, setIntentos] = useState(0);

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
  }, [userId, refreshKey, intentos]);

  const diario = historial ? dedupeUltimaPorDia(historial) : [];
  const totales = diario.reduce(
    (acc, dia) => {
      acc[dia.resultado as "green" | "yellow" | "red"] =
        (acc[dia.resultado as "green" | "yellow" | "red"] ?? 0) + 1;
      return acc;
    },
    {} as Record<"green" | "yellow" | "red", number>
  );

  return (
    <Card>
      <CardTitle>Tendencia de readiness (30 días)</CardTitle>
      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && historial === null && <LoadingState lines={1} />}
      {!error && historial !== null && diario.length === 0 && (
        <EmptyState icon={CalendarClock} message="Todavía no hay check-ins registrados." />
      )}
      {!error && diario.length > 0 && (
        <>
          {/* Barra de proporción: la distribución general de un vistazo,
              antes del detalle día a día del heatmap de abajo. */}
          <div className="flex h-2 w-full rounded-full overflow-hidden mb-4 bg-white/5">
            {(["green", "yellow", "red"] as const).map((zona) =>
              totales[zona] ? (
                <motion.div
                  key={zona}
                  className={COLOR_POR_RESULTADO[zona]}
                  initial={{ width: 0 }}
                  animate={{ width: `${(totales[zona] / diario.length) * 100}%` }}
                  transition={springs.gentle}
                />
              ) : null
            )}
          </div>
          <div
            className="flex flex-wrap gap-2"
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
                // Hallazgo H5 de la auditoría UI/UX: 16px (w-4 h-4) está
                // muy por debajo del área táctil mínima recomendada
                // (WCAG 2.5.5, ~24px como mínimo AA) - se sube a 24px y
                // se añade un pequeño padding visual vía el propio
                // tamaño para que sea razonable de tocar en móvil.
                className={`w-6 h-6 rounded-full transition-transform hover:scale-125 ${COLOR_POR_RESULTADO[dia.resultado] ?? "bg-gray-600"}`}
              />
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
