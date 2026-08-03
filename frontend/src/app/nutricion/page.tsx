"use client";

import { useUser } from "@/lib/UserContext";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Nutrición: objetivo diario de macros (motor de reglas, Capa 1).
 * Pendiente (ver 02-roadmap): diario de comidas real. Investigación ya
 * hecha: wger ya expone un módulo de nutrición completo
 * (ingredient/ingredientinfo = catálogo re-normalizado de Open Food
 * Facts, más nutritionplan/meal/mealitem/nutritiondiary para el
 * registro real) - se reutilizará ese en vez de integrar una tercera
 * fuente externa, mismo patrón que el catálogo de ejercicios.
 */
export default function NutricionPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-2xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Nutrición</h1>
        <p className="text-gray-400 mt-1">Tu objetivo de macros de hoy.</p>
      </header>
      <div className="flex flex-col gap-6">
        <FadeIn>
          <NutritionTargetCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
