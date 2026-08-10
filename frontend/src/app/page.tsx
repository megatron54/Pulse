"use client";

import { useUser } from "@/lib/UserContext";
import { DailySessionCard } from "@/components/DailySessionCard";
import { ReadinessTrendCard } from "@/components/ReadinessTrendCard";
import { RecoveryStatusCard } from "@/components/RecoveryStatusCard";
import { FadeIn } from "@/components/ui/FadeIn";

/**
 * Página "Hoy" - reconstrucción v2 (01-arquitectura/04-design-system-v2.md,
 * Fase 2). Jerarquía de 3 niveles explícita, en vez del grid "bento" de
 * cajas del mismo tamaño de la iteración anterior:
 *
 * Nivel 1 (hero): estado de recovery de HOY, 100% automático de
 * Garmin - `RecoveryStatusCard` sustituye por completo al check-in
 * manual (`ReadinessCheckinForm`, ELIMINADO) y a los anillos
 * (`RecoveryRing`, ELIMINADO).
 * Nivel 2 (soporte): sesión de entrenamiento recomendada/realizada hoy.
 * Nivel 3 (glanceable): mini-tendencia de recovery de 7 días.
 *
 * Sin scroll forzado en desktop para el contenido de nivel 1-2 (cabe
 * en una pantalla de portátil estándar); nivel 3 puede quedar bajo el
 * pliegue sin que eso sea un problema (es contenido secundario).
 */
export default function HoyPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Hoy</h1>
        <p className="text-text-secondary mt-1">Hola, {user.nombre}.</p>
      </header>
      <div className="flex flex-col gap-6">
        <FadeIn delay={0}>
          <RecoveryStatusCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <DailySessionCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.1}>
          <ReadinessTrendCard userId={user.id} refreshKey={0} />
        </FadeIn>
      </div>
    </main>
  );
}
