"use client";

import { motion, useReducedMotion } from "motion/react";
import { PALETA } from "@/lib/theme";

/**
 * Anillo circular de recovery, estilo WHOOP (ver guía oficial de marca
 * "WHOOP - Brand & Design Guidelines" - colores exactos, no aproximados):
 * - Verde #16EC06: recovery alta (67-100%).
 * - Amarillo #FFDE00: recovery media (34-66%).
 * - Rojo #FF0026: recovery baja (0-33%).
 *
 * El color se puede fijar explícitamente (`zone`) - útil cuando el
 * dato ya viene clasificado por el motor de reglas del backend
 * (verde/amarillo/rojo) - o derivarse del porcentaje con los mismos
 * umbrales que documenta WHOOP, para reutilizar este componente con
 * cualquier métrica 0-100 que necesite su propio anillo (Sleep,
 * Strain normalizado, etc.).
 *
 * Accesibilidad (WCAG 1.4.1): el significado nunca depende solo del
 * color - el propio `aria-label` del SVG describe la etiqueta, el
 * valor y el nombre de la zona en texto.
 */
type Zone = "green" | "yellow" | "red";

const COLOR_POR_ZONA: Record<Zone, string> = {
  green: PALETA.recoveryHigh,
  yellow: PALETA.recoveryMedium,
  red: PALETA.recoveryLow,
};

const NOMBRE_ZONA_ES: Record<Zone, string> = {
  green: "verde",
  yellow: "amarilla",
  red: "roja",
};

function derivarZona(percent: number): Zone {
  if (percent >= 67) return "green";
  if (percent >= 34) return "yellow";
  return "red";
}

const RADIO = 54;
const CIRCUNFERENCIA = 2 * Math.PI * RADIO;

// Punto representativo del ARCO (nunca mostrado como número) para el
// modo categórico - mismos puntos medios de zona que documenta la
// guía de marca de WHOOP, usados SOLO para dar lenguaje visual al
// relleno del anillo, nunca como una cifra visible al usuario.
const PERCENT_REPRESENTATIVO_POR_ZONA: Record<Zone, number> = {
  green: 83,
  yellow: 50,
  red: 17,
};

type RecoveryRingProps =
  | {
      /** Porcentaje real 0-100 medido (p.ej. una futura métrica de
       * Sleep o Strain normalizado). Se muestra tal cual, como número. */
      percent: number;
      zone?: Zone;
      categoryLabel?: undefined;
      label?: string;
      size?: number;
    }
  | {
      /** Modo categórico (hallazgo CRÍTICO de code-review): el motor
       * de reglas de Pulse decide verde/amarillo/rojo, NUNCA un score
       * continuo 0-100 como el de WHOOP. En este modo el centro del
       * anillo muestra la PALABRA de la zona, nunca un número
       * inventado - el arco se rellena hasta un punto representativo
       * fijo de la zona solo para el lenguaje visual. */
      percent?: undefined;
      zone: Zone;
      categoryLabel: string;
      label?: string;
      size?: number;
    };

export function RecoveryRing(props: RecoveryRingProps) {
  const { zone, categoryLabel, label, size = 160 } = props;
  const modoCategoria = categoryLabel !== undefined;
  const prefiereMenosMovimiento = useReducedMotion();

  const percentClamped = modoCategoria
    ? PERCENT_REPRESENTATIVO_POR_ZONA[zone ?? "green"]
    : Math.min(100, Math.max(0, props.percent));
  const zonaFinal = zone ?? derivarZona(percentClamped);
  const color = COLOR_POR_ZONA[zonaFinal];
  const offsetFinal = CIRCUNFERENCIA * (1 - percentClamped / 100);
  const percentRedondeado = Math.round(percentClamped);

  const ariaLabel = modoCategoria
    ? `${label ?? "Valor"}: ${categoryLabel}, zona ${NOMBRE_ZONA_ES[zonaFinal]}`
    : `${label ?? "Valor"}: ${percentRedondeado}%, zona ${NOMBRE_ZONA_ES[zonaFinal]}`;

  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      role="img"
      aria-label={ariaLabel}
    >
      <circle
        cx={60}
        cy={60}
        r={RADIO}
        fill="none"
        stroke={PALETA.surfaceTrack}
        strokeWidth={10}
      />
      <motion.circle
        data-testid="ring-progress"
        cx={60}
        cy={60}
        r={RADIO}
        fill="none"
        stroke={color}
        strokeWidth={10}
        strokeLinecap="round"
        strokeDasharray={CIRCUNFERENCIA}
        transform="rotate(-90 60 60)"
        initial={{ strokeDashoffset: CIRCUNFERENCIA }}
        animate={{ strokeDashoffset: offsetFinal }}
        transition={{ duration: prefiereMenosMovimiento ? 0 : 1, ease: "easeOut" }}
      />
      <text
        x="60"
        y={label ? "56" : "64"}
        textAnchor="middle"
        fontSize={modoCategoria ? "16" : "26"}
        fontWeight="700"
        fill={PALETA.textPrimary}
        className="font-display"
      >
        {modoCategoria ? categoryLabel.toUpperCase() : `${percentRedondeado}%`}
      </text>
      {label && (
        <text
          x="60"
          y="74"
          textAnchor="middle"
          fontSize="10"
          letterSpacing="1.5"
          fill={PALETA.textMuted}
          style={{ textTransform: "uppercase" }}
        >
          {label}
        </text>
      )}
    </svg>
  );
}
