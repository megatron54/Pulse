"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { TrainingLoadCard } from "@/components/TrainingLoadCard";
import { ExercisePicker } from "@/components/ExercisePicker";
import { SesionesEntrenamiento } from "@/components/SesionesEntrenamiento";
import { GarminHealthHistoryCard } from "@/components/GarminHealthHistoryCard";
import { HealthMetricsSummaryRow } from "@/components/HealthMetricsSummaryRow";
import { IntradayMetricCard } from "@/components/IntradayMetricCard";
import { CoachNarrativeBlock } from "@/components/CoachNarrativeBlock";
import { PeriodicSummaryCard } from "@/components/PeriodicSummaryCard";
import { HabitJournalCard } from "@/components/HabitJournalCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { FadeIn } from "@/components/ui/FadeIn";

type Tab = "sesiones" | "plan" | "recuperacion" | "analisis";

const TABS = [
  { value: "sesiones", label: "Sesiones" },
  { value: "plan", label: "Plan" },
  { value: "recuperacion", label: "Recuperación" },
  { value: "analisis", label: "Análisis" },
] as const;

/**
 * Entrenamiento (reconstrucción v2 - 01-arquitectura/04-design-system-v2.md,
 * Fase 5 completa): fusiona en una sola página lo que antes vivía
 * disperso en 3 rutas (Entrenamiento, Recuperación, Análisis) - queja
 * explícita del usuario ("información desperdigada, sin cohesión entre
 * lo que se muestra y para qué sirve"). Las 4 pestañas comparten el
 * mismo eje temático (todo lo relacionado con entrenar y recuperarse),
 * a diferencia de "Hoy" (vistazo del día) y "Cuerpo" (composición
 * corporal/peso frente a objetivos).
 *
 * "Sesiones" = lo que hice, "Plan" = lo que planifico, "Recuperación" =
 * detalle completo de Garmin (antes /salud), "Análisis" = tendencias
 * agregadas semana a semana (antes /analisis, sin el `WeightTrendCard`
 * que quedaba duplicado con Cuerpo - el peso vive solo en Cuerpo).
 */
export default function EntrenamientoPage() {
  const user = useUser();
  const [tab, setTab] = useState<Tab>("sesiones");

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader
        title="Entrenamiento"
        actions={<SegmentedControl options={TABS} value={tab} onChange={setTab} ariaLabel="Sección" />}
      />

      {tab === "sesiones" && <SesionesEntrenamiento userId={user.id} />}

      {tab === "plan" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <TrainingLoadCard userId={user.id} />
          <WeeklyScheduleForm userId={user.id} />
          <div className="lg:col-span-2">
            <ExercisePicker />
          </div>
        </div>
      )}

      {tab === "recuperacion" && (
        <div className="flex flex-col gap-6">
          <FadeIn>
            <CoachNarrativeBlock userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.03}>
            <HealthMetricsSummaryRow userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.05}>
            <IntradayMetricCard userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.1}>
            <GarminHealthHistoryCard userId={user.id} />
          </FadeIn>
        </div>
      )}

      {tab === "analisis" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <PeriodicSummaryCard userId={user.id} refreshKey={0} />
          <div className="lg:col-span-2">
            <HabitJournalCard userId={user.id} />
          </div>
        </div>
      )}
    </main>
  );
}
