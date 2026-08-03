"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type NutritionTarget } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { PALETA } from "@/lib/theme";

// Reutiliza los mismos colores centralizados en lib/theme.ts (code-review
// M1) - no tienen un color "oficial" para nutrición en WHOOP, se
// reasignan por analogía visual: teal para el macro "positivo" por
// excelencia, azul de recovery para carbohidratos, sleep-blue para grasa.
const MACRO_COLOR = {
  proteina: PALETA.teal,
  carbohidratos: PALETA.recoveryBlue,
  grasa: PALETA.sleep,
};

function MacroBar({
  nombre,
  gramos,
  kcalPorGramo,
  kcalTotal,
  color,
}: {
  nombre: string;
  gramos: number;
  kcalPorGramo: number;
  kcalTotal: number;
  color: string;
}) {
  const kcalDelMacro = gramos * kcalPorGramo;
  const porcentaje = kcalTotal > 0 ? Math.min(100, (kcalDelMacro / kcalTotal) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-300">{nombre}</span>
        <span className="font-display font-semibold text-white">{gramos.toFixed(0)} g</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${porcentaje}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

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
    <Card>
      <CardTitle>Objetivo nutricional de hoy</CardTitle>
      <button
        onClick={fetchTarget}
        disabled={loading}
        className="bg-teal text-black font-semibold rounded-lg px-4 py-2.5 disabled:bg-surface disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:scale-100 transition-transform hover:scale-[1.02] active:scale-[0.98]"
      >
        {loading ? "Calculando..." : "Calcular macros de hoy"}
      </button>
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
      {resultado && (
        <div className="mt-5">
          <p className="font-display text-4xl font-bold text-white">
            {resultado.kcal_objetivo.toFixed(0)}
            <span className="text-lg text-gray-400 font-sans font-normal ml-2">kcal</span>
          </p>
          <div className="flex flex-col gap-3 mt-5">
            <MacroBar
              nombre="Proteína"
              gramos={resultado.proteina_g}
              kcalPorGramo={4}
              kcalTotal={resultado.kcal_objetivo}
              color={MACRO_COLOR.proteina}
            />
            <MacroBar
              nombre="Carbohidratos"
              gramos={resultado.carbohidratos_g}
              kcalPorGramo={4}
              kcalTotal={resultado.kcal_objetivo}
              color={MACRO_COLOR.carbohidratos}
            />
            <MacroBar
              nombre="Grasa"
              gramos={resultado.grasa_g}
              kcalPorGramo={9}
              kcalTotal={resultado.kcal_objetivo}
              color={MACRO_COLOR.grasa}
            />
          </div>
          <p className="text-sm text-gray-400 mt-4 uppercase tracking-wide">
            Fase aplicada: {resultado.fase_aplicada}
          </p>
          {resultado.deficit_pausado_por_guardrail && (
            <p className="text-sm text-recovery-medium mt-2 flex items-center gap-1.5">
              ⚠️ Déficit pausado automáticamente por mala recuperación sostenida.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
