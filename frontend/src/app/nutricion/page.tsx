"use client";

import { useUser } from "@/lib/UserContext";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { FoodLogCard } from "@/components/FoodLogCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Nutrición: objetivo diario de macros (motor de reglas, Capa 1) +
 * diario de comidas real vía tu propio wger (Épica de food log, ver
 * 02-roadmap/03-vision-produccion.md - wger ya expone `nutritiondiary`
 * autenticado con token permanente, reutilizado aquí en vez de
 * integrar una tercera fuente externa como MyFitnessPal, descartado
 * tras investigación por no tener API pública viable).
 */
export default function NutricionPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Nutrición</h1>
        <p className="text-text-secondary mt-1">Tu objetivo de macros y diario de comidas.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <FadeIn>
          <NutritionTargetCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <FoodLogCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
