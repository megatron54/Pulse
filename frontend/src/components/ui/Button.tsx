"use client";

import type { ComponentProps, ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { motionTokens, springs } from "@/lib/motion-tokens";

/**
 * Botón compartido (Design System v2): feedback con spring físico
 * (`motion/react`), anillo de foco visible (WCAG 2.4.7), área táctil
 * mínima de 44×44px en la variante `ghost` (WCAG 2.5.5). Colores del
 * tema único Apple-clean (`--color-accent`), funcionan en claro/oscuro.
 */
const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent " +
  "focus-visible:ring-offset-2 focus-visible:ring-offset-surface " +
  "disabled:cursor-not-allowed disabled:opacity-60";

const VARIANTES = {
  // text-white fijo (no text-foreground): el botón primario siempre
  // tiene fondo azul de acento en claro Y oscuro, así que el texto
  // debe ser siempre claro - text-foreground cambiaría a negro en
  // modo claro y sería ilegible sobre el mismo azul.
  primary: `${BASE} bg-accent text-white px-4 py-2.5 text-sm disabled:bg-surface-muted disabled:text-text-secondary`,
  secondary:
    `${BASE} bg-surface-muted text-foreground px-4 py-2.5 text-sm ` +
    "disabled:bg-surface-muted disabled:text-text-secondary",
  ghost:
    `${BASE} min-h-11 min-w-11 px-3 text-accent text-sm font-medium ` +
    "hover:bg-accent/10 disabled:hover:bg-transparent",
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
