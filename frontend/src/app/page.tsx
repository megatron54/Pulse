"use client";

import { useCurrentUser } from "@/lib/useCurrentUser";
import { OnboardingForm } from "@/components/OnboardingForm";
import { BodyMeasurementForm } from "@/components/BodyMeasurementForm";
import { ReadinessCheckinForm } from "@/components/ReadinessCheckinForm";
import { DailySessionCard } from "@/components/DailySessionCard";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { WeightTrendCard } from "@/components/WeightTrendCard";
import { ReadinessTrendCard } from "@/components/ReadinessTrendCard";

export default function Home() {
  const { user, loading, error, createUser } = useCurrentUser();

  if (loading) {
    return <main className="p-8 text-center text-gray-500">Cargando...</main>;
  }

  if (!user) {
    return (
      <main className="p-8">
        <h1 className="text-2xl font-bold text-center mb-6">Pulse</h1>
        {error && <p className="text-red-600 text-sm text-center mb-4">{error}</p>}
        <OnboardingForm onCreate={createUser} />
      </main>
    );
  }

  return (
    <main className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Pulse</h1>
      <p className="text-gray-500 mb-8">Hola, {user.nombre}.</p>
      <div className="flex flex-col gap-6">
        <ReadinessCheckinForm userId={user.id} />
        <ReadinessTrendCard userId={user.id} />
        <DailySessionCard userId={user.id} />
        <WeeklyScheduleForm userId={user.id} />
        <BodyMeasurementForm userId={user.id} />
        <WeightTrendCard userId={user.id} />
        <NutritionTargetCard userId={user.id} />
      </div>
    </main>
  );
}
