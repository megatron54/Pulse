"use client";

import { useState } from "react";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { OnboardingForm } from "@/components/OnboardingForm";
import { BodyMeasurementForm } from "@/components/BodyMeasurementForm";
import { ReadinessCheckinForm } from "@/components/ReadinessCheckinForm";
import { DailySessionCard } from "@/components/DailySessionCard";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { WeightTrendCard } from "@/components/WeightTrendCard";
import { ReadinessTrendCard } from "@/components/ReadinessTrendCard";
import { FadeIn } from "@/components/ui/FadeIn";

export default function Home() {
  const { user, loading, error, createUser } = useCurrentUser();
  // Incrementados tras un guardado exitoso en el formulario hermano
  // correspondiente, para forzar a las tarjetas de tendencia a recargar
  // su historial (hallazgo real de pruebas manuales: sin esto, la
  // tendencia se quedaba mostrando "sin datos" hasta recargar la página
  // entera, aunque el dato ya estuviera guardado en el backend).
  const [readinessRefreshKey, setReadinessRefreshKey] = useState(0);
  const [weightRefreshKey, setWeightRefreshKey] = useState(0);

  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center text-gray-400">
        Cargando...
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex-1 flex flex-col justify-center p-8">
        <h1 className="font-display text-3xl font-bold text-center mb-8 tracking-wide text-white">
          PULSE
        </h1>
        {error && <p className="text-red-400 text-sm text-center mb-4">{error}</p>}
        <OnboardingForm onCreate={createUser} />
      </main>
    );
  }

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
    <WeeklyScheduleForm key="schedule" userId={user.id} />,
    <BodyMeasurementForm
      key="body-measurement"
      userId={user.id}
      onSaved={() => setWeightRefreshKey((k) => k + 1)}
    />,
    <WeightTrendCard key="weight-trend" userId={user.id} refreshKey={weightRefreshKey} />,
    <NutritionTargetCard key="nutrition" userId={user.id} />,
  ];

  return (
    <main className="flex-1 p-8 max-w-3xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">PULSE</h1>
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
