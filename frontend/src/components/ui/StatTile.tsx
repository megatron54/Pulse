"use client";

import type { LucideIcon } from "lucide-react";
import { AnimatedNumber } from "./AnimatedNumber";

/**
 * Tile compacto de métrica (v2.1, inspirado en el "rail" de anillos de
 * Garmin Connect/Apple Health): sustituye a las tarjetas apiladas a
 * ancho completo que antes usaba cada métrica suelta (HRV, Body
 * Battery, sueño...) en un rail horizontal deslizable en móvil y en
 * grid en desktop - mismo patrón en "Hoy" y en "Recuperación".
 */
export function StatTile({
  icon: Icon,
  label,
  value,
  unit = "",
  decimals = 0,
  valueClassName = "text-foreground",
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  valueClassName?: string;
}) {
  return (
    <div className="flex min-w-[7.5rem] shrink-0 flex-col gap-1.5 rounded-xl border border-surface-border bg-surface px-4 py-3">
      <div className="flex items-center gap-1.5 text-text-secondary">
        <Icon aria-hidden="true" size={14} />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className={`text-xl font-semibold tabular-nums ${valueClassName}`}>
        <AnimatedNumber value={value} decimals={decimals} />
        {unit}
      </p>
    </div>
  );
}
