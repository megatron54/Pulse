"use client";

import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { TrainingLoadCard } from "@/components/TrainingLoadCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Gestión del plan de entrenamiento: bloque activo, calendario semanal
 * y carga de entrenamiento real (ACWR calculado de verdad a partir del
 * historial de volume_pct, ver services/training_load_service.py -
 * Épica 3 de 02-roadmap/03-vision-produccion.md). Pendiente: historial
 * de sesiones completadas y selector de ejercicios del catálogo de
 * wger - el cliente de wger ya existe (backend/wger_client/) pero
 * todavía no está conectado a ninguna pantalla.
 */
export default function EntrenamientoPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-2xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">
          Entrenamiento
        </h1>
        <p className="text-gray-400 mt-1">Tu plan semanal y bloque activo.</p>
      </header>
      <div className="flex flex-col gap-6">
        <FadeIn>
          <TrainingLoadCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <WeeklyScheduleForm userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
