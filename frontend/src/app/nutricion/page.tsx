"use client";

import { useUser } from "@/lib/UserContext";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Nutrición: objetivo diario de macros (motor de reglas, Capa 1).
 *
 * El diario de comidas vía wger se ELIMINÓ por petición explícita del
 * usuario ("no quiero lo del wger, no se qué es y no lo quiero") - a
 * la espera de conectar MyFitnessPal, o del motor de recomendación
 * nutricional propio (calorías/macros/planes de déficit-superávit-
 * mantenimiento con duración determinada, basado en datos reales de
 * Garmin + tendencia de peso) que sustituirá por completo a wger como
 * "nutricionista personal" en vez de solo ser un proxy de un catálogo
 * de ingredientes externo.
 */
export default function NutricionPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Nutrición</h1>
        <p className="text-text-secondary mt-1">Tu objetivo de macros.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <FadeIn>
          <NutritionTargetCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
