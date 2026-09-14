"use client";

import { useEffect, useState } from "react";
import { api, type WeeklyVolume } from "@/lib/api";
import { formatDistancia, formatDuracion } from "@/lib/activityFormat";
import { TrendChart } from "./ui/TrendChart";

/**
 * Volumen semanal del deporte que se está viendo (distancia para
 * running/ciclismo, duración para gimnasio). Va al final de la tarjeta
 * de sesiones, separado por una línea de 1px: es el contexto de la
 * tabla de arriba, no un objeto independiente.
 *
 * Bloque deliberadamente silencioso si falla o no hay datos: es un
 * añadido secundario dentro de una tarjeta que ya gestiona su propio
 * error para la lista de actividades; duplicar ese estado aquí sería
 * ruido y no información nueva.
 *
 * Una semana sin sesiones NO se dibuja como 0 sino que se omite
 * (doctrina 6): un cero real y "esa semana no sincronizó nada" no son
 * lo mismo, y solo el primero significa "no entrené".
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
        if (!cancelado) setSemanas(datos);
      })
      .catch(() => {
        // Ver docstring: se ignora el error a propósito.
        if (!cancelado) setSemanas([]);
      });
    return () => {
      cancelado = true;
    };
  }, [userId, categoria, weeks]);

  if (semanas === null) return null;

  const valorSemana = (s: WeeklyVolume) =>
    metrica === "distancia" ? s.distancia_total_m : s.duracion_total_seg;

  const conDatos = semanas.filter((s) => s.num_sesiones > 0 && valorSemana(s) !== null);
  // Con una sola semana no hay tendencia que mirar: una gráfica de un
  // punto era otro de los hallazgos de la auditoría.
  if (conDatos.length < 2) return null;

  const data = conDatos.map((s) => {
    const bruto = valorSemana(s) as number;
    return { fecha: s.semana_inicio, valor: metrica === "distancia" ? bruto / 1000 : bruto / 60 };
  });
  const ultima = conDatos[conDatos.length - 1];
  const textoUltima =
    metrica === "distancia"
      ? formatDistancia(ultima.distancia_total_m)
      : formatDuracion(ultima.duracion_total_seg);

  return (
    <div className="border-t border-line px-5 py-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="t-section text-ink">Volumen por semana</h3>
        {textoUltima && (
          <span className="t-secondary text-ink-3">Última semana: {textoUltima}</span>
        )}
      </div>
      <TrendChart
        data={data}
        unidad={metrica === "distancia" ? " km" : " min"}
        decimales={metrica === "distancia" ? 1 : 0}
        etiqueta={metrica === "distancia" ? "Distancia por semana" : "Duración por semana"}
        alto={170}
      />
    </div>
  );
}
