"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api, type HealthNarrative } from "@/lib/api";

/** Épica H del plan de expansión (02-roadmap/03-vision-produccion.md):
 * primer punto real donde el coach (Capa 3) aparece fuera de la
 * página "Hoy" - explica el estado de recovery ya decidido, citando
 * los datos reales (nunca decide nada nuevo, ver
 * `coach.health_narrative_service`).
 *
 * Deliberadamente NO renderiza ningún estado de carga/error visible:
 * es un bloque de valor añadido, no crítico para usar la página - si
 * la petición falla o todavía no hay una decisión de recovery ese día
 * (`text`/`source` vienen `None`), simplemente no aparece nada, en vez
 * de un hueco de "Cargando..." o un error que distraiga del resto del
 * contenido (HRV/Body Battery/sueño reales) que sí es crítico.
 */
export function CoachNarrativeBlock({ userId }: { userId: number }) {
  const [narrativa, setNarrativa] = useState<HealthNarrative | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthNarrative(userId)
      .then((res) => {
        if (!cancelado) setNarrativa(res);
      })
      .catch(() => {
        // Bloque no crítico - un fallo aquí no debe interrumpir el
        // resto de la página, ver docstring de arriba.
      });
    return () => {
      cancelado = true;
    };
  }, [userId]);

  if (!narrativa || !narrativa.text) return null;

  return (
    <div className="flex items-start gap-2 rounded-xl border border-accent/20 bg-accent/5 px-4 py-3">
      <Sparkles aria-hidden="true" size={16} className="mt-0.5 shrink-0 text-accent" />
      <p className="text-sm text-foreground text-pretty">{narrativa.text}</p>
    </div>
  );
}
