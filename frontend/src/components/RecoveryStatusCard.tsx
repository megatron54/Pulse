"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type GarminHealthDay, type ReadinessResult } from "@/lib/api";
import { diasDesdeHoy, fechaRelativa, masRecientePorFecha } from "@/lib/fechas";
import { CoachNarrativeBlock } from "./CoachNarrativeBlock";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { MetricGrid, StatTile } from "./ui/StatTile";

const DIAS_VENTANA = 7;

const ZONA = {
  green: { label: "Recuperación óptima", color: "text-pos", punto: "bg-pos" },
  yellow: { label: "Recuperación media", color: "text-warn", punto: "bg-warn" },
  red: { label: "Recuperación baja", color: "text-neg", punto: "bg-neg" },
} as const;

/**
 * Hero de "Hoy" (Design System v3). Responde a una sola pregunta:
 * ¿cómo estoy hoy?
 *
 * Aquí vivía el bug más serio que encontró la auditoría: se leía
 * `historial.at(-1)`, pero `GET /garmin/health-history` devuelve orden
 * DESCENDENTE, así que `.at(-1)` era el día MÁS ANTIGUO de la ventana -
 * con `days=7`, la app mostraba los datos de hace una semana bajo el
 * título "Tu recovery de hoy". Se veía en la propia tarjeta: las cifras
 * (VFC 65 ms, sueño 83) contradecían a la narrativa del coach justo
 * debajo (50 ms, 51), que sí usaba el día correcto. Ahora se elige por
 * fecha máxima (`masRecientePorFecha`), correcto con cualquier orden.
 *
 * Y se muestra DE QUÉ DÍA son los datos: si el scheduler aún no ha
 * sincronizado hoy, decirlo es más honesto que etiquetar como "hoy" lo
 * último que haya ("unknown is not zero" aplicado a la fecha).
 *
 * Sin medidor circular: el gauge de la iteración anterior presentaba
 * Body Battery como si fuera un score global de recuperación (no lo es,
 * y su etiqueta además desbordaba el círculo), y coloreaba el anillo con
 * la zona, mezclando dos métricas distintas en un solo objeto.
 */
export function RecoveryStatusCard({ userId }: { userId: number }) {
  const [readiness, setReadiness] = useState<ReadinessResult[] | null>(null);
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    Promise.all([
      api.getReadinessHistory(userId, 1),
      api.getGarminHealthHistory(userId, DIAS_VENTANA),
    ])
      .then(([resultadoReadiness, salud]) => {
        if (cancelado) return;
        setReadiness(resultadoReadiness);
        setHistorial(salud);
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

  const zona = masRecientePorFecha(readiness ?? [])?.resultado ?? null;
  const dia = masRecientePorFecha(historial ?? []);
  /** Si el día más reciente con datos es hoy mismo. Distingue "Garmin no
   *  ha sincronizado" de "ha sincronizado, pero la recuperación aún no
   *  se puede calcular". */
  const datosDeHoy = dia !== null && diasDesdeHoy(dia.fecha) === 0;
  const cargando = readiness === null || historial === null;

  if (error) {
    return (
      <section className="rounded-[10px] border border-line bg-surface p-5">
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      </section>
    );
  }

  if (cargando) {
    return (
      <section className="rounded-[10px] border border-line bg-surface p-5">
        <LoadingState lines={4} />
      </section>
    );
  }

  return (
    <section className="rounded-[10px] border border-line bg-surface">
      <div className="flex flex-col gap-5 p-5">
        <div>
          {zona ? (
            <div className="flex items-center gap-2">
              <span aria-hidden="true" className={`size-2 rounded-full ${ZONA[zona].punto}`} />
              <h2 className={`t-page-title ${ZONA[zona].color}`}>{ZONA[zona].label}</h2>
            </div>
          ) : (
            // Tres estados, no dos: "sin datos de hoy" era falso cuando
            // Garmin YA había sincronizado hoy y lo que faltaba era el
            // cálculo. La tarjeta se contradecía a dos líneas de
            // distancia ("Sin datos de hoy todavía" / "Últimos datos
            // sincronizados: hoy") y encima enseñaba las cifras de hoy
            // justo debajo.
            <h2 className="t-page-title text-ink-2">
              {datosDeHoy ? "Recuperación sin calcular" : "Sin datos de hoy todavía"}
            </h2>
          )}
          <p className="t-secondary mt-1 text-pretty text-ink-3">
            {!dia
              ? "Garmin aún no ha sincronizado ningún día."
              : zona || !datosDeHoy
                ? `Últimos datos sincronizados: ${fechaRelativa(dia.fecha).toLowerCase()}`
                : "Garmin ya ha sincronizado hoy. La recuperación necesita además el sueño y la variabilidad cardíaca de esta noche."}
          </p>
        </div>

        {dia && (
          <MetricGrid>
            {dia.sleep_score != null && <StatTile label="Sueño" value={dia.sleep_score} />}
            {dia.body_battery_am != null && (
              <StatTile label="Body Battery" value={dia.body_battery_am} />
            )}
            {dia.hrv_value != null && <StatTile label="VFC" value={dia.hrv_value} unit=" ms" />}
            {dia.stress_avg != null && <StatTile label="Estrés" value={dia.stress_avg} />}
            {dia.resting_hr != null && (
              <StatTile label="Pulso reposo" value={dia.resting_hr} unit=" ppm" />
            )}
            {dia.pasos != null && <StatTile label="Pasos" value={dia.pasos} />}
          </MetricGrid>
        )}
      </div>

      {/* Divisor de 1px en vez de meter la narrativa en otra tarjeta
          dentro de esta (doctrina 2: prohibida la tarjeta anidada).
          `empty:hidden` porque la narrativa no existe todos los días:
          sin eso quedaba una franja vacía con una línea arriba, visible
          en las capturas de la auditoría. */}
      <div className="border-t border-line px-5 py-4 empty:hidden">
        <CoachNarrativeBlock userId={userId} />
      </div>
    </section>
  );
}
