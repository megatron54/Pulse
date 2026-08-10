"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bike,
  Dumbbell,
  HeartPulse,
  PersonStanding,
  Ruler,
  Sun,
  Utensils,
  Watch,
  Weight,
} from "lucide-react";

/**
 * Navegación principal de Pulse (rediseño de arquitectura de
 * información a petición explícita del usuario: "no veo diferentes
 * paginas, menus"). Responsive real, no solo un layout que se encoge:
 * - Desktop (md+): barra lateral fija con las 9 secciones.
 * - Móvil (<md): barra de pestañas fija abajo, patrón estándar de app
 *   de fitness (WHOOP, Strava, etc. usan esto mismo en vez de un menú
 *   hamburguesa, porque la navegación se usa varias veces al día).
 *   Con 9 secciones (Épica G añadió running/ciclismo/gimnasio) se
 *   desliza horizontalmente en vez de repartir el ancho a partes
 *   iguales - un gradiente en el borde derecho (`nav-scroll-fade`,
 *   ver globals.css) da la pista visual de que hay más pestañas fuera
 *   de vista, ya que `overflow-x-auto` por sí solo no lo comunica.
 *
 * Iconos SVG (lucide-react) en vez de emoji (code-review M4): el
 * renderizado de emoji varía entre plataformas (monocromo vs. color,
 * variantes ZWJ) - inaceptable para un diseño pulido tipo WHOOP.
 */
const SECCIONES = [
  { href: "/", label: "Hoy", labelCorto: "Hoy", Icono: Sun },
  { href: "/salud", label: "Salud", labelCorto: "Salud", Icono: HeartPulse },
  { href: "/entrenamiento", label: "Entrenamiento", labelCorto: "Entreno", Icono: Dumbbell },
  { href: "/running", label: "Running", labelCorto: "Running", Icono: PersonStanding },
  { href: "/ciclismo", label: "Ciclismo", labelCorto: "Ciclismo", Icono: Bike },
  { href: "/gimnasio", label: "Gimnasio", labelCorto: "Gimnasio", Icono: Weight },
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
      {/* Sidebar de escritorio: material translúcido (apple-design §12
          "build nav/toolbars/sheets as translucent layers"), no una
          columna opaca con borde recto. El borde derecho pasa de un
          1px sólido a un hairline translúcido (`border-surface-border`
          ya es rgba tras el repintado de globals.css). */}
      <nav
        aria-label="Navegación principal"
        className="material-surface hidden md:flex md:flex-col md:w-56 md:shrink-0 md:border-r md:border-surface-border md:p-4 md:gap-1"
      >
        <span className="text-xl font-semibold tracking-tight text-white mb-6 px-2">Pulse</span>
        {SECCIONES.map(({ href, label, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 active:scale-[0.98] ${focusRing} ${
                activa ? "bg-teal/15 text-teal" : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Icono aria-hidden="true" size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Barra de pestañas de móvil. Con 9 secciones (Épica G añadió
          running/ciclismo/gimnasio), repartir el ancho a partes iguales
          (flex-1) dejaría cada pestaña casi ilegible - se desliza
          horizontalmente en su lugar (ancho fijo por item, swipe para
          ver el resto), en vez de comprimir todo para que quepa. El
          div envolvente + el degradado son solo la PISTA VISUAL de que
          hay más pestañas fuera de vista (hallazgo de @code-reviewer:
          `overflow-x-auto` por sí solo no lo comunica) - no afecta a
          teclado/lectores de pantalla, cada `<Link>` sigue siendo
          alcanzable con Tab y el navegador auto-desplaza al enfocarlo. */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-10">
        <nav
          aria-label="Navegación principal (móvil)"
          className="material-surface relative flex overflow-x-auto border-t border-surface-border pb-[env(safe-area-inset-bottom)]"
        >
          {SECCIONES.map(({ href, labelCorto, Icono }) => {
            const activa = esRutaActiva(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={activa ? "page" : undefined}
                className={`flex w-16 shrink-0 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium leading-tight transition-transform active:scale-95 ${focusRing} ${
                  activa ? "text-teal" : "text-gray-400"
                }`}
              >
                <Icono aria-hidden="true" size={20} />
                <span className="truncate max-w-full px-0.5">{labelCorto}</span>
              </Link>
            );
          })}
        </nav>
        <div
          aria-hidden="true"
          className="pointer-events-none absolute right-0 top-0 bottom-[env(safe-area-inset-bottom)] w-8 bg-gradient-to-l from-black to-transparent"
        />
      </div>
    </>
  );
}
