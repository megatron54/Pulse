"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type GarminHealthDay } from "@/lib/api";
import { fechaRelativa, masRecientePorFecha } from "@/lib/fechas";
import { METRICAS_SALUD } from "@/lib/metricasSalud";
import { Card } from "./ui/Card";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { MetricGrid, StatTile } from "./ui/StatTile";

/**
 * Últimas medidas de Garmin de cada métrica de recuperación, en
 * Entrenamiento › Recuperación: las siete de `METRICAS_SALUD`, VO₂ máx
 * incluido, frente a las seis del hero de "Hoy" (que deja fuera la que
 * se mueve en semanas y no en días). El detalle intradía vive debajo en
 * `IntradayMetricCard` y el histórico completo en
 * `GarminHealthHistoryCard`: esto es el "de un vistazo" que los
 * precede.
 *
 * v3: se llamaba `HealthMetricsSummaryRow` y era una rejilla suelta,
 * sin título ni contenedor, colgada entre dos tarjetas. Seis cifras sin
 * encabezado no dicen de qué día son ni de dónde vienen - dos preguntas
 * que la auditoría marcó en esta pestaña. Ahora es una tarjeta con
 * título y con la fecha real del dato escrita ("Hoy", "Ayer" o la fecha
 * corta): si el scheduler nocturno no ha sincronizado, el usuario lo ve
 * en vez de leer cifras viejas como si fueran de hoy.
 */
export function HealthMetricsTodayCard({ userId }: { userId: number }) {
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthHistory(userId, 1)
      .then((datos) => {
        if (cancelado) return;
        setHistorial(datos);
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

  const encabezado = (
    <h2 className="t-section text-ink">Tus métricas de recuperación</h2>
  );

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

  if (historial === null) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <LoadingState lines={1} />
      </Card>
    );
  }

  // Por fecha máxima, no `.at(-1)`: este endpoint devuelve orden
  // descendente y `.at(-1)` daba el día más ANTIGUO de la ventana (el
  // mismo bug que en `RecoveryStatusCard`, ver `lib/fechas.ts`).
  const diaHoy = masRecientePorFecha(historial);
  // "unknown is not zero": sin ningún dato todavía (el scheduler
  // nocturno no ha sincronizado), no se muestra nada aquí - el
  // histórico de abajo sigue disponible igualmente.
  if (!diaHoy) return null;

  return (
    <Card>
      <div className="mb-4">
        {encabezado}
        {/* La fecha del dato, no "hoy" a ciegas: el sync de Garmin es
            nocturno y puede fallar (doctrina 9, fechas humanas). */}
        <p className="t-secondary mt-1 text-ink-3">
          Última medida: {fechaRelativa(diaHoy.fecha).toLowerCase()}.
        </p>
      </div>
      {/* Las mismas métricas, los mismos nombres y las mismas unidades
          que en "Hoy" y que en cada página de detalle, porque salen de
          la misma lista; y cada una enlaza a la suya, para que la cifra
          no sea otra vez un callejón sin salida. */}
      <MetricGrid>
        {METRICAS_SALUD.map((metrica) => {
          const valor = diaHoy[metrica.campo];
          if (valor == null) return null;
          return (
            <StatTile
              key={metrica.campo}
              label={metrica.tituloCorto}
              value={valor}
              unit={metrica.unidad}
              decimals={metrica.decimales}
              href={`/salud/${metrica.slug}`}
            />
          );
        })}
      </MetricGrid>
    </Card>
  );
}
