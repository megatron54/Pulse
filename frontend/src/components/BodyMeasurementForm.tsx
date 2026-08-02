"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type BodyMeasurement } from "@/lib/api";

export function BodyMeasurementForm({ userId }: { userId: number }) {
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Registrar peso / medidas</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          Peso (kg)
          <input
            type="number"
            step="0.1"
            className="border rounded px-2 py-1"
            value={pesoKg}
            onChange={(e) => setPesoKg(Number(e.target.value))}
            required
          />
        </label>
        <p className="text-sm text-gray-500">
          Opcional: añade cuello/cintura(/cadera) para estimar % de grasa (fórmula Navy, siempre
          como rango, nunca un número exacto).
        </p>
        <div className="grid grid-cols-3 gap-2">
          <input
            type="number"
            placeholder="Cuello cm"
            className="border rounded px-2 py-1"
            value={cuelloCm}
            onChange={(e) => setCuelloCm(e.target.value)}
          />
          <input
            type="number"
            placeholder="Cintura cm"
            className="border rounded px-2 py-1"
            value={cinturaCm}
            onChange={(e) => setCinturaCm(e.target.value)}
          />
          <input
            type="number"
            placeholder="Cadera cm (mujer)"
            className="border rounded px-2 py-1"
            value={caderaCm}
            onChange={(e) => setCaderaCm(e.target.value)}
          />
        </div>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="bg-black text-white rounded px-4 py-2 disabled:opacity-50 self-start"
        >
          {submitting ? "Guardando..." : "Guardar"}
        </button>
      </form>
      {resultado && (
        <div className="mt-4 p-3 bg-gray-50 rounded text-sm">
          <p>Método: {resultado.metodo}</p>
          {resultado.bodyfat_pct_rango_min !== null && (
            <p>
              % grasa estimado: {resultado.bodyfat_pct_rango_min.toFixed(1)}% -{" "}
              {resultado.bodyfat_pct_rango_max?.toFixed(1)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}
