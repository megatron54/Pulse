"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dumbbell, Ruler, Sun, User, Utensils } from "lucide-react";

/**
 * Navegación principal (Design System v3 -
 * 01-arquitectura/05-design-system-v3.md, "Arquitectura de información").
 *
 * Dos decisiones de la auditoría:
 *
 *  - **`Coach` sale del nav principal y entra `Perfil`.** Coach ocupaba
 *    un quinto de la navegación para mostrar "Todavía no está
 *    construido" (y su estado vacío exponía jerga interna del
 *    proyecto). Su valor real ya se entrega hoy como narrativa en
 *    contexto dentro de las páginas. Perfil, que faltaba por completo,
 *    ocupa su sitio: apariencia (tema), conexiones y datos propios.
 *  - **Etiqueta corta propia en móvil.** A 390px cinco destinos dejan
 *    ~78px cada uno, y "Entrenamiento" no cabe: era una de las causas
 *    del texto cortado que encontró la auditoría. En vez de truncar con
 *    elipsis (prohibido por la doctrina 4) se usa una etiqueta corta
 *    pensada para ese ancho.
 *
 * El estado activo no usa color de acento: es contraste (doctrina 1).
 */
const SECCIONES = [
  { href: "/", label: "Hoy", labelCorto: "Hoy", Icono: Sun },
  { href: "/cuerpo", label: "Cuerpo", labelCorto: "Cuerpo", Icono: Ruler },
  { href: "/entrenamiento", label: "Entrenamiento", labelCorto: "Entreno", Icono: Dumbbell },
  { href: "/nutricion", label: "Nutrición", labelCorto: "Nutrición", Icono: Utensils },
  { href: "/perfil", label: "Perfil", labelCorto: "Perfil", Icono: User },
] as const;

function esRutaActiva(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-inset";

export function Nav() {
  const pathname = usePathname();

  return (
    <>
      {/* Barra lateral de escritorio */}
      <nav
        aria-label="Navegación principal"
        className="hidden md:flex md:w-56 md:shrink-0 md:flex-col md:gap-0.5 md:border-r md:border-line md:p-3"
      >
        <div className="mb-7 flex items-center gap-2.5 px-2 pt-2">
          <Image src="/icon-192.png" alt="" width={24} height={24} className="rounded-md" priority />
          <span className="t-section text-ink">Pulse</span>
        </div>
        {SECCIONES.map(({ href, label, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-md px-2 py-2 t-body transition-colors ${focusRing} ${
                activa
                  ? "bg-surface font-medium text-ink"
                  : "text-ink-2 hover:bg-surface hover:text-ink"
              }`}
            >
              <Icono aria-hidden="true" size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Barra inferior de móvil: anclada y con etiquetas, no la
          "pastilla" flotante con el icono activo en un círculo negro.
          Esa pastilla es un patrón de galería de inspiración: flotaba
          sobre el contenido y lo dejaba cortado por debajo, y al ser
          solo iconos obligaba a adivinar cada destino. Una tab bar
          anclada y etiquetada es lo que usan las apps de referencia
          (Salud de Apple, Strava) por buenas razones. */}
      <nav
        aria-label="Navegación principal (móvil)"
        className="md:hidden fixed bottom-0 left-0 right-0 z-10 flex border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]"
      >
        {SECCIONES.map(({ href, labelCorto, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 transition-colors ${focusRing} ${
                activa ? "text-ink" : "text-ink-3"
              }`}
            >
              <Icono aria-hidden="true" size={19} strokeWidth={activa ? 2.25 : 1.75} />
              <span className={`text-[0.6875rem] leading-none ${activa ? "font-medium" : ""}`}>
                {labelCorto}
              </span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
