"use client";

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

/**
 * Entrada animada sutil (fade + slide-up corto) para las tarjetas del
 * dashboard. `delay` permite escalonar la entrada de varias tarjetas en
 * secuencia (efecto "stagger") sin coordinar un padre con Framer's
 * `staggerChildren` - suficiente para el número de tarjetas de esta app
 * y más simple de razonar por tarjeta individual.
 *
 * Respeta `prefers-reduced-motion` (WCAG 2.3.3): si el usuario lo pide,
 * el contenido aparece directamente sin desplazamiento ni fundido.
 */
export function FadeIn({
  children,
  delay = 0,
}: {
  children: ReactNode;
  delay?: number;
}) {
  const prefiereMenosMovimiento = useReducedMotion();

  if (prefiereMenosMovimiento) {
    return <>{children}</>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
