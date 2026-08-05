"use client";

import { useState } from "react";
import { TriangleAlert } from "lucide-react";
import { api, ApiError, todayLocalDate, type NutritionTarget } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { AnimatedNumber } from "./ui/AnimatedNumber";
import { DonutChart } from "./ui/DonutChart";
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

function LeyendaMacro({ nombre, gramos, color }: { nombre: string; gramos: number; color: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        aria-hidden="true"
        className="w-2.5 h-2.5 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />
      <span className="text-gray-300">{nombre}</span>
      <span className="font-display font-semibold text-white ml-auto">
        {gramos.toFixed(0)} g
      </span>
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
      <Button onClick={fetchTarget} disabled={loading}>
        {loading ? "Calculando..." : "Calcular macros de hoy"}
      </Button>
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
      {resultado && (
        <div className="mt-5">
          <div className="flex items-center gap-5">
            <DonutChart
              segments={[
                {
                  nombre: "Proteína",
                  valor: resultado.proteina_g * 4,
                  color: MACRO_COLOR.proteina,
                },
                {
                  nombre: "Carbohidratos",
                  valor: resultado.carbohidratos_g * 4,
                  color: MACRO_COLOR.carbohidratos,
                },
                { nombre: "Grasa", valor: resultado.grasa_g * 9, color: MACRO_COLOR.grasa },
              ]}
              size={110}
              centro={
                <>
                  <span className="font-display text-xl font-bold text-white">
                    <AnimatedNumber value={resultado.kcal_objetivo} />
                  </span>
                  <span className="text-[10px] uppercase tracking-wide text-gray-400">kcal</span>
                </>
              }
            />
            <div className="flex-1 flex flex-col gap-2.5">
              <LeyendaMacro
                nombre="Proteína"
                gramos={resultado.proteina_g}
                color={MACRO_COLOR.proteina}
              />
              <LeyendaMacro
                nombre="Carbohidratos"
                gramos={resultado.carbohidratos_g}
                color={MACRO_COLOR.carbohidratos}
              />
              <LeyendaMacro nombre="Grasa" gramos={resultado.grasa_g} color={MACRO_COLOR.grasa} />
            </div>
          </div>
          <p className="text-sm text-gray-400 mt-4 uppercase tracking-wide">
            Fase aplicada: {resultado.fase_aplicada}
          </p>
          {resultado.deficit_pausado_por_guardrail && (
            <p className="text-sm text-recovery-medium mt-2 flex items-center gap-1.5">
              <TriangleAlert aria-hidden="true" size={14} />
              Déficit pausado automáticamente por mala recuperación sostenida.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
