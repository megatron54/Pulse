"use client";

import { useState } from "react";
import { ActivitiesCard } from "./ActivitiesCard";
import { ChipFilter } from "./ui/ChipFilter";

type Filtro = "todas" | "running" | "ciclismo" | "gimnasio";

const FILTROS = [
  { value: "todas", label: "Todas" },
  { value: "running", label: "Carrera" },
  { value: "ciclismo", label: "Ciclismo" },
  { value: "gimnasio", label: "Gimnasio" },
] as const;

/** Título y mensaje vacío por filtro. El mensaje dice por qué está
 *  vacío (no hay sesiones de ESE deporte) y de dónde vendrían, en vez
 *  de un "sin datos" que no orienta. */
const VISTA: Record<Filtro, { titulo: string; vacio: string }> = {
  todas: {
    titulo: "Todas las sesiones",
    vacio: "Todavía no hay sesiones sincronizadas. Llegan solas desde tu reloj Garmin en cuanto registres una; Pulse no inventa ninguna mientras tanto.",
  },
  running: {
    titulo: "Carrera",
    vacio: "No hay carreras en los últimos 90 días.",
  },
  ciclismo: {
    titulo: "Ciclismo",
    vacio: "No hay salidas en bici en los últimos 90 días.",
  },
  gimnasio: {
    titulo: "Gimnasio",
    vacio: "No hay sesiones de gimnasio en los últimos 90 días.",
  },
};

/**
 * Entrenamiento › Sesiones. Un filtro dentro de una sola vista en vez de
 * las páginas `/running` `/ciclismo` `/gimnasio` de v1: el backend ya
 * filtraba por `categoria` en un único endpoint, así que tres rutas de
 * nivel superior para eso era arquitectura de información innecesaria.
 *
 * v3: se quitó el pie "Sincronizado automáticamente de tu reloj Garmin"
 * con su iconito de reloj - era una nota permanente que no cambia nunca
 * y que solo aparecía en el filtro "Todas"; esa información vive ahora
 * donde se puede actuar sobre ella (Perfil › Conexiones) y en el estado
 * vacío, que es cuando de verdad hace falta saberlo.
 */
export function SesionesEntrenamiento({ userId }: { userId: number }) {
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const vista = VISTA[filtro];

  return (
    <div className="flex flex-col gap-5">
      <ChipFilter
        options={FILTROS}
        value={filtro}
        onChange={setFiltro}
        ariaLabel="Filtrar por deporte"
      />
      <ActivitiesCard
        // `key` fuerza el remontaje al cambiar de deporte: sin ello se
        // veían un instante las sesiones del filtro anterior bajo el
        // título nuevo.
        key={filtro}
        userId={userId}
        categoria={filtro === "todas" ? undefined : filtro}
        titulo={vista.titulo}
        mensajeVacio={vista.vacio}
      />
    </div>
  );
}
