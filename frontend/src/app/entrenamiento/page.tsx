"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { TrainingLoadCard } from "@/components/TrainingLoadCard";
import { ExercisePicker } from "@/components/ExercisePicker";
import { SesionesEntrenamiento } from "@/components/SesionesEntrenamiento";
import { GarminHealthHistoryCard } from "@/components/GarminHealthHistoryCard";
import { HealthMetricsTodayCard } from "@/components/HealthMetricsTodayCard";
import { IntradayMetricCard } from "@/components/IntradayMetricCard";
import { ReadinessTrendCard } from "@/components/ReadinessTrendCard";
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
 * Entrenamiento (Design System v3 - 01-arquitectura/05-design-system-v3.md):
 * fusiona en una sola página lo que antes vivía disperso en 3 rutas
 * (Entrenamiento, Recuperación, Análisis) - queja explícita del usuario
 * ("información desperdigada, sin cohesión entre lo que se muestra y
 * para qué sirve"). Las 4 pestañas comparten el mismo eje temático
 * (todo lo relacionado con entrenar y recuperarse), a diferencia de
 * "Hoy" (vistazo del día), "Cuerpo" (composición corporal/peso frente a
 * objetivos) y "Perfil" (ajustes y conexiones).
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
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
          <TrainingLoadCard userId={user.id} />
          <WeeklyScheduleForm userId={user.id} />
          <div className="lg:col-span-2">
            <ExercisePicker />
          </div>
        </div>
      )}

      {/* Orden de lectura de la pestaña: narrativa (qué significa) →
          cifras de la última medida → tendencia del mes → detalle
          intradía → histórico completo. Una sola columna: son bloques
          que se leen en secuencia, y a 1280px dos columnas obligaban a
          saltar la vista de un lado al otro para seguir el hilo. */}
      {tab === "recuperacion" && (
        <div className="flex flex-col gap-5">
          <FadeIn>
            <CoachNarrativeBlock userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.03}>
            <HealthMetricsTodayCard userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.05}>
            {/* Su sitio, tras salir de "Hoy": una tendencia de 30 días
                no responde "cómo estoy hoy", pero sí "cómo ha ido el
                mes", que es la pregunta de esta pestaña. */}
            <ReadinessTrendCard userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.07}>
            <IntradayMetricCard userId={user.id} />
          </FadeIn>
          <FadeIn delay={0.1}>
            <GarminHealthHistoryCard userId={user.id} />
          </FadeIn>
        </div>
      )}

      {/* También en una columna: `PeriodicSummaryCard` lleva tabla y
          `HabitJournalCard` dos secciones, y a media anchura las dos
          apretaban el contenido (doctrina 3, la tabla necesita su
          ancho). */}
      {tab === "analisis" && (
        <div className="flex flex-col gap-5">
          <PeriodicSummaryCard userId={user.id} refreshKey={0} />
          <HabitJournalCard userId={user.id} />
        </div>
      )}
    </main>
  );
}
