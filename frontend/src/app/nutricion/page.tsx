"use client";

import Link from "next/link";
import { useUser } from "@/lib/UserContext";
import { NutritionTargetCard } from "@/components/NutritionTargetCard";
import { NutritionPlanCard } from "@/components/NutritionPlanCard";
import { Card } from "@/components/ui/Card";
import { FadeIn } from "@/components/ui/FadeIn";
import { PageHeader } from "@/components/ui/PageHeader";

/**
 * Nutrición: plan de fase (Capa 0, motor propio) + objetivo diario de
 * macros (motor de reglas, Capa 1).
 *
 * El diario de comidas vía wger se ELIMINÓ por petición explícita del
 * usuario ("no quiero lo del wger, no se qué es y no lo quiero") - a
 * la espera de conectar MyFitnessPal. El motor de recomendación de
 * fases nutricionales (déficit/superávit/mantenimiento con duración
 * determinada, basado en datos reales de Garmin + tendencia de peso)
 * sustituye a wger como "nutricionista personal": el sistema
 * RECOMIENDA la fase, el usuario CONFIRMA - nunca se aplica sola.
 */
export default function NutricionPage() {
  const user = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader title="Nutrición" subtitle="Tu plan y tu objetivo de macros." />
      <div className="flex flex-col gap-5">
        <FadeIn>
          <NutritionTargetCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.05}>
          <NutritionPlanCard userId={user.id} />
        </FadeIn>
        <FadeIn delay={0.1}>
          <ComoSeComprueba />
        </FadeIn>
      </div>
    </main>
  );
}

/**
 * Qué hacer con el objetivo de arriba (doctrina 7 aplicada a una página
 * entera, no a una tarjeta vacía).
 *
 * Esta pantalla eran dos tarjetas y medio metro de fondo vacío, y el
 * hueco escondía una pregunta que la app no contestaba en ningún sitio:
 * si Pulse no sabe lo que como, ¿para qué me da un objetivo y cómo sé si
 * lo estoy cumpliendo? La respuesta es el peso, que es lo único medido
 * de verdad aquí - así que se escribe, con el enlace a donde se mira.
 *
 * No repite la tendencia de peso: esa gráfica vive solo en Cuerpo (ya se
 * quitó una copia de Análisis por duplicada). Aquí va la frase y la
 * puerta.
 */
function ComoSeComprueba() {
  return (
    <Card>
      <h2 className="t-section mb-3 text-ink">Cómo saber si funciona</h2>
      <div className="flex flex-col items-start gap-4">
        <p className="t-body max-w-prose text-pretty text-ink-2">
          Pulse no apunta lo que comes: el objetivo de arriba es la referencia que cumples tú, y
          la comprobación es tu peso. Si estás en déficit y en dos o tres semanas no baja, el
          objetivo de calorías se te queda alto; si estás en superávit y no sube, se te queda
          bajo. Una semana suelta no dice nada: pesa la tendencia, no la pesada de hoy.
        </p>
        <Link
          href="/cuerpo"
          className="t-body inline-flex min-h-11 items-center rounded-md border border-line px-4 text-ink hover:bg-canvas focus:outline-none focus-visible:ring-2 focus-visible:ring-ink"
        >
          Ver mi tendencia de peso
        </Link>
      </div>
    </Card>
  );
}
