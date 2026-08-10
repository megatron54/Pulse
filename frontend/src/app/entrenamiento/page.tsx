"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { WeeklyScheduleForm } from "@/components/WeeklyScheduleForm";
import { TrainingLoadCard } from "@/components/TrainingLoadCard";
import { ExercisePicker } from "@/components/ExercisePicker";
import { SesionesEntrenamiento } from "@/components/SesionesEntrenamiento";

type Tab = "sesiones" | "plan";

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
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Entrenamiento</h1>
        <div className="mt-4 flex gap-1 border-b border-surface-border">
          <TabButton activo={tab === "sesiones"} onClick={() => setTab("sesiones")}>
            Sesiones
          </TabButton>
          <TabButton activo={tab === "plan"} onClick={() => setTab("plan")}>
            Plan
          </TabButton>
        </div>
      </header>

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

function TabButton({
  activo,
  onClick,
  children,
}: {
  activo: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      role="tab"
      aria-selected={activo}
      onClick={onClick}
      className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
        activo ? "border-accent text-accent" : "border-transparent text-text-secondary hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}
