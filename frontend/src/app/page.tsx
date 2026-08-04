"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { ReadinessCheckinForm } from "@/components/ReadinessCheckinForm";
import { DailySessionCard } from "@/components/DailySessionCard";
import { ReadinessTrendCard } from "@/components/ReadinessTrendCard";
import { HabitJournalCard } from "@/components/HabitJournalCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Página "Hoy" (dashboard diario, ruta raíz): lo que un usuario mira
 * cada mañana - check-in de recuperación, su tendencia reciente, y qué
 * toca entrenar hoy. El resto de secciones (entrenamiento, nutrición,
 * cuerpo, garmin) viven en sus propias rutas - ver `components/Nav.tsx`
 * para la arquitectura de información completa.
 */
export default function HoyPage() {
  const user = useUser();
  // Incrementado tras un check-in exitoso, para forzar a la tarjeta de
  // tendencia a recargar su historial (ver docstring de refreshKey en
  // ReadinessTrendCard/WeightTrendCard - mismo patrón).
  const [readinessRefreshKey, setReadinessRefreshKey] = useState(0);

  const tarjetas = [
    <ReadinessCheckinForm
      key="readiness-checkin"
      userId={user.id}
      onResult={() => setReadinessRefreshKey((k) => k + 1)}
    />,
    <ReadinessTrendCard
      key="readiness-trend"
      userId={user.id}
      refreshKey={readinessRefreshKey}
    />,
    <DailySessionCard key="session" userId={user.id} />,
    <HabitJournalCard key="habits" userId={user.id} />,
  ];

  return (
    <main className="p-6 md:p-8 max-w-2xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Hoy</h1>
        <p className="text-gray-400 mt-1">Hola, {user.nombre}.</p>
      </header>
      <div className="flex flex-col gap-6">
        {tarjetas.map((tarjeta, i) => (
          <FadeIn key={tarjeta.key} delay={i * 0.05}>
            {tarjeta}
          </FadeIn>
        ))}
      </div>
    </main>
  );
}
