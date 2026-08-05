"use client";

import { RadialBar, RadialBarChart, PolarAngleAxis } from "recharts";
import { PALETA } from "@/lib/theme";
import { AnimatedNumber } from "./AnimatedNumber";

/**
 * Medidor circular (estilo "anillo" de Apple Health/Samsung
 * Health/WHOOP Strain) para una métrica 0-100 con color semántico -
 * reemplaza al número plano `text-4xl` que usaban `TrainingLoadCard`
 * y similares. El valor central usa `AnimatedNumber` (mismo motor de
 * `motion/react` que el resto de la app) en vez de saltar de golpe.
 */
export function RadialGauge({
  value,
  max,
  color,
  label,
  size = 120,
  decimals = 0,
  valueClassName = "text-white",
}: {
  value: number;
  max: number;
  color: string;
  label: string;
  size?: number;
  decimals?: number;
  valueClassName?: string;
}) {
  const porcentaje = Math.min(100, Math.max(0, (value / max) * 100));
  const data = [{ valor: porcentaje, fill: color }];

  return (
    <div
      style={{ width: size, height: size }}
      className="relative shrink-0"
      role="img"
      aria-label={`${label}: ${value.toFixed(decimals)}`}
    >
      <RadialBarChart
        width={size}
        height={size}
        cx="50%"
        cy="50%"
        innerRadius="72%"
        outerRadius="100%"
        barSize={10}
        data={data}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar
          background={{ fill: PALETA.surfaceTrack }}
          dataKey="valor"
          cornerRadius={5}
          isAnimationActive={true}
          animationDuration={700}
        />
      </RadialBarChart>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <AnimatedNumber
          value={value}
          decimals={decimals}
          className={`font-display text-2xl font-bold ${valueClassName}`}
        />
        <span className="text-[10px] uppercase tracking-wide text-gray-400" aria-hidden="true">
          {label}
        </span>
      </div>
    </div>
  );
}
