"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type BodyMeasurement } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { fechaRelativa } from "@/lib/fechas";
import { useUser } from "@/lib/UserContext";
import {
  CLASE_POR_ESTADO,
  estadoAguaCorporal,
  estadoGrasaCorporal,
  estadoImc,
} from "@/lib/rangosCorporales";
import { Card, CardTitle } from "./ui/Card";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { MetricGrid, StatTile } from "./ui/StatTile";

/** Un año de historial, no 90 días: la última pesada puede ser de hace
 *  meses, y con la ventana corta esta tarjeta desaparecía entera en vez
 *  de mostrar la composición conocida con su fecha. */
const DIAS_CONSULTA = 365;

/**
 * Composición completa de bioimpedancia (báscula Feelfit): antes se
 * descartaba todo salvo peso y % de grasa (ver services/
 * feelfit_sync_service.py), pese a que la báscula la reporta en cada
 * medición. Solo se muestra si el registro más reciente trae al menos
 * un campo de composición - "unknown is not zero", una medición manual
 * de solo peso no debe mostrar un tile vacío.
 */
export function BodyCompositionTile({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  /** Ver docstring de `ReadinessTrendCard` para el mismo patrón: el
   * padre incrementa esto tras guardar una medición nueva en el
   * formulario hermano. */
  refreshKey?: number;
}) {
  const usuario = useUser();
  const [mediciones, setMediciones] = useState<BodyMeasurement[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getBodyMeasurementHistory(userId, DIAS_CONSULTA)
      .then((datos) => {
        if (!cancelado) setMediciones(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar tu composición corporal."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey, intentos]);

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          setError(null);
          setIntentos((n) => n + 1);
        }}
      />
    );
  }

  if (mediciones === null) return <LoadingState lines={1} />;

  // Orden explícito antes de `.at(-1)`: `dedupeUltimaPorDia` devuelve el
  // orden de inserción del Map y no promete nada (ver ese módulo), así
  // que sin ordenar aquí "la más reciente" dependía del orden en que
  // llegara la respuesta.
  const ultimo = dedupeUltimaPorDia(mediciones)
    .sort((a, b) => a.fecha.localeCompare(b.fecha))
    .at(-1);
  if (!ultimo) return null;

  const grasaEsRango =
    ultimo.bodyfat_pct_rango_min != null &&
    ultimo.bodyfat_pct_rango_max != null &&
    ultimo.bodyfat_pct_rango_min !== ultimo.bodyfat_pct_rango_max;

  const tieneComposicion =
    ultimo.bodyfat_pct_rango_min != null ||
    ultimo.muscle_kg != null ||
    ultimo.bone_kg != null ||
    ultimo.water_pct != null ||
    ultimo.bmi != null;
  if (!tieneComposicion) return null;

  return (
    <Card>
      <CardTitle>Composición corporal</CardTitle>
      {/* Cinco cifras sin fecha no dicen de cuándo son, y la última
          pesada puede ser de hace semanas (doctrina 6). */}
      <p className="t-secondary -mt-2 mb-4 text-ink-3">
        Última medida: {fechaRelativa(ultimo.fecha).toLowerCase()}.
      </p>
      {/* v3: rejilla que se adapta, no un rail con scroll horizontal
          (doctrina 4 - el rail cortaba el último tile a 390px y nada
          indicaba que hubiera más a la derecha). Sin iconos: eran
          decorativos y de colores, parte del aspecto que se rechaza. */}
      <MetricGrid>
        {ultimo.bodyfat_pct_rango_min != null &&
          (grasaEsRango ? (
            // Rango real (método Navy), no un punto: la precisión falsa
            // está prohibida, así que este caso no puede usar StatTile.
            // El color sí se puede aplicar al extremo superior del
            // rango: es el dato más desfavorable, y es el mismo criterio
            // (rango de ACE) que usa el caso de abajo con un solo punto.
            <div className="flex w-full flex-col gap-1">
              <span className="t-micro text-ink-3">% Grasa</span>
              <p
                className={`t-metric ${CLASE_POR_ESTADO[estadoGrasaCorporal(ultimo.bodyfat_pct_rango_max!, usuario.sexo)]}`}
              >
                {ultimo.bodyfat_pct_rango_min.toFixed(1)}–
                {ultimo.bodyfat_pct_rango_max!.toFixed(1)}
                <span className="t-body text-ink-2">%</span>
              </p>
            </div>
          ) : (
            <StatTile
              label="% Grasa"
              value={ultimo.bodyfat_pct_rango_min}
              unit="%"
              decimals={1}
              valueClassName={
                CLASE_POR_ESTADO[estadoGrasaCorporal(ultimo.bodyfat_pct_rango_min, usuario.sexo)]
              }
            />
          ))}
        {ultimo.muscle_kg != null && (
          <StatTile label="Músculo" value={ultimo.muscle_kg} unit=" kg" decimals={1} />
        )}
        {ultimo.bone_kg != null && (
          <StatTile label="Hueso" value={ultimo.bone_kg} unit=" kg" decimals={1} />
        )}
        {ultimo.water_pct != null && (
          <StatTile
            label="Agua"
            value={ultimo.water_pct}
            unit="%"
            decimals={1}
            valueClassName={CLASE_POR_ESTADO[estadoAguaCorporal(ultimo.water_pct, usuario.sexo)]}
          />
        )}
        {/* "IMC", no "BMI": el nombre del campo del backend es inglés,
            la interfaz no (doctrina 9). */}
        {ultimo.bmi != null && (
          <StatTile
            label="IMC"
            value={ultimo.bmi}
            decimals={1}
            valueClassName={CLASE_POR_ESTADO[estadoImc(ultimo.bmi)]}
          />
        )}
      </MetricGrid>
      <p className="t-secondary mt-4 text-ink-3">
        Las dos últimas cifras van en kilogramos sin rango de referencia: sin tu altura y
        complexión, un umbral de «normal» en kg sería inventado.
      </p>
    </Card>
  );
}
