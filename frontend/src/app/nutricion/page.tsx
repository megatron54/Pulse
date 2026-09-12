"use client";

import { useUser } from "@/lib/UserContext";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { NutritionPlanCard } from "@/components/NutritionPlanCard";
import { FadeIn } from "@/components/ui/FadeIn";
import { PageHeader } from "@/components/ui/PageHeader";

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
      <PageHeader title="Nutrición" subtitle="Tu plan y tu objetivo de macros." />
      <div className="flex flex-col gap-6">
        <FadeIn>
          <NutritionTargetCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <NutritionPlanCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
