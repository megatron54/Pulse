"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { BodyMeasurementForm } from "@/components/BodyMeasurementForm";
import { BodyCompositionTile } from "@/components/BodyCompositionTile";
import { BodyGoalInsightCard } from "@/components/BodyGoalInsightCard";
import { FeelfitConnectForm } from "@/components/FeelfitConnectForm";
import { WeightTrendCard } from "@/components/WeightTrendCard";
import { FadeIn } from "@/components/ui/FadeIn";
import { PageHeader } from "@/components/ui/PageHeader";

/**
 * Cuerpo: peso, medidas y su tendencia. Pendiente (ver 02-roadmap,
 * Fase G): fotos de progreso. Investigación ya hecha - conclusión
 * importante: una foto NO puede dar un % de grasa fiable con
 * MediaPipe.js (landmarks 2D monoculares, sin profundidad real);
 * cuando se construya, mostrará solo una tendencia relativa de
 * silueta (ratios hombro/cintura/cadera), nunca un número de %grasa -
 * el método Navy con cinta métrica sigue siendo la única fuente de
 * verdad para eso, coherente con el principio "nunca falsa precisión"
 * ya aplicado aquí mismo.
 */
export default function CuerpoPage() {
  const user = useUser();
  const [weightRefreshKey, setWeightRefreshKey] = useState(0);

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader title="Cuerpo" subtitle="Peso, medidas y su evolución." />
      <div className="flex flex-col gap-6">
        <FadeIn>
          <WeightTrendCard userId={user.id} refreshKey={weightRefreshKey} />
        </FadeIn>
        <FadeIn delay={0.03}>
          <BodyGoalInsightCard userId={user.id} />
        </FadeIn>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <FadeIn delay={0.05} className="lg:flex-1 lg:min-w-0 empty:hidden">
            <BodyCompositionTile userId={user.id} refreshKey={weightRefreshKey} />
          </FadeIn>
          <FadeIn delay={0.1} className="flex flex-col gap-6 lg:w-[22rem] lg:shrink-0">
            <BodyMeasurementForm
              userId={user.id}
              onSaved={() => setWeightRefreshKey((k) => k + 1)}
            />
            <FeelfitConnectForm userId={user.id} />
          </FadeIn>
        </div>
      </div>
    </main>
  );
}
