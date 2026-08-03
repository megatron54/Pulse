"use client";

import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Gestión del plan de entrenamiento: bloque activo y calendario
 * semanal. Pendiente (ver 02-roadmap): historial de sesiones
 * completadas y selector de ejercicios del catálogo de wger - el
 * cliente de wger ya existe (backend/wger_client/) pero todavía no
 * está conectado a ninguna pantalla.
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
          <WeeklyScheduleForm userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
