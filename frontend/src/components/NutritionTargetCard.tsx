"use client";

import { useState } from "react";
import { TriangleAlert } from "lucide-react";
import { api, ApiError, todayLocalDate, type NutritionTarget } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { AnimatedNumber } from "./ui/AnimatedNumber";
import { Disclosure } from "./ui/Disclosure";
import { DonutChart } from "./ui/DonutChart";
import { MacroBar } from "./ui/MacroBar";
import { PALETA } from "@/lib/theme";

// Reutiliza los mismos colores centralizados en lib/theme.ts (code-review
// M1) - no tienen un color "oficial" para nutrición en WHOOP, se
// reasignan por analogía visual: teal para el macro "positivo" por
// excelencia, azul de recovery para carbohidratos, sleep-blue para grasa.
const MACRO_COLOR = {
  proteina: PALETA.accent,
  carbohidratos: PALETA.accent,
  grasa: PALETA.sleep,
};

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
      {error && <p className="text-recovery-low text-sm mt-2">{error}</p>}
      {resultado && (
        <div className="mt-5 flex flex-col gap-4">
          <div>
            <span className="text-3xl font-bold text-foreground">
              <AnimatedNumber value={resultado.kcal_objetivo} />
            </span>
            <span className="ml-1.5 text-sm text-text-secondary">kcal objetivo</span>
          </div>
          <MacroBar
            segments={[
              {
                label: "Proteína",
                grams: resultado.proteina_g,
                kcal: resultado.proteina_g * 4,
                color: MACRO_COLOR.proteina,
              },
              {
                label: "Carbohidratos",
                grams: resultado.carbohidratos_g,
                kcal: resultado.carbohidratos_g * 4,
                color: MACRO_COLOR.carbohidratos,
              },
              {
                label: "Grasa",
                grams: resultado.grasa_g,
                kcal: resultado.grasa_g * 9,
                color: MACRO_COLOR.grasa,
              },
            ]}
          />
          <Disclosure summary="Ver como anillo">
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
                  <span className="text-xl font-bold text-foreground">
                    <AnimatedNumber value={resultado.kcal_objetivo} />
                  </span>
                  <span className="text-[10px] uppercase tracking-wide text-text-secondary">kcal</span>
                </>
              }
            />
          </Disclosure>
          <p className="text-sm text-text-secondary uppercase tracking-wide">
            Fase aplicada: {resultado.fase_aplicada}
          </p>
          {resultado.deficit_pausado_por_guardrail && (
            <p className="text-sm text-recovery-medium mt-2 flex items-center gap-1.5">
              <TriangleAlert aria-hidden="true" size={14} />
              {/* Épica I del plan de expansión: la pausa puede
                  dispararse por readiness categórico sostenido O por
                  sleep_score crudo sostenido (mismo guardrail,
                  extendido) - el texto no distingue el motivo exacto
                  porque el backend no expone hoy cuál de los dos
                  disparó (solo el booleano), ver services.nutrition_service. */}
              Déficit pausado automáticamente por recuperación (readiness o sueño) sostenida por debajo de lo saludable.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
