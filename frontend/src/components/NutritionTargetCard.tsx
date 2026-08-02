"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type NutritionTarget } from "@/lib/api";

export function NutritionTargetCard({ userId }: { userId: number }) {
  const [resultado, setResultado] = useState<NutritionTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchTarget() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.getNutritionTarget(userId, todayLocalDate());
      setResultado(r);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 400
            ? "Registra tu peso primero (sección de arriba)."
            : err.message
          : String(err)
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Objetivo nutricional de hoy</h2>
      <button
        onClick={fetchTarget}
        disabled={loading}
        className="bg-black text-white rounded px-4 py-2 disabled:opacity-50"
      >
        {loading ? "Calculando..." : "Calcular macros de hoy"}
      </button>
      {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      {resultado && (
        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <p>Calorías: {resultado.kcal_objetivo.toFixed(0)} kcal</p>
          <p>Proteína: {resultado.proteina_g.toFixed(0)} g</p>
          <p>Carbohidratos: {resultado.carbohidratos_g.toFixed(0)} g</p>
          <p>Grasa: {resultado.grasa_g.toFixed(0)} g</p>
          <p className="col-span-2 text-gray-500">Fase aplicada: {resultado.fase_aplicada}</p>
          {resultado.deficit_pausado_por_guardrail && (
            <p className="col-span-2 text-orange-600">
              ⚠️ Déficit pausado automáticamente por mala recuperación sostenida.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
