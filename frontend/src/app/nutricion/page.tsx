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
    <main className="p-6 md:p-8 max-w-2xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Nutrición</h1>
        <p className="text-gray-400 mt-1">Tu objetivo de macros y diario de comidas.</p>
      </header>
      <div className="flex flex-col gap-6">
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
