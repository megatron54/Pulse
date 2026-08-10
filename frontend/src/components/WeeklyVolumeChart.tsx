"use client";

import { useEffect, useState } from "react";
import { api, type WeeklyVolume } from "@/lib/api";
import { formatDistancia, formatDuracion } from "@/lib/activityFormat";
import { AreaTrendChart } from "./ui/AreaTrendChart";

/** Épica 10 del plan de expansión (02-roadmap/03-vision-produccion.md):
 * gráfica de volumen semanal (distancia o duración total, según la
 * categoría) - se integra dentro de `SportActivityHistoryCard` en las
 * páginas `/running`, `/ciclismo`, `/gimnasio`.
 *
 * Bloque deliberadamente "silencioso" si algo falla o no hay datos
 * todavía (no muestra error ni estado vacío propio): es un añadido
 * secundario dentro de una tarjeta que ya tiene su propio manejo de
 * error para la lista de actividades - duplicar ese estado aquí sería
 * ruido, no información nueva para el usuario.
 */
export function WeeklyVolumeChart({
  userId,
  categoria,
  metrica,
  weeks = 12,
}: {
  userId: number;
  categoria: "running" | "ciclismo" | "gimnasio";
  metrica: "distancia" | "duracion";
  weeks?: number;
}) {
  const [semanas, setSemanas] = useState<WeeklyVolume[] | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminWeeklyVolume(userId, categoria, weeks)
      .then((datos) => {
        if (cancelado) return;
        setSemanas(datos);
      })
      .catch(() => {
        if (cancelado) return;
        // Ver comentario del componente: se ignora el error a
        // propósito, el bloque simplemente no aparece.
        setSemanas([]);
      });
    return () => {
      cancelado = true;
    };
  }, [userId, categoria, weeks]);

  if (semanas === null) return null;

  const valorSemana = (s: WeeklyVolume) =>
    metrica === "distancia" ? s.distancia_total_m : s.duracion_total_seg;
  const formatValor = metrica === "distancia" ? formatDistancia : formatDuracion;

  const conDatos = semanas.filter((s) => s.num_sesiones > 0 && valorSemana(s) !== null);
  if (conDatos.length === 0) return null;

  const data = conDatos.map((s) => {
    const bruto = valorSemana(s) as number;
    return { fecha: s.semana_inicio, valor: metrica === "distancia" ? bruto / 1000 : bruto / 60 };
  });
  const ultima = conDatos[conDatos.length - 1];

  return (
    <div className="mt-4 border-t border-surface-border pt-4">
      <div className="flex items-baseline justify-between mb-2">
        <p className="text-xs uppercase tracking-wide text-text-secondary">Volumen semanal</p>
        <p className="text-sm text-foreground">{formatValor(valorSemana(ultima))}</p>
      </div>
      <AreaTrendChart
        data={data}
        color="#5eead4"
        unidad={metrica === "distancia" ? " km" : " min"}
        decimales={metrica === "distancia" ? 1 : 0}
      />
    </div>
  );
}
