"use client";

import { useUser } from "@/lib/UserContext";
import { Card, CardTitle } from "@/components/ui/Card";
import { FadeIn } from "@/components/ui/FadeIn";
import { GarminActivitiesCard } from "@/components/GarminActivitiesCard";

/**
 * Estado de la integración con Garmin. Deliberadamente NO muestra
 * datos falsos ni una maqueta de gráficas vacías: el scheduler y el
 * cliente de sincronización ya existen y están probados (backend/
 * scheduler/, backend/garmin_sync/), pero sin credenciales reales
 * (Fase H del roadmap, bloqueada por el usuario) no hay ningún dato
 * que mostrar todavía. Esta pantalla comunica ese estado con
 * honestidad en vez de aparentar una integración terminada.
 */
export default function GarminPage() {
  const user = useUser();

  return (
    <main className="p-6 md:p-8 max-w-5xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Garmin</h1>
        <p className="text-gray-400 mt-1">Estado de la sincronización con tu reloj.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <FadeIn>
          <Card>
            <CardTitle>Sincronización</CardTitle>
            <p className="text-sm text-gray-300">
              El scheduler nocturno sincroniza recovery y actividades automáticamente
              cada noche una vez emparejada tu cuenta. Algunas métricas (HRV, sleep
              score) tardan unos días en poblarse tras emparejar un dispositivo
              nuevo - no se inventa ningún valor mientras tanto.
            </p>
          </Card>
        </FadeIn>
        <FadeIn delay={0.05}>
          <GarminActivitiesCard userId={user.id} />
        </FadeIn>
      </div>
    </main>
  );
}
