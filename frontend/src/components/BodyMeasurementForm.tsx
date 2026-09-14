"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type BodyMeasurement } from "@/lib/api";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { DataList, DataRow } from "./ui/DataList";
import { Disclosure } from "./ui/Disclosure";
import { FormField, fieldInputClass } from "./ui/FormField";

const METODOS: Record<string, string> = {
  manual: "peso introducido a mano",
  navy: "estimación por cinta (método Navy)",
  feelfit: "báscula Feelfit",
};

/**
 * Registrar una pesada del día (Cuerpo).
 *
 * v3: el resumen de "guardado" era una caja gris con "Método: navy" -
 * el valor crudo de la columna `metodo` y una etiqueta que no dice
 * nada al usuario. Ahora el resultado se confirma con `role="status"`
 * (un lector de pantalla lo anuncia, antes no) y el método se explica
 * en palabras.
 *
 * El rango de % de grasa se mantiene como RANGO: el método Navy no da
 * precisión de decimal único y presentarlo como un número exacto sería
 * falsa precisión.
 */
export function BodyMeasurementForm({
  userId,
  onSaved,
}: {
  userId: number;
  onSaved?: (m: BodyMeasurement) => void;
}) {
  const [pesoKg, setPesoKg] = useState("");
  const [cuelloCm, setCuelloCm] = useState("");
  const [cinturaCm, setCinturaCm] = useState("");
  const [caderaCm, setCaderaCm] = useState("");
  const [resultado, setResultado] = useState<BodyMeasurement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    setResultado(null);
    try {
      const medicion = await api.createBodyMeasurement(userId, {
        target_date: todayLocalDate(),
        peso_kg: Number(pesoKg),
        cuello_cm: cuelloCm ? Number(cuelloCm) : undefined,
        cintura_cm: cinturaCm ? Number(cinturaCm) : undefined,
        cadera_cm: caderaCm ? Number(caderaCm) : undefined,
      });
      setResultado(medicion);
      onSaved?.(medicion);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Card>
      <div className="mb-4">
        <h2 className="t-section text-ink">Registrar medición</h2>
        <p className="t-secondary mt-1 text-pretty text-ink-3">
          Si usas la báscula Feelfit no hace falta: sus pesadas entran solas.
        </p>
      </div>

      <form onSubmit={enviar} className="flex flex-col gap-4">
        <FormField label="Peso de hoy (kg)" htmlFor="peso-kg">
          <input
            id="peso-kg"
            type="number"
            inputMode="decimal"
            step="0.1"
            min="20"
            max="400"
            placeholder="78.4"
            className={fieldInputClass}
            value={pesoKg}
            onChange={(e) => setPesoKg(e.target.value)}
            required
          />
        </FormField>

        <Disclosure summary="Añadir medidas con cinta métrica">
          <p className="t-secondary max-w-prose text-pretty text-ink-3">
            Con cuello y cintura (y cadera, en mujeres) estimamos tu porcentaje de grasa como un
            rango. Nunca como un número exacto: la cinta no da para tanto.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Cuello (cm)" htmlFor="cuello-cm">
              <input
                id="cuello-cm"
                type="number"
                inputMode="decimal"
                step="0.1"
                className={fieldInputClass}
                value={cuelloCm}
                onChange={(e) => setCuelloCm(e.target.value)}
              />
            </FormField>
            <FormField label="Cintura (cm)" htmlFor="cintura-cm">
              <input
                id="cintura-cm"
                type="number"
                inputMode="decimal"
                step="0.1"
                className={fieldInputClass}
                value={cinturaCm}
                onChange={(e) => setCinturaCm(e.target.value)}
              />
            </FormField>
            <FormField label="Cadera (cm)" htmlFor="cadera-cm">
              <input
                id="cadera-cm"
                type="number"
                inputMode="decimal"
                step="0.1"
                className={fieldInputClass}
                value={caderaCm}
                onChange={(e) => setCaderaCm(e.target.value)}
              />
            </FormField>
          </div>
        </Disclosure>

        {error && (
          <p role="alert" className="t-body text-neg">
            {error}
          </p>
        )}

        <div>
          <Button type="submit" disabled={enviando}>
            {enviando ? "Guardando…" : "Guardar medición"}
          </Button>
        </div>
      </form>

      {resultado && (
        <div role="status" className="mt-5">
          <p className="t-body text-pos">Medición guardada.</p>
          <div className="mt-3">
            <DataList>
              <DataRow label="Peso" nota={METODOS[resultado.metodo] ?? resultado.metodo}>
                <span className="tabular">{resultado.peso_kg.toFixed(1)} kg</span>
              </DataRow>
              {resultado.bodyfat_pct_rango_min !== null &&
                resultado.bodyfat_pct_rango_max !== null && (
                  <DataRow label="Grasa estimada" nota="rango, no un valor exacto">
                    <span className="tabular">
                      {resultado.bodyfat_pct_rango_min.toFixed(1)}–
                      {resultado.bodyfat_pct_rango_max.toFixed(1)} %
                    </span>
                  </DataRow>
                )}
            </DataList>
          </div>
        </div>
      )}
    </Card>
  );
}
