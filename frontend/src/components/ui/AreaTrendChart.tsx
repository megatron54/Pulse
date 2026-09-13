"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * Gráfica de tendencia con degradado (estilo Apple Health/Samsung
 * Health: una línea suave con relleno de gradiente que se desvanece
 * hacia abajo, en vez del `Sparkline` anterior sin ejes ni tooltip).
 *
 * Por defecto minimalista (sin grid, sin eje X con fechas apretadas) -
 * pensado para el mini-trend glanceable de "Hoy", donde el rango
 * temporal ya lo dice el título de la tarjeta y el objetivo es
 * comunicar la FORMA de la tendencia de un vistazo, con el valor
 * exacto disponible al pasar el cursor.
 *
 * `mostrarEjes` activa eje Y con ticks + eje X con fechas + grid tenue
 * - para las páginas de detalle (Análisis, Recuperación, Cuerpo) donde
 * el usuario pidió explícitamente poder leer valores/unidades sin
 * depender del hover (queja de "gráficas sin ejes ni leyendas").
 */
export function AreaTrendChart({
  data,
  color,
  unidad = "",
  alto = 96,
  decimales = 1,
  mostrarEjes = false,
  formatoEjeX = "fecha",
}: {
  data: { fecha: string; valor: number }[];
  color: string;
  unidad?: string;
  alto?: number;
  decimales?: number;
  mostrarEjes?: boolean;
  /** "fecha" (día/mes, para series de varios días) u "hora" (HH:mm,
   * para series intradía donde todos los puntos son del mismo día). */
  formatoEjeX?: "fecha" | "hora";
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
        <AreaChart
          data={data}
          margin={{ top: 4, right: 4, left: mostrarEjes ? 0 : 4, bottom: mostrarEjes ? 0 : 0 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          {mostrarEjes && (
            <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" vertical={false} />
          )}
          {mostrarEjes && (
            <XAxis
              dataKey="fecha"
              tickFormatter={(fecha: string) =>
                formatoEjeX === "hora"
                  ? new Date(fecha).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })
                  : new Date(fecha).toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" })
              }
              tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
              axisLine={{ stroke: "var(--surface-border)" }}
              tickLine={false}
              minTickGap={24}
            />
          )}
          <YAxis
            domain={[min - margen, max + margen]}
            hide={!mostrarEjes}
            width={mostrarEjes ? 36 : undefined}
            tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${v.toFixed(decimales)}${unidad}`}
          />
          <Tooltip
            cursor={{ stroke: color, strokeOpacity: 0.3 }}
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--surface-border)",
              borderRadius: 8,
              fontSize: 12,
              padding: "6px 10px",
            }}
            labelStyle={{ color: "var(--text-secondary)" }}
            itemStyle={{ color: "var(--foreground)" }}
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
