"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export type DonutSegment = { nombre: string; valor: number; color: string };

/**
 * Donut de composición (macros, distribución de readiness...) - más
 * visual que una columna de barras de progreso apiladas: de un
 * vistazo se ve la PROPORCIÓN relativa entre segmentos, que es
 * exactamente lo que una barra 1D comunica peor.
 */
export function DonutChart({
  segments,
  size = 120,
  centro,
}: {
  segments: DonutSegment[];
  size?: number;
  /** Contenido central (p.ej. "2400 kcal") superpuesto al hueco del donut. */
  centro?: React.ReactNode;
}) {
  const total = segments.reduce((acc, s) => acc + s.valor, 0);

  return (
    <div style={{ width: size, height: size }} className="relative shrink-0">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={segments}
            dataKey="valor"
            nameKey="nombre"
            innerRadius="68%"
            outerRadius="100%"
            paddingAngle={2}
            stroke="none"
            isAnimationActive={true}
            animationDuration={600}
          >
            {segments.map((s) => (
              <Cell key={s.nombre} fill={s.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#1a1f23",
              border: "1px solid #2c3338",
              borderRadius: 8,
              fontSize: 12,
              padding: "6px 10px",
            }}
            labelStyle={{ color: "#f2f4f5" }}
            itemStyle={{ color: "#a9b2b8" }}
            formatter={(value, nombre) => {
              const num = Number(value);
              return [
                `${num.toFixed(0)} (${total > 0 ? Math.round((num / total) * 100) : 0}%)`,
                String(nombre),
              ];
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      {centro && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          {centro}
        </div>
      )}
    </div>
  );
}
