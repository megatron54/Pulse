"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { BodyMeasurementForm } from "@/components/BodyMeasurementForm";
import { WeightTrendCard } from "@/components/WeightTrendCard";
import { FadeIn } from "@/components/ui/FadeIn";

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
    <main className="p-6 md:p-8 max-w-5xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-white">Cuerpo</h1>
        <p className="text-gray-400 mt-1">Peso, medidas y su evolución.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <FadeIn>
          <BodyMeasurementForm
            userId={user.id}
            onSaved={() => setWeightRefreshKey((k) => k + 1)}
          />
        </FadeIn>
        <FadeIn delay={0.05}>
          <WeightTrendCard userId={user.id} refreshKey={weightRefreshKey} />
        </FadeIn>
      </div>
    </main>
  );
}
