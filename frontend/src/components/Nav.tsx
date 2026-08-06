"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dumbbell, HeartPulse, Ruler, Sun, Utensils, Watch } from "lucide-react";

/**
 * Navegación principal de Pulse (rediseño de arquitectura de
 * información a petición explícita del usuario: "no veo diferentes
 * paginas, menus"). Responsive real, no solo un layout que se encoge:
 * - Desktop (md+): barra lateral fija con las 5 secciones.
 * - Móvil (<md): barra de pestañas fija abajo, patrón estándar de app
 *   de fitness (WHOOP, Strava, etc. usan esto mismo en vez de un menú
 *   hamburguesa, porque la navegación se usa varias veces al día).
 *
 * Iconos SVG (lucide-react) en vez de emoji (code-review M4): el
 * renderizado de emoji varía entre plataformas (monocromo vs. color,
 * variantes ZWJ) - inaceptable para un diseño pulido tipo WHOOP.
 */
const SECCIONES = [
  { href: "/", label: "Hoy", labelCorto: "Hoy", Icono: Sun },
  { href: "/salud", label: "Salud", labelCorto: "Salud", Icono: HeartPulse },
  { href: "/entrenamiento", label: "Entrenamiento", labelCorto: "Entreno", Icono: Dumbbell },
  { href: "/nutricion", label: "Nutrición", labelCorto: "Nutrición", Icono: Utensils },
  { href: "/cuerpo", label: "Cuerpo", labelCorto: "Cuerpo", Icono: Ruler },
  { href: "/garmin", label: "Garmin", labelCorto: "Garmin", Icono: Watch },
] as const;

function esRutaActiva(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-inset";

export function Nav() {
  const pathname = usePathname();

  return (
    <>
      {/* Sidebar de escritorio */}
      <nav
        aria-label="Navegación principal"
        className="hidden md:flex md:flex-col md:w-56 md:shrink-0 md:border-r md:border-surface-border md:p-4 md:gap-1"
      >
        <span className="font-display text-xl font-bold tracking-wide text-white mb-6 px-2">
          PULSE
        </span>
        {SECCIONES.map(({ href, label, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${focusRing} ${
                activa
                  ? "bg-teal/10 text-teal"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Icono aria-hidden="true" size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Barra de pestañas de móvil */}
      <nav
        aria-label="Navegación principal (móvil)"
        className="md:hidden fixed bottom-0 left-0 right-0 z-10 flex border-t border-surface-border bg-surface/95 backdrop-blur pb-[env(safe-area-inset-bottom)]"
      >
        {SECCIONES.map(({ href, labelCorto, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium leading-tight ${focusRing} ${
                activa ? "text-teal" : "text-gray-400"
              }`}
            >
              <Icono aria-hidden="true" size={20} />
              <span className="truncate max-w-full px-0.5">{labelCorto}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
