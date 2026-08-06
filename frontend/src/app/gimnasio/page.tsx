"use client";

import { Dumbbell } from "lucide-react";
import { useUser } from "@/lib/UserContext";
import { SportActivityHistoryCard } from "@/components/SportActivityHistoryCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Gimnasio (Épica G del plan de expansión, 02-roadmap/
 * 03-vision-produccion.md) - histórico de sesiones de fuerza
 * (strength_training/indoor_cardio/fitness_equipment) ya sincronizadas
 * de Garmin, filtrado por el backend (Épica D). Detalle de
 * series/reps por sesión (`get_activity_exercise_sets`, ya
 * identificado en el punto 9 del doc vivo) queda fuera de esta épica -
 * requiere una ingesta nueva, no solo un filtro sobre lo ya ingerido.
 * Coach por deporte: pendiente (Épica H).
 */
export default function GimnasioPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-5xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Gimnasio</h1>
        <p className="text-gray-400 mt-1">Tus sesiones de fuerza, sacadas de Garmin.</p>
      </header>
      <div className="grid grid-cols-1 gap-6 items-start">
        <FadeIn>
          <SportActivityHistoryCard
            userId={user.id}
            categoria="gimnasio"
            titulo="Sesiones de gimnasio"
            icono={Dumbbell}
            mensajeVacio="Sin sesiones de gimnasio sincronizadas todavía. El scheduler nocturno las trae automáticamente en cuanto haya alguna nueva."
          />
        </FadeIn>
      </div>
    </main>
  );
}
