"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";

/**
 * Gráfica de tendencia con degradado (estilo Apple Health/Samsung
 * Health: una línea suave con relleno de gradiente que se desvanece
 * hacia abajo, en vez del `Sparkline` anterior sin ejes ni tooltip).
 * Deliberadamente minimalista: sin grid, sin eje X con fechas
 * apretadas (el rango temporal ya lo dice el título de la tarjeta) -
 * el objetivo es comunicar la FORMA de la tendencia de un vistazo, con
 * el valor exacto disponible al pasar el cursor.
 */
export function AreaTrendChart({
  data,
  color,
  unidad = "",
  alto = 96,
  decimales = 1,
}: {
  data: { fecha: string; valor: number }[];
  color: string;
  unidad?: string;
  alto?: number;
  decimales?: number;
}) {
  const gradientId = `area-gradient-${color.replace("#", "")}`;
  if (data.length === 0) {
    return (
      <div style={{ width: "100%", height: alto }} role="img" aria-label="Gráfica de tendencia" />
    );
  }
  const valores = data.map((d) => d.valor);
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  // Domain con margen del 8% para que la línea nunca toque el borde
  // superior/inferior del contenedor (se vería "cortada").
  const margen = Math.max((max - min) * 0.08, 0.5);

  return (
    <div style={{ width: "100%", height: alto }} role="img" aria-label="Gráfica de tendencia">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis domain={[min - margen, max + margen]} hide />
          <Tooltip
            cursor={{ stroke: color, strokeOpacity: 0.3 }}
            contentStyle={{
              background: "#1a1f23",
              border: "1px solid #2c3338",
              borderRadius: 8,
              fontSize: 12,
              padding: "6px 10px",
            }}
            labelStyle={{ color: "#a9b2b8" }}
            itemStyle={{ color: "#f2f4f5" }}
            formatter={(value) => [`${Number(value).toFixed(decimales)}${unidad}`, ""]}
          />
          <Area
            type="monotone"
            dataKey="valor"
            stroke={color}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            isAnimationActive={true}
            animationDuration={600}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
