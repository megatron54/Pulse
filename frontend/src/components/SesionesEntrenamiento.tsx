"use client";

import { useState } from "react";
import { Bike, Dumbbell, PersonStanding, Watch } from "lucide-react";
import { GarminActivitiesCard } from "./GarminActivitiesCard";
import { SportActivityHistoryCard } from "./SportActivityHistoryCard";

type Filtro = "todas" | "running" | "ciclismo" | "gimnasio";

const FILTROS: { valor: Filtro; label: string }[] = [
  { valor: "todas", label: "Todas" },
  { valor: "running", label: "Running" },
  { valor: "ciclismo", label: "Ciclismo" },
  { valor: "gimnasio", label: "Gimnasio" },
];

/**
 * Entrenamiento → Sesiones (reconstrucción v2 -
 * 01-arquitectura/04-design-system-v2.md, Fase 4): sustituye a las
 * páginas independientes `/running` `/ciclismo` `/gimnasio` - el
 * backend ya filtraba por `categoria` como query param de un único
 * endpoint (`GET /garmin/activities?categoria=...`), así que tener 3
 * páginas de nivel superior para eso era arquitectura de información
 * innecesaria. Aquí es un filtro dentro de una sola vista.
 */
export function SesionesEntrenamiento({ userId }: { userId: number }) {
  const [filtro, setFiltro] = useState<Filtro>("todas");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 flex-wrap" role="tablist" aria-label="Filtrar por deporte">
        {FILTROS.map(({ valor, label }) => (
          <button
            key={valor}
            role="tab"
            aria-selected={filtro === valor}
            onClick={() => setFiltro(valor)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              filtro === valor
                ? "bg-accent text-white"
                : "bg-surface-muted text-text-secondary hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {filtro === "todas" && <GarminActivitiesCard userId={userId} />}
      {filtro === "running" && (
        <SportActivityHistoryCard
          userId={userId}
          categoria="running"
          titulo="Running"
          icono={PersonStanding}
          mensajeVacio="Todavía no hay sesiones de running sincronizadas."
        />
      )}
      {filtro === "ciclismo" && (
        <SportActivityHistoryCard
          userId={userId}
          categoria="ciclismo"
          titulo="Ciclismo"
          icono={Bike}
          mensajeVacio="Todavía no hay sesiones de ciclismo sincronizadas."
        />
      )}
      {filtro === "gimnasio" && (
        <SportActivityHistoryCard
          userId={userId}
          categoria="gimnasio"
          titulo="Gimnasio"
          icono={Dumbbell}
          mensajeVacio="Todavía no hay sesiones de gimnasio sincronizadas."
        />
      )}
      {filtro === "todas" && (
        <p className="flex items-center gap-1.5 text-xs text-text-secondary">
          <Watch size={12} aria-hidden="true" /> Sincronizado automáticamente de tu reloj Garmin.
        </p>
      )}
    </div>
  );
}
