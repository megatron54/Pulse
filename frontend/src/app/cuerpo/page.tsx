"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { BodyMeasurementForm } from "@/components/BodyMeasurementForm";
import { BodyCompositionTile } from "@/components/BodyCompositionTile";
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
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-start">
          <FadeIn delay={0.05}>
            <BodyCompositionTile userId={user.id} refreshKey={weightRefreshKey} />
          </FadeIn>
          <FadeIn delay={0.1}>
            <BodyMeasurementForm
              userId={user.id}
              onSaved={() => setWeightRefreshKey((k) => k + 1)}
            />
          </FadeIn>
        </div>
      </div>
    </main>
  );
}
