"use client";

import { useCallback, useEffect, useState } from "react";

export const TEMAS = ["light", "dark", "system"] as const;
export type Tema = (typeof TEMAS)[number];

export const CLAVE_TEMA = "pulse_theme";

export const ETIQUETA_TEMA: Record<Tema, string> = {
  light: "Claro",
  dark: "Oscuro",
  system: "Sistema",
};

/**
 * Tema claro/oscuro/sistema con control explícito del usuario (Design
 * System v3): hasta v2 el modo dependía solo de `prefers-color-scheme`
 * y no había forma de forzarlo, que es una de las carencias concretas
 * que motivó la página de Perfil.
 *
 * El tema resuelto vive en `data-theme` del <html>, no en una clase de
 * React, porque lo escribe también el script inline de `layout.tsx`
 * antes del primer paint (sin destello). Aquí solo se sincroniza el
 * control de la UI con esa misma fuente.
 */
export function aplicarTema(tema: Tema): void {
  const oscuro =
    tema === "dark" ||
    (tema === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = oscuro ? "dark" : "light";
}

function leerTemaGuardado(): Tema {
  const guardado = localStorage.getItem(CLAVE_TEMA);
  return TEMAS.includes(guardado as Tema) ? (guardado as Tema) : "system";
}

export function useTheme() {
  // `system` como estado inicial en SSR y en el primer render del
  // cliente: leer localStorage aquí daría un desajuste de hidratación.
  // El valor real se lee en el efecto de abajo.
  const [tema, setTemaState] = useState<Tema>("system");

  useEffect(() => {
    // Sincronización con un sistema externo (localStorage), el caso que
    // la propia regla documenta como legítimo: no se puede leer en el
    // render inicial sin provocar un desajuste de hidratación, porque
    // el servidor no tiene localStorage. Mismo patrón, y mismo
    // `eslint-disable`, que en `useCurrentUser`.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTemaState(leerTemaGuardado());
  }, []);

  // Con `system`, seguir al sistema operativo EN VIVO (no solo al
  // cargar): si el usuario cambia el modo del sistema con la app
  // abierta, la app cambia con él.
  useEffect(() => {
    if (tema !== "system") return;
    const consulta = window.matchMedia("(prefers-color-scheme: dark)");
    const alCambiar = () => aplicarTema("system");
    consulta.addEventListener("change", alCambiar);
    return () => consulta.removeEventListener("change", alCambiar);
  }, [tema]);

  const setTema = useCallback((siguiente: Tema) => {
    localStorage.setItem(CLAVE_TEMA, siguiente);
    aplicarTema(siguiente);
    setTemaState(siguiente);
  }, []);

  return { tema, setTema };
}
