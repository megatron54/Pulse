"use client";

import { ETIQUETA_TEMA, TEMAS, useTheme } from "@/lib/useTheme";
import { Card, CardTitle } from "./ui/Card";
import { SegmentedControl } from "./ui/SegmentedControl";

const OPCIONES = TEMAS.map((tema) => ({ value: tema, label: ETIQUETA_TEMA[tema] }));

/**
 * Apariencia: claro / oscuro / sistema (petición explícita del
 * usuario). Hasta v2 el modo dependía SOLO de `prefers-color-scheme`,
 * sin ninguna forma de forzarlo desde la app.
 *
 * El cambio se aplica al instante y se recuerda en `localStorage`; el
 * script inline de `layout.tsx` lo relee antes del primer paint, así
 * que al volver a abrir la app no hay destello de claro antes de
 * oscuro. Con "Sistema" la app sigue al sistema operativo en vivo
 * (`matchMedia`), no solo al cargar.
 */
export function AppearanceCard() {
  const { tema, setTema } = useTheme();

  return (
    <Card>
      <CardTitle>Apariencia</CardTitle>
      <div className="flex flex-col gap-3">
        <SegmentedControl
          options={OPCIONES}
          value={tema}
          onChange={setTema}
          ariaLabel="Tema de la aplicación"
        />
        <p className="t-secondary text-pretty text-ink-2">
          {tema === "system"
            ? "Pulse sigue el modo claro u oscuro de tu dispositivo."
            : `Pulse usa siempre el modo ${ETIQUETA_TEMA[tema].toLowerCase()}, aunque tu dispositivo cambie.`}
        </p>
      </div>
    </Card>
  );
}
