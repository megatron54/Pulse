"use client";

import { useUser } from "@/lib/UserContext";
import { DailySessionCard } from "@/components/DailySessionCard";
import { IntradayMetricCard } from "@/components/IntradayMetricCard";
import { RecoveryStatusCard } from "@/components/RecoveryStatusCard";
import { FadeIn } from "@/components/ui/FadeIn";
import { PageHeader } from "@/components/ui/PageHeader";

/**
 * Página "Hoy" (Design System v3). Responsabilidad única, del cuadro de
 * arquitectura de información: **cómo estoy hoy y qué hago hoy. Nada
 * más.**
 *
 * Se han quitado dos bloques, los dos por petición explícita del
 * usuario respaldada por la auditoría:
 *
 *  - **`ReadinessTrendCard`** ("Tendencia de readiness, 30 días"): eran
 *    30 círculos de color sin eje, sin fechas y sin cifras, con
 *    `flex-wrap` (el día 27 caía debajo del día 1, rompiendo la lectura
 *    de línea temporal) y con el significado accesible solo por `title`
 *    al pasar el cursor, inexistente en móvil. Una tendencia de 30 días
 *    no es "hoy": su sitio es Entrenamiento › Recuperación, rehecha con
 *    eje y cifras.
 *  - **`NutritionTargetCard`**: en esta página era una tarjeta cuyo
 *    único contenido era un botón "Calcular macros de hoy". Una tarjeta
 *    que no informa de nada y exige pulsar para calcular algo que el
 *    motor puede resolver solo. Su sitio es Nutrición, donde el
 *    objetivo se muestra ya calculado.
 *
 * Y se ha traído uno, `IntradayMetricCard` ("Minuto a minuto de hoy"),
 * que vivía en Entrenamiento › Recuperación: su eje es el día en curso,
 * o sea exactamente la pregunta de esta página. Con él, "Hoy" pasa de
 * dos bloques de texto y cifras a tener la forma del día dibujada -
 * cuándo se ha gastado la energía y cuándo ha subido el pulso -, que es
 * lo que el usuario pedía al decir que la pantalla se le quedaba vacía y
 * sin gráficas. No es una tendencia: sigue siendo hoy.
 */
export default function HoyPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader title="Hoy" subtitle={`Hola, ${user.nombre}.`} />
      <div className="flex flex-col gap-5">
        <FadeIn delay={0}>
          <RecoveryStatusCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <DailySessionCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.1}>
          <IntradayMetricCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
