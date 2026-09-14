"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type TrainingLoad } from "@/lib/api";
import { plural } from "@/lib/fechas";
import { Card } from "./ui/Card";
import { DataList, DataRow } from "./ui/DataList";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

/**
 * Mismos umbrales que el motor de reglas del backend
 * (`engine/guardrails.py` `_ACWR_DELOAD_UMBRAL=1.5`,
 * `engine/periodization.py` `_ACWR_YELLOW=1.3`). Aquí son puramente
 * informativos: la decisión de forzar un deload la toma el backend, y
 * además exige 2 días CONSECUTIVOS por encima de 1.5 - así que "riesgo
 * alto" en esta tarjeta no implica por sí solo que el deload automático
 * se haya disparado.
 *
 * El significado nunca depende solo del color (WCAG 1.4.1): la etiqueta
 * de texto va siempre, y el color acompaña.
 */
function zonaPorAcwr(acwr: number): { etiqueta: string; color: string; explicacion: string } {
  if (acwr > 1.5) {
    return {
      etiqueta: "Carga muy alta",
      color: "text-neg",
      explicacion: "Estás entrenando bastante más de lo que tu cuerpo tiene asimilado. Si se mantiene dos días, Pulse fuerza una semana de descarga.",
    };
  }
  if (acwr > 1.3) {
    return {
      etiqueta: "Carga alta",
      color: "text-warn",
      explicacion: "Has subido el volumen más rápido de lo habitual. Vigila el sueño y la variabilidad cardíaca estos días.",
    };
  }
  if (acwr < 0.8) {
    return {
      etiqueta: "Carga baja",
      color: "text-ink-2",
      explicacion: "Estás entrenando por debajo de tu media del último mes. Normal en una semana de descarga o tras un parón.",
    };
  }
  return {
    etiqueta: "Carga sostenible",
    color: "text-pos",
    explicacion: "Lo que entrenas esta semana está en línea con lo que tu cuerpo ya tiene asimilado.",
  };
}

/**
 * Carga de entrenamiento (ACWR) en Entrenamiento › Plan.
 *
 * v3 quita el medidor circular: un anillo con "1.12" dentro y la
 * etiqueta "ACWR" no dice qué significa ni respecto a qué, y su color
 * saturado era la parte más llamativa de la página. Lo que informa es la
 * cifra, la zona en palabras y los dos promedios que la producen - una
 * relación, y una relación se lee mejor escrita que en un arco.
 */
export function TrainingLoadCard({ userId }: { userId: number }) {
  const [resultado, setResultado] = useState<TrainingLoad | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

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
  }, [userId, intentos]);

  return (
    <Card>
      <div className="mb-4">
        <h2 className="t-section text-ink">Carga de entrenamiento</h2>
        <p className="t-secondary mt-1 text-ink-3">
          Lo que has entrenado esta semana frente a tu media del último mes.
        </p>
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
      {!error && resultado === null && <LoadingState lines={2} />}
      {!error && resultado && resultado.acwr === null && (
        <EmptyState message="Aún no hay suficientes sesiones registradas para calcular tu carga. Hacen falta varios días de entreno seguidos; se calcula sola en cuanto los haya." />
      )}
      {!error && resultado && resultado.acwr !== null && (
        <Contenido resultado={resultado} acwr={resultado.acwr} />
      )}
    </Card>
  );
}

function Contenido({ resultado, acwr }: { resultado: TrainingLoad; acwr: number }) {
  const zona = zonaPorAcwr(acwr);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="t-hero text-ink">{acwr.toFixed(2)}</p>
        <p className={`t-section mt-1 ${zona.color}`}>{zona.etiqueta}</p>
        <p className="t-body mt-2 max-w-prose text-pretty text-ink-2">{zona.explicacion}</p>
      </div>

      <DataList>
        <DataRow label="Últimos 7 días" nota="media de volumen">
          {resultado.acute_avg_7d?.toFixed(0)}%
        </DataRow>
        <DataRow label="Últimos 28 días" nota="media de volumen">
          {resultado.chronic_avg_28d?.toFixed(0)}%
        </DataRow>
      </DataList>

      {!resultado.datos_suficientes && (
        <p className="t-secondary text-pretty text-warn">
          Solo hay {plural(resultado.dias_con_dato_cronico, "día", "días")} de los 28 que necesita
          el cálculo, así que la cifra es orientativa: se vuelve fiable a medida que acumules
          historial.
        </p>
      )}
    </div>
  );
}
