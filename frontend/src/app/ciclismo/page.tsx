"use client";

import { Bike } from "lucide-react";
import { useUser } from "@/lib/UserContext";
import { SportActivityHistoryCard } from "@/components/SportActivityHistoryCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Ciclismo (Épica G del plan de expansión, 02-roadmap/
 * 03-vision-produccion.md) - histórico de actividades de ciclismo
 * (road/mountain/indoor/gravel/virtual) ya sincronizadas de Garmin,
 * filtrado por el backend (Épica D). Coach por deporte: pendiente
 * (Épica H, requiere generalizar la Capa 3 primero).
 */
export default function CiclismoPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-5xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Ciclismo</h1>
        <p className="text-gray-400 mt-1">Tus sesiones de bici, sacadas de Garmin.</p>
      </header>
      <div className="grid grid-cols-1 gap-6 items-start">
        <FadeIn>
          <SportActivityHistoryCard
            userId={user.id}
            categoria="ciclismo"
            titulo="Sesiones de ciclismo"
            icono={Bike}
            mensajeVacio="Sin sesiones de ciclismo sincronizadas todavía. El scheduler nocturno las trae automáticamente en cuanto haya alguna nueva."
          />
        </FadeIn>
      </div>
    </main>
  );
}
