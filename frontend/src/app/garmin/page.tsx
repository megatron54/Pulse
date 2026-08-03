"use client";

import { Card, CardTitle } from "@/components/ui/Card";
import { FadeIn } from "@/components/ui/FadeIn";

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
  return (
    <main className="p-6 md:p-8 max-w-2xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">Garmin</h1>
        <p className="text-gray-400 mt-1">Estado de la sincronización con tu reloj.</p>
      </header>
      <FadeIn>
        <Card>
          <CardTitle>Sin conectar todavía</CardTitle>
          <p className="text-sm text-gray-300">
            La infraestructura de sincronización (scheduler nocturno, cliente de
            Garmin Connect) ya está construida y probada, pero necesita tus
            credenciales reales para empezar a traer datos - por ahora no hay
            actividades de carrera/ciclismo ni métricas diarias que mostrar aquí,
            y no vamos a inventar ninguna.
          </p>
          <p className="text-sm text-gray-500 mt-4">
            Próximamente, una vez conectado: HRV, Body Battery, entrenamiento
            readiness, y tus actividades (carrera, ciclismo, fuerza) sincronizadas
            automáticamente cada noche.
          </p>
        </Card>
      </FadeIn>
    </main>
  );
}
