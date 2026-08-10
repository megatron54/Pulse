"use client";

import { useUser } from "@/lib/UserContext";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { NutritionPlanCard } from "@/components/NutritionPlanCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Nutrición: plan de fase (Capa 0, motor propio) + objetivo diario de
 * macros (motor de reglas, Capa 1).
 *
 * El diario de comidas vía wger se ELIMINÓ por petición explícita del
 * usuario ("no quiero lo del wger, no se qué es y no lo quiero") - a
 * la espera de conectar MyFitnessPal. El motor de recomendación de
 * fases nutricionales (déficit/superávit/mantenimiento con duración
 * determinada, basado en datos reales de Garmin + tendencia de peso)
 * sustituye a wger como "nutricionista personal": el sistema
 * RECOMIENDA la fase, el usuario CONFIRMA - nunca se aplica sola.
 */
export default function NutricionPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Nutrición</h1>
        <p className="text-text-secondary mt-1">Tu plan y tu objetivo de macros.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <FadeIn>
          <NutritionPlanCard userId={user.id} />
        </FadeIn>
        <FadeIn>
          <NutritionTargetCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
