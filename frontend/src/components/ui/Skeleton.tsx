"use client";

import { useEffect } from "react";
import type { CSSProperties } from "react";
import { motion, useAnimation, useReducedMotion } from "motion/react";
import { motionTokens } from "@/lib/motion-tokens";

/**
 * Bloque de shimmer compartido: un barrido de gradiente diagonal en
 * movimiento, en vez de la clase `animate-pulse` de Tailwind (el
 * placeholder de opacidad parpadeante que trae cualquier dashboard
 * generado por defecto - justo la estética que esta pasada de pulido
 * quiere evitar). Se pausa cuando la pestaña no está visible y
 * respeta `prefers-reduced-motion` con un bloque estático.
 *
 * Usado tanto por `LoadingState` (líneas de texto) como por el
 * shimmer de página completa de `AppShell` (bloques grandes) - una
 * sola implementación del efecto en toda la app.
 */
export function Skeleton({
  className = "",
  style,
}: {
  className?: string;
  style?: CSSProperties;
}) {
  const controls = useAnimation();
  const prefiereMenosMovimiento = useReducedMotion();

  useEffect(() => {
    if (prefiereMenosMovimiento) return;

    const reproducir = () =>
      controls.start({
        backgroundPosition: ["200% 0", "-200% 0"],
        transition: {
          repeat: Infinity,
          duration: motionTokens.duration.crawl * 1.5,
          ease: motionTokens.easing.linear,
        },
      });

    const alCambiarVisibilidad = () => {
      if (document.visibilityState === "hidden") controls.stop();
      else void reproducir();
    };

    void reproducir();
    document.addEventListener("visibilitychange", alCambiarVisibilidad);
    return () => {
      controls.stop();
      document.removeEventListener("visibilitychange", alCambiarVisibilidad);
    };
  }, [controls, prefiereMenosMovimiento]);

  return (
    <motion.div
      data-testid="shimmer-bar"
      className={`rounded-md bg-white/5 ${className}`}
      style={{
        ...style,
        backgroundImage: prefiereMenosMovimiento
          ? undefined
          : "linear-gradient(100deg, rgba(255,255,255,0.05) 40%, rgba(255,255,255,0.12) 50%, rgba(255,255,255,0.05) 60%)",
        backgroundSize: "300% 100%",
      }}
      animate={controls}
    />
  );
}
