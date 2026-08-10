"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type BodyMeasurement } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";

const inputClass =
  "border border-surface-border bg-surface-muted rounded-lg px-3 py-2 text-foreground placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent";

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
      <CardTitle>Registrar peso / medidas</CardTitle>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm text-text-secondary">
          Peso (kg)
          <input
            type="number"
            step="0.1"
            className={inputClass}
            value={pesoKg}
            onChange={(e) => setPesoKg(Number(e.target.value))}
            required
          />
        </label>
        <p className="text-sm text-text-secondary">
          Opcional: añade cuello/cintura (y cadera si eres mujer) para estimar % de grasa
          (fórmula Navy, siempre como rango, nunca un número exacto).
        </p>
        <div className="grid grid-cols-3 gap-2">
          <input
            type="number"
            step="0.1"
            placeholder="Cuello (cm)"
            aria-label="Cuello en centímetros"
            className={inputClass}
            value={cuelloCm}
            onChange={(e) => setCuelloCm(e.target.value)}
          />
          <input
            type="number"
            step="0.1"
            placeholder="Cintura (cm)"
            aria-label="Cintura en centímetros"
            className={inputClass}
            value={cinturaCm}
            onChange={(e) => setCinturaCm(e.target.value)}
          />
          <input
            type="number"
            step="0.1"
            placeholder="Cadera (cm)"
            aria-label="Cadera en centímetros, solo para mujer"
            className={inputClass}
            value={caderaCm}
            onChange={(e) => setCaderaCm(e.target.value)}
          />
        </div>
        {error && <p className="text-recovery-low text-sm">{error}</p>}
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
