"use client";

import { useEffect, useState } from "react";
import { api, type HealthNarrative } from "@/lib/api";

/** Épica H del plan de expansión (02-roadmap/03-vision-produccion.md):
 * primer punto real donde el coach (Capa 3) aparece fuera de la
 * página "Hoy" - explica el estado de recovery ya decidido, citando
 * los datos reales (nunca decide nada nuevo, ver
 * `coach.health_narrative_service`).
 *
 * `categoria` (Épica G2, 02-roadmap/04-plan-desarrollo-siguiente-fase.md,
 * Fase 1) reutiliza el mismo bloque para el slot de coach por deporte
 * (`coach.sport_narrative_service`) en vez de duplicar el componente -
 * mismo contrato text/source, solo cambia el endpoint consultado.
 *
 * Deliberadamente NO renderiza ningún estado de carga/error visible:
 * es un bloque de valor añadido, no crítico para usar la página - si
 * la petición falla o todavía no hay una decisión ese día (`text`/
 * `source` vienen `None`), simplemente no aparece nada, en vez de un
 * hueco de "Cargando..." o un error que distraiga del resto del
 * contenido que sí es crítico.
 */
export function CoachNarrativeBlock({
  userId,
  categoria,
}: {
  userId: number;
  categoria?: "running" | "ciclismo" | "gimnasio";
}) {
  const [narrativa, setNarrativa] = useState<HealthNarrative | null>(null);

  useEffect(() => {
    let cancelado = false;
    const peticion = categoria
      ? api.getGarminSportNarrative(userId, categoria)
      : api.getGarminHealthNarrative(userId);
    peticion
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
  }, [userId, categoria]);

  if (!narrativa || !narrativa.text) return null;

  // v3: párrafo, no una tarjeta teñida con un icono de chispas dentro
  // de otra tarjeta. La caja `bg-accent/5` + `Sparkles` era justo el
  // patrón "generado por IA" que se rechaza, y además anidaba un
  // contenedor dentro de otro (doctrina 2). Quien lo encuadra ahora es
  // el divisor de 1px de la tarjeta que lo contiene.
  return <p className="t-body text-pretty text-ink-2">{narrativa.text}</p>;
}
