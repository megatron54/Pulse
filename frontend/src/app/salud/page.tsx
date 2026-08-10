"use client";

import { useUser } from "@/lib/UserContext";
import { GarminHealthHistoryCard } from "@/components/GarminHealthHistoryCard";
import { CoachNarrativeBlock } from "@/components/CoachNarrativeBlock";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Salud: histórico completo de recovery de Garmin (Épica E del plan
 * de expansión, 02-roadmap/03-vision-produccion.md) - VFC, Body
 * Battery, sueño, estrés, pulso en reposo y VO2max, con selector de
 * rango temporal. El resumen corto de estas mismas métricas vive en
 * el dashboard "Hoy" (Épica J); esta página es el DETALLE completo.
 * El bloque de coach (Épica H) explica el estado de recovery ya
 * decidido citando estos mismos datos reales - nunca decide nada
 * nuevo, ver `coach.health_narrative_service`.
 */
export default function SaludPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-5xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-white">Salud</h1>
        <p className="text-gray-400 mt-1">Histórico de recovery, sacado directamente de Garmin.</p>
      </header>
      <div className="grid grid-cols-1 gap-6 items-start">
        <FadeIn>
          <CoachNarrativeBlock userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <GarminHealthHistoryCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
