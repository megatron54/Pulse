"use client";

import { useEffect, useState } from "react";
import { HeartPulse } from "lucide-react";
import { api, ApiError, type GarminHealthDay } from "@/lib/api";
import { AreaTrendChart } from "./ui/AreaTrendChart";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { PALETA } from "@/lib/theme";

const RANGOS = [
  { dias: 7, label: "7d" },
  { dias: 30, label: "30d" },
  { dias: 90, label: "90d" },
] as const;

/** Épica E del plan de expansión (02-roadmap/03-vision-produccion.md):
 * histórico interactivo completo de recovery de Garmin. Selector de
 * rango (7/30/90 días, la opción más barata y de mayor valor del plan
 * - un zoom por arrastre queda diferido a v2) + una gráfica por
 * métrica, mostrada SOLO si esa métrica tiene al menos un dato real en
 * la ventana ("unknown is not zero": nunca se dibuja una gráfica vacía
 * o inventada para una métrica sin datos, ej. VO2max en un dispositivo
 * que no lo calcula todavía - ver garmin_sync/client.py::_extraer_vo2max). */
export function GarminHealthHistoryCard({ userId }: { userId: number }) {
  const [dias, setDias] = useState<(typeof RANGOS)[number]["dias"]>(90);
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthHistory(userId, dias)
      .then((datos) => {
        if (cancelado) return;
        setHistorial(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial de recovery.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, dias, intentos]);

  // El backend devuelve más reciente primero (un punto por día, ya
  // deduplicado) - las gráficas de tendencia esperan orden ascendente
  // (pasado -> presente), de ahí el reverse.
  const cronologico = historial ? [...historial].reverse() : [];

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <CardTitle>Salud y recovery</CardTitle>
        <div className="flex gap-1" role="radiogroup" aria-label="Rango temporal">
          {RANGOS.map((rango) => (
            <button
              key={rango.dias}
              type="button"
              role="radio"
              onClick={() => setDias(rango.dias)}
              aria-checked={dias === rango.dias}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                dias === rango.dias
                  ? "bg-white/10 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {rango.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      )}
      {!error && historial === null && <LoadingState lines={4} />}
      {!error && historial !== null && historial.length === 0 && (
        <EmptyState icon={HeartPulse} message="Todavía no hay datos de recovery sincronizados." />
      )}
      {!error && historial && historial.length > 0 && (
        <div className="flex flex-col gap-5">
          <MetricaSeccion
            titulo="VFC (HRV)"
            unidad=" ms"
            color={PALETA.recoveryHigh}
            datos={cronologico}
            campo="hrv_value"
          />
          <MetricaSeccion
            titulo="Body Battery"
            unidad=""
            color={PALETA.teal}
            datos={cronologico}
            campo="body_battery_am"
          />
          <MetricaSeccion
            titulo="Sueño (score)"
            unidad=""
            color={PALETA.sleep}
            datos={cronologico}
            campo="sleep_score"
          />
          <MetricaSeccion
            titulo="Estrés medio"
            unidad=""
            color={PALETA.recoveryLow}
            datos={cronologico}
            campo="stress_avg"
          />
          <MetricaSeccion
            titulo="Pulso en reposo"
            unidad=" ppm"
            color={PALETA.strain}
            datos={cronologico}
            campo="resting_hr"
          />
          <MetricaSeccion
            titulo="VO2max"
            unidad=""
            color={PALETA.recoveryBlue}
            datos={cronologico}
            campo="vo2max"
          />
        </div>
      )}
    </Card>
  );
}

function MetricaSeccion({
  titulo,
  unidad,
  color,
  datos,
  campo,
}: {
  titulo: string;
  unidad: string;
  color: string;
  datos: GarminHealthDay[];
  campo: keyof Pick<
    GarminHealthDay,
    "hrv_value" | "body_battery_am" | "sleep_score" | "stress_avg" | "resting_hr" | "vo2max"
  >;
}) {
  const puntos = datos
    // `!= null` (laxo) en vez de `!== null`: defensa en profundidad si
    // el backend alguna vez omitiera la clave del todo (undefined) en
    // vez de mandar null explícito - el tipo GarminHealthDay lo
    // garantiza hoy, pero request() hace JSON.parse crudo sin validar
    // el payload en runtime (hallazgo de @code-reviewer).
    .filter((d) => d[campo] != null)
    .map((d) => ({ fecha: d.fecha, valor: d[campo] as number }));

  // "unknown is not zero": si NINGÚN día de la ventana tiene este
  // campo (ej. VO2max en un dispositivo que no lo calcula todavía),
  // no se muestra la sección en absoluto - mostrar una gráfica vacía
  // aparentaría un dato ausente como "cero", que es falso.
  if (puntos.length === 0) return null;

  const ultimo = puntos[puntos.length - 1].valor;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">{titulo}</h3>
        <span className="font-display text-sm font-bold text-white">
          {ultimo}
          {unidad}
        </span>
      </div>
      <AreaTrendChart data={puntos} color={color} unidad={unidad} alto={64} decimales={0} />
    </div>
  );
}
