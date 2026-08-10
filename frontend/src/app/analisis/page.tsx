"use client";

import { useUser } from "@/lib/UserContext";
import { PeriodicSummaryCard } from "@/components/PeriodicSummaryCard";
import { HabitJournalCard } from "@/components/HabitJournalCard";
import { WeightTrendCard } from "@/components/WeightTrendCard";

/**
 * Análisis (reconstrucción v2 - 01-arquitectura/04-design-system-v2.md,
 * Fase 5, ENTREGA PARCIAL): vista de tendencias históricas. Reutiliza
 * `PeriodicSummaryCard` (resumen semanal de readiness/carga/peso) y
 * `HabitJournalCard` (correlación de hábitos), que antes vivían
 * dispersos en "Hoy". Pendiente (Fase 5 completa, no entregado en esta
 * sesión): tendencias de HRV/sueño/body battery/resting HR
 * dedicadas y volumen de entrenamiento por deporte con selector de
 * rango temporal - hoy viven en Recuperación y Entrenamiento
 * respectivamente, sin unificar todavía en esta vista.
 */
export default function AnalisisPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Análisis</h1>
        <p className="text-text-secondary mt-1">Tendencias de tu recovery, carga y peso.</p>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <PeriodicSummaryCard userId={user.id} refreshKey={0} />
        <WeightTrendCard userId={user.id} />
        <div className="lg:col-span-2">
          <HabitJournalCard userId={user.id} />
        </div>
      </div>
    </main>
  );
}
