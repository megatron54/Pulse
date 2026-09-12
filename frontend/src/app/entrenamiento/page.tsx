"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { TrainingLoadCard } from "@/components/TrainingLoadCard";
import { ExercisePicker } from "@/components/ExercisePicker";
import { SesionesEntrenamiento } from "@/components/SesionesEntrenamiento";
import { PageHeader } from "@/components/ui/PageHeader";
import { SegmentedControl } from "@/components/ui/SegmentedControl";

type Tab = "sesiones" | "plan";

const TABS = [
  { value: "sesiones", label: "Sesiones" },
  { value: "plan", label: "Plan" },
] as const;

/**
 * Entrenamiento (reconstrucción v2 - 01-arquitectura/04-design-system-v2.md,
 * Fase 4): separa "lo que hice" (Sesiones reales de Garmin) de "lo que
 * planifico" (Plan semanal) - antes ambos vivían mezclados en la misma
 * página sin distinción clara, y las sesiones reales de Garmin no
 * tenían ningún lugar prominente donde vivir.
 */
export default function EntrenamientoPage() {
  const user = useUser();
  const [tab, setTab] = useState<Tab>("sesiones");

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader
        title="Entrenamiento"
        actions={
          <SegmentedControl options={TABS} value={tab} onChange={setTab} ariaLabel="Sesiones o plan" />
        }
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
    </main>
  );
}
