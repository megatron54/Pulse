"use client";

import type { ComponentProps, ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { motionTokens, springs } from "@/lib/motion-tokens";

/**
 * Botón compartido (auditoría UI/UX): antes de esto, cada formulario
 * de la app repetía su propia clase `bg-teal ... hover:scale-[1.02]
 * active:scale-[0.98]` con transiciones CSS lineales - el look "por
 * defecto de cualquier dashboard generado rápido". Aquí el feedback de
 * hover/tap usa un spring físico real (`motion/react`, mismo motor que
 * `RecoveryRing`) en vez de un `transition: transform` de CSS, y
 * NINGÚN botón tenía un anillo de foco visible propio (solo `Nav.tsx`
 * lo definía para los links) - un problema real de accesibilidad de
 * teclado (WCAG 2.4.7) que se arregla aquí de una vez para todos.
 *
 * `variant="ghost"` es para acciones secundarias tipo "Añadir" dentro
 * de una lista (antes texto plano sin padding, con un área táctil por
 * debajo del mínimo de 44×44px recomendado por WCAG 2.5.5) - aquí
 * siempre lleva `min-h-11` (44px) aunque el texto sea pequeño.
 */
const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal " +
  "focus-visible:ring-offset-2 focus-visible:ring-offset-surface-solid " +
  "disabled:cursor-not-allowed disabled:opacity-60";

const VARIANTES = {
  primary: `${BASE} bg-teal text-black px-4 py-2.5 text-sm disabled:bg-surface-solid disabled:text-gray-400`,
  // text-black (no text-white): code-review del rediseño Apple detectó
  // que el nuevo azul de sistema (#0A84FF) con texto blanco encima cae
  // a ~3.6:1, por debajo de AA (4.5:1) para texto normal - con negro
  // sube a ~5.9:1. El teal viejo de WHOOP (#0093E7, más oscuro) sí
  // pasaba con blanco; el azul de sistema Apple es más claro.
  strain: `${BASE} bg-strain text-black px-4 py-2.5 text-sm disabled:bg-surface-solid disabled:text-gray-400`,
  ghost:
    `${BASE} min-h-11 min-w-11 px-3 text-teal text-xs font-semibold uppercase tracking-wide ` +
    "hover:bg-teal/10 disabled:hover:bg-transparent",
} as const;

export function Button({
  variant = "primary",
  className = "",
  children,
  disabled,
  ...props
}: {
  variant?: keyof typeof VARIANTES;
  children: ReactNode;
} & Omit<ComponentProps<typeof motion.button>, "children">) {
  const prefiereMenosMovimiento = useReducedMotion();
  const gestos =
    disabled || prefiereMenosMovimiento
      ? {}
      : {
          whileHover: { scale: motionTokens.scale.pop },
          whileTap: { scale: motionTokens.scale.press },
          transition: springs.snappy,
        };

  return (
    <motion.button
      className={`${VARIANTES[variant]} ${className}`}
      disabled={disabled}
      {...gestos}
      {...props}
    >
      {children}
    </motion.button>
  );
}
