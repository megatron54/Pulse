/**
 * Sistema de tokens de motion de Pulse: toda duración/easing/spring del
 * proyecto vale de aquí, nunca como número suelto en un componente
 * (evita que cada tarjeta invente su propio "duration-700" o
 * "hover:scale-[1.02]" a mano, como pasaba antes de esta pasada de
 * pulido UI/UX). Los valores de spring/easing son físicos y sutiles a
 * propósito - lo contrario del "ease-in-out linealón" genérico que se
 * ve en cualquier dashboard generado rápido.
 */
export const motionTokens = {
  duration: {
    instant: 0.08,
    fast: 0.18,
    normal: 0.35,
    slow: 0.6,
    crawl: 1.4,
  },
  easing: {
    smooth: [0.22, 1, 0.36, 1],
    sharp: [0.4, 0, 0.2, 1],
    linear: [0, 0, 1, 1],
  },
  distance: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 48,
  },
  scale: {
    subtle: 0.98,
    press: 0.96,
    pop: 1.02,
  },
} as const;

export const springs = {
  // Default de UI: botones, chips, elementos interactivos pequeños.
  snappy: { type: "spring", stiffness: 420, damping: 28 } as const,
  // Tarjetas/paneles aterrizando con suavidad.
  gentle: { type: "spring", stiffness: 160, damping: 20 } as const,
  // Momentos con un poco de rebote intencional (anillo de recovery).
  bouncy: { type: "spring", stiffness: 320, damping: 14 } as const,
};
