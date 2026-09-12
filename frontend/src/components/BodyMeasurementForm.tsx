"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type BodyMeasurement } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { Disclosure } from "./ui/Disclosure";
import { FormField, fieldInputClass } from "./ui/FormField";

export function BodyMeasurementForm({
  userId,
  onSaved,
}: {
  userId: number;
  onSaved?: (m: BodyMeasurement) => void;
}) {
  const [pesoKg, setPesoKg] = useState(80);
  const [cuelloCm, setCuelloCm] = useState<string>("");
  const [cinturaCm, setCinturaCm] = useState<string>("");
  const [caderaCm, setCaderaCm] = useState<string>("");
  const [resultado, setResultado] = useState<BodyMeasurement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResultado(null);
    try {
      const medicion = await api.createBodyMeasurement(userId, {
        target_date: todayLocalDate(),
        peso_kg: pesoKg,
        cuello_cm: cuelloCm ? Number(cuelloCm) : undefined,
        cintura_cm: cinturaCm ? Number(cinturaCm) : undefined,
        cadera_cm: caderaCm ? Number(caderaCm) : undefined,
      });
      setResultado(medicion);
      onSaved?.(medicion);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardTitle>Registrar peso</CardTitle>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <FormField label="Peso (kg)" htmlFor="peso-kg">
          <input
            id="peso-kg"
            type="number"
            step="0.1"
            className={fieldInputClass}
            value={pesoKg}
            onChange={(e) => setPesoKg(Number(e.target.value))}
            required
          />
        </FormField>
        <Disclosure summary="Medida manual opcional (método Navy)">
          <p className="text-xs text-text-secondary -mt-1">
            Solo hace falta si no usas la báscula Feelfit: con cuello y cintura (y cadera si eres
            mujer) estimamos tu % de grasa como un rango, nunca un número exacto.
          </p>
          <div className="grid grid-cols-3 gap-2">
            <FormField label="Cuello" htmlFor="cuello-cm">
              <input
                id="cuello-cm"
                type="number"
                step="0.1"
                placeholder="cm"
                className={fieldInputClass}
                value={cuelloCm}
                onChange={(e) => setCuelloCm(e.target.value)}
              />
            </FormField>
            <FormField label="Cintura" htmlFor="cintura-cm">
              <input
                id="cintura-cm"
                type="number"
                step="0.1"
                placeholder="cm"
                className={fieldInputClass}
                value={cinturaCm}
                onChange={(e) => setCinturaCm(e.target.value)}
              />
            </FormField>
            <FormField label="Cadera (mujer)" htmlFor="cadera-cm">
              <input
                id="cadera-cm"
                type="number"
                step="0.1"
                placeholder="cm"
                className={fieldInputClass}
                value={caderaCm}
                onChange={(e) => setCaderaCm(e.target.value)}
              />
            </FormField>
          </div>
        </Disclosure>
        {error && (
          <p role="alert" className="text-recovery-low text-sm">
            {error}
          </p>
        )}
        <Button type="submit" disabled={submitting} className="self-start">
          {submitting ? "Guardando..." : "Guardar"}
        </Button>
      </form>
      {resultado && (
        <div className="mt-4 p-3 bg-surface-muted rounded-lg text-sm text-text-secondary">
          <p>Método: {resultado.metodo}</p>
          {resultado.bodyfat_pct_rango_min !== null && (
            <p className="text-lg text-foreground mt-1">
              {resultado.bodyfat_pct_rango_min.toFixed(1)}% -{" "}
              {resultado.bodyfat_pct_rango_max?.toFixed(1)}%{" "}
              <span className="text-sm text-text-secondary font-sans">grasa estimada</span>
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
