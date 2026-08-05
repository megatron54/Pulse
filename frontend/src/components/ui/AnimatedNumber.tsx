"use client";

import { useEffect, useRef } from "react";
import { animate } from "motion";
import { useReducedMotion } from "motion/react";
import { motionTokens } from "@/lib/motion-tokens";

/**
 * Contador animado (auditoría UI/UX, hallazgo M1): antes, los números
 * "hero" de las tarjetas (kcal objetivo, ACWR, kcal del diario...)
 * cambiaban de golpe en cada re-render - inconsistente frente al
 * `RecoveryRing`, que sí anima. En vez de forzar un re-render de React
 * en cada frame (el patrón ingenuo con `useState`), se anima el número
 * de forma IMPERATIVA escribiendo directamente en `textContent` vía
 * `onUpdate` - cero re-renders de React durante la animación, un
 * fotograma más barato y fluido (patrón recomendado para contadores en
 * `motion/react`).
 *
 * Respeta `prefers-reduced-motion` (WCAG 2.3.3): salta directo al
 * valor final sin animar.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  className = "",
}: {
  value: number;
  decimals?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const valorAnterior = useRef(value);
  const prefiereMenosMovimiento = useReducedMotion();

  useEffect(() => {
    const nodo = ref.current;
    if (!nodo) return;

    if (prefiereMenosMovimiento) {
      nodo.textContent = value.toFixed(decimals);
      valorAnterior.current = value;
      return;
    }

    const controles = animate(valorAnterior.current, value, {
      duration: motionTokens.duration.slow,
      ease: motionTokens.easing.smooth,
      onUpdate: (v) => {
        if (nodo) nodo.textContent = v.toFixed(decimals);
      },
    });
    valorAnterior.current = value;
    return () => controles.stop();
  }, [value, decimals, prefiereMenosMovimiento]);

  return (
    <span ref={ref} className={`tabular-nums ${className}`}>
      {value.toFixed(decimals)}
    </span>
  );
}
