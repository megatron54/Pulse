"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { ReadinessCheckinForm } from "@/components/ReadinessCheckinForm";
import { DailySessionCard } from "@/components/DailySessionCard";
import { ReadinessTrendCard } from "@/components/ReadinessTrendCard";
import { HabitJournalCard } from "@/components/HabitJournalCard";
import { PeriodicSummaryCard } from "@/components/PeriodicSummaryCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Página "Hoy" - dashboard diario real (rediseño a petición explícita
 * del usuario: "pantalla principal con un dashboard interactivo...
 * estilo WHOOP/Samsung Health/Apple Health"). Layout en grid tipo
 * "bento" en vez de una columna única apilada: el check-in de
 * recuperación (con el `RecoveryRing`) es el elemento hero que ocupa
 * más espacio, el resto de tarjetas se distribuyen alrededor según su
 * densidad de contenido - mismo patrón que la pantalla "Hoy" de estas
 * apps de referencia, donde no todo pesa lo mismo visualmente.
 */
export default function HoyPage() {
  const user = useUser();
  // Incrementado tras un check-in exitoso, para forzar a la tarjeta de
  // tendencia a recargar su historial (ver docstring de refreshKey en
  // ReadinessTrendCard/WeightTrendCard - mismo patrón).
  const [readinessRefreshKey, setReadinessRefreshKey] = useState(0);

  return (
    <main className="p-6 md:p-8 max-w-6xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Hoy</h1>
        <p className="text-gray-400 mt-1">Hola, {user.nombre}.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 items-start">
        <FadeIn delay={0} className="md:col-span-2">
          <ReadinessCheckinForm
            userId={user.id}
            onResult={() => setReadinessRefreshKey((k) => k + 1)}
          />
        </FadeIn>
        <FadeIn delay={0.05}>
          <DailySessionCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.1} className="md:col-span-2 xl:col-span-1">
          <ReadinessTrendCard userId={user.id} refreshKey={readinessRefreshKey} />
        </FadeIn>
        <FadeIn delay={0.15}>
          <PeriodicSummaryCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.2} className="md:col-span-2 xl:col-span-1">
          <HabitJournalCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
