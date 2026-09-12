"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Dumbbell,
  HeartPulse,
  MessageCircle,
  Ruler,
  Sun,
  Utensils,
} from "lucide-react";

/**
 * Navegación principal (reconstrucción v2 -
 * 01-arquitectura/04-design-system-v2.md): 7 secciones con jerarquía
 * de producto real, en vez de las 9 páginas planas anteriores
 * (running/ciclismo/gimnasio se pliegan en Entrenamiento→Sesiones como
 * un filtro `categoria`, Garmin se reparte entre Recuperación/Análisis).
 *
 * Responsive verificado por redimensionado real (Design System v2,
 * principio 5): sidebar fluida en desktop, tab bar fija abajo en
 * móvil - ambos casos sin anchos fijos que corten contenido.
 */
const SECCIONES = [
  { href: "/", label: "Hoy", Icono: Sun },
  { href: "/entrenamiento", label: "Entrenamiento", Icono: Dumbbell },
  { href: "/salud", label: "Recuperación", Icono: HeartPulse },
  { href: "/analisis", label: "Análisis", Icono: BarChart3 },
  { href: "/coach", label: "Coach", Icono: MessageCircle },
  { href: "/nutricion", label: "Nutrición", Icono: Utensils },
  { href: "/cuerpo", label: "Cuerpo", Icono: Ruler },
] as const;

function esRutaActiva(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset";

export function Nav() {
  const pathname = usePathname();

  return (
    <>
      {/* Sidebar de escritorio */}
      <nav
        aria-label="Navegación principal"
        className="hidden md:flex md:w-60 md:shrink-0 md:flex-col md:gap-1 md:border-r md:border-surface-border md:bg-surface md:p-4"
      >
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <Image src="/icon-192.png" alt="" width={28} height={28} className="rounded-lg" priority />
          <span className="text-xl font-semibold tracking-tight text-foreground">Pulse</span>
        </div>
        {SECCIONES.map(({ href, label, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors active:scale-[0.98] ${focusRing} ${
                activa
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:text-foreground hover:bg-surface-muted"
              }`}
            >
              <Icono aria-hidden="true" size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Barra de pestañas de móvil: 7 secciones caben sin scroll
          horizontal (a diferencia de las 9 anteriores), flex-1 a
          partes iguales. */}
      <nav
        aria-label="Navegación principal (móvil)"
        className="md:hidden fixed bottom-0 left-0 right-0 z-10 flex border-t border-surface-border bg-surface pb-[env(safe-area-inset-bottom)]"
      >
        {SECCIONES.map(({ href, label, Icono }) => {
          const activa = esRutaActiva(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={activa ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium leading-tight transition-transform active:scale-95 ${focusRing} ${
                activa ? "text-accent" : "text-text-secondary"
              }`}
            >
              <Icono aria-hidden="true" size={20} />
              <span className="truncate max-w-full px-0.5">{label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
