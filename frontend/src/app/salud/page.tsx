"use client";

import { useUser } from "@/lib/UserContext";
import { GarminHealthHistoryCard } from "@/components/GarminHealthHistoryCard";
import { HealthMetricsSummaryRow } from "@/components/HealthMetricsSummaryRow";
import { IntradayMetricCard } from "@/components/IntradayMetricCard";
import { CoachNarrativeBlock } from "@/components/CoachNarrativeBlock";
import { PageHeader } from "@/components/ui/PageHeader";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Salud: histórico completo de recovery de Garmin (Épica E del plan
 * de expansión, 02-roadmap/03-vision-produccion.md) - VFC, Body
 * Battery, sueño, estrés, pulso en reposo y VO2max, con selector de
 * rango temporal. El resumen corto de estas mismas métricas vive en
 * el dashboard "Hoy" (Épica J); esta página es el DETALLE completo.
 * El bloque de coach (Épica H) explica el estado de recovery ya
 * decidido citando estos mismos datos reales - nunca decide nada
 * nuevo, ver `coach.health_narrative_service`.
 */
export default function SaludPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader
        title="Recuperación"
        subtitle="Histórico de recovery, sacado directamente de Garmin."
      />
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
    </main>
  );
}
