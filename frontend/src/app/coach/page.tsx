"use client";

import { MessageCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

/**
 * Coach (reconstrucción v2 - 01-arquitectura/04-design-system-v2.md,
 * Fase 6, PENDIENTE): chat conversacional con IA. Requiere backend
 * nuevo (`POST /users/{id}/coach/chat`, no existe todavía - ver plan
 * de la Fase 6) que arme el prompt con los datos reales del usuario
 * (recovery de hoy, sesiones, tendencias) sobre `coach/gemini_client.py`
 * ya existente. Esta página es un placeholder honesto en vez de una
 * maqueta de chat que no funciona de verdad - "unknown is not zero"
 * aplicado también a features, no solo a datos.
 */
export default function CoachPage() {
  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader title="Coach" subtitle="Chat conversacional con tu coach de IA." />
      <Card className="flex flex-col items-center gap-4 py-16 text-center">
        <div className="flex size-14 items-center justify-center rounded-full bg-surface-muted">
          <MessageCircle size={26} aria-hidden="true" className="text-text-secondary" />
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-foreground font-medium">Todavía no está construido.</p>
          <p className="text-sm text-text-secondary max-w-sm text-pretty">
            El chat conversacional con IA es la Fase 6 del plan de reconstrucción - requiere un
            endpoint nuevo en el backend que todavía no existe. Esta página no aparenta una
            función que no funciona de verdad.
          </p>
        </div>
      </Card>
    </main>
  );
}
