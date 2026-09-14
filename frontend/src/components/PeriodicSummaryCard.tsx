"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type PeriodicSummary } from "@/lib/api";
import { plural } from "@/lib/fechas";
import { formatDuracion } from "@/lib/activityFormat";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { DataList, DataRow } from "./ui/DataList";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

const ZONAS = [
  { clave: "green", label: "Recuperación óptima", barra: "bg-pos" },
  { clave: "yellow", label: "Recuperación media", barra: "bg-warn" },
  { clave: "red", label: "Recuperación baja", barra: "bg-neg" },
] as const;

/**
 * Resumen de la semana (Entrenamiento › Análisis).
 *
 * v3 sustituye el donut de distribución de recuperación por una barra
 * proporcional con las cifras escritas al lado. El donut de 84px con
 * tres arcos y tres números gigantes de colores era, por superficie de
 * color, el objeto más llamativo de la app - y para tres enteros que se
 * leen mejor en una línea de texto. La barra sí aporta algo que los
 * números no: la proporción de un vistazo.
 *
 * Los colores que quedan son los tres semánticos de recuperación, que
 * codifican estado (doctrina 1) y son los mismos de la pantalla de Hoy.
 *
 * Nunca fabrica un delta de peso con una sola medición ni una tendencia
 * de carga sin historial suficiente: respeta los flags que ya devuelve
 * el backend (`peso_delta_kg` a `null`).
 */
export function PeriodicSummaryCard({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  /** Al cambiar (p.ej. tras un check-in de recuperación), fuerza a
   * recargar: sin esto, "días con check-in" se quedaba en 0 hasta
   * recargar la página entera (hallazgo de verificación manual). */
  refreshKey?: number;
}) {
  const [resumen, setResumen] = useState<PeriodicSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getPeriodicSummary(userId)
      .then((datos) => {
        if (!cancelado) setResumen(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el resumen.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey, intentos]);

  if (error) {
    return (
      <Card>
        <h2 className="t-section mb-4 text-ink">Resumen de la semana</h2>
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

  if (resumen === null) {
    return (
      <Card>
        <h2 className="t-section mb-4 text-ink">Resumen de la semana</h2>
        <LoadingState lines={3} />
      </Card>
    );
  }

  const totalCheckins = ZONAS.reduce(
    (suma, zona) => suma + resumen.distribucion_readiness[zona.clave],
    0
  );

  return (
    <Card plano className="p-5" data-print-target>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <h2 className="t-section text-ink">Resumen de la semana</h2>
        <div data-print-hide>
          <Button variant="secondary" onClick={() => window.print()}>
            Guardar en PDF
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-5">
        <section>
          <h3 className="t-micro mb-2 text-ink-3">Cómo has estado</h3>
          {totalCheckins === 0 ? (
            <p className="t-body text-pretty text-ink-2">
              No hay ningún día con recuperación calculada esta semana, así que no hay nada que
              resumir todavía.
            </p>
          ) : (
            <>
              <div className="flex h-2 w-full overflow-hidden rounded-full bg-canvas">
                {ZONAS.map((zona) => {
                  const dias = resumen.distribucion_readiness[zona.clave];
                  if (dias === 0) return null;
                  return (
                    <div
                      key={zona.clave}
                      className={zona.barra}
                      style={{ width: `${(dias / totalCheckins) * 100}%` }}
                    />
                  );
                })}
              </div>
              <dl className="mt-3 divide-y divide-line">
                {ZONAS.map((zona) => {
                  const dias = resumen.distribucion_readiness[zona.clave];
                  if (dias === 0) return null;
                  return (
                    <div key={zona.clave} className="flex items-baseline justify-between gap-6 py-2">
                      <dt className="t-body flex items-center gap-2 text-ink-2">
                        <span aria-hidden="true" className={`size-2 rounded-full ${zona.barra}`} />
                        {zona.label}
                      </dt>
                      <dd className="t-body tabular text-ink">{plural(dias, "día", "días")}</dd>
                    </div>
                  );
                })}
              </dl>
            </>
          )}
        </section>

        <section>
          <h3 className="t-micro mb-2 text-ink-3">Peso y actividad</h3>
          <DataList>
            <DataRow
              label="Peso"
              nota={
                resumen.peso_delta_kg === null
                  ? undefined
                  : `de ${resumen.peso_inicio_kg?.toFixed(1)} a ${resumen.peso_fin_kg?.toFixed(1)} kg`
              }
            >
              {resumen.peso_delta_kg === null ? (
                <span className="text-ink-3">Hacen falta dos pesadas en la semana</span>
              ) : (
                `${resumen.peso_delta_kg > 0 ? "+" : ""}${resumen.peso_delta_kg.toFixed(1)} kg`
              )}
            </DataRow>
            <DataRow
              label="Sesiones"
              nota={
                resumen.duracion_actividades_total_seg > 0
                  ? `${formatDuracion(resumen.duracion_actividades_total_seg)} en total`
                  : undefined
              }
            >
              {plural(resumen.actividades_totales, "sesión", "sesiones")}
            </DataRow>
          </DataList>
        </section>
      </div>
    </Card>
  );
}
