"use client";

import type { ComponentProps, ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { motionTokens, springs } from "@/lib/motion-tokens";

/**
 * Botón compartido (Design System v3).
 *
 * El cambio de fondo respecto a v2 es deliberado y es el corazón de la
 * doctrina 1 ("el color es información, nunca decoración"): la acción
 * primaria ya NO es azul saturado, sino neutro de alto contraste
 * (`--action`: casi negro en claro, casi blanco en oscuro). Un botón
 * azul brillante en cada tarjeta competía con los datos y era una de
 * las fuentes del aspecto "neón" que se rechaza.
 *
 * Se mantiene el anillo de foco visible (WCAG 2.4.7), el área táctil
 * mínima de 44px en `ghost` (WCAG 2.5.5) y el spring de `motion/react`
 * respetando `prefers-reduced-motion`.
 */
const BASE =
  "inline-flex items-center justify-center gap-2 rounded-md font-medium " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink " +
  "focus-visible:ring-offset-2 focus-visible:ring-offset-surface " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const VARIANTES = {
  // `text-action-ink` (no `text-white`): al ser el fondo casi blanco en
  // modo oscuro, un texto blanco fijo sería ilegible. El par
  // action/action-ink se invierte junto con el tema.
  primary: `${BASE} bg-action text-action-ink px-3.5 py-2 t-body`,
  secondary: `${BASE} border border-line bg-surface text-ink px-3.5 py-2 t-body hover:bg-canvas`,
  ghost: `${BASE} min-h-11 min-w-11 px-3 text-ink-2 t-body hover:text-ink hover:bg-canvas`,
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
