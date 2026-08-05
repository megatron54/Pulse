"use client";

import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { TrainingLoadCard } from "@/components/TrainingLoadCard";
import { ExercisePicker } from "@/components/ExercisePicker";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Gestión del plan de entrenamiento: bloque activo, calendario semanal,
 * carga de entrenamiento real (ACWR calculado de verdad a partir del
 * historial de volume_pct, ver services/training_load_service.py -
 * Épica 3 de 02-roadmap/03-vision-produccion.md) y explorador del
 * catálogo de ejercicios de wger (Épica 6 - cliente construido hace
 * tiempo, nunca conectado a una pantalla hasta ahora). Pendiente:
 * historial de sesiones completadas, y añadir ejercicios concretos a
 * una sesión (requiere decidir el modelo de "sesión con ejercicios").
 */
export default function EntrenamientoPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-6xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">
          Entrenamiento
        </h1>
        <p className="text-gray-400 mt-1">Tu plan semanal y bloque activo.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <FadeIn>
          <TrainingLoadCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <WeeklyScheduleForm userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.1} className="md:col-span-2">
          <ExercisePicker />
        </FadeIn>
      </div>
    </main>
  );
}
