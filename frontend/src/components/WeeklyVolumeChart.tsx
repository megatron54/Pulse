"use client";

import { useEffect, useState } from "react";
import { api, type WeeklyVolume } from "@/lib/api";
import { formatDistancia, formatDuracion } from "@/lib/activityFormat";
import { TrendChart } from "./ui/TrendChart";

/**
 * Volumen semanal del deporte que se está viendo (distancia para
 * running/ciclismo, duración para gimnasio) o de todos juntos en la
 * vista "Todas" (duración: sumar kilómetros de carrera con kilómetros
 * de bici daría una cifra que no significa nada). Va entre el
 * encabezado y la tabla de sesiones, separado por líneas de 1px: no es
 * un objeto independiente, es el resumen de la tabla que sigue.
 *
 * Estaba debajo de la tabla, y ahí no se veía: en "Todas" hay 27
 * sesiones en 90 días, así que la única gráfica de la pestaña quedaba a
 * dos pantallas de scroll de la pregunta que contesta ("¿cuánto llevo
 * esta semana?"). Primero el resumen, luego el detalle.
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
  /** Sin categoría, el volumen de todos los deportes juntos (vista
   *  "Todas"): la pregunta de esa lista es cuánto se ha entrenado en
   *  total, no cuánto de cada deporte. */
  categoria?: "running" | "ciclismo" | "gimnasio";
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

  const escala = escalaEje(
    conDatos.map((s) => valorSemana(s) as number),
    metrica
  );
  const data = conDatos.map((s) => ({
    fecha: s.semana_inicio,
    valor: (valorSemana(s) as number) / escala.divisor,
  }));
  // La semana en curso y la anterior por POSICIÓN, no por "la última con
  // datos": el endpoint devuelve siempre `weeks` puntos ascendentes
  // terminando en la semana de hoy, así que una semana en blanco es un
  // dato ("esta semana no has entrenado") y no un hueco que se salta.
  const estaSemana = semanas[semanas.length - 1];
  const semanaAnterior = semanas[semanas.length - 2];

  return (
    <div className="border-t border-line px-5 py-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="t-section text-ink">Volumen por semana</h3>
        <span className="t-secondary text-ink-2">
          {resumenSemana(estaSemana, semanaAnterior, metrica)}
        </span>
      </div>
      <TrendChart
        data={data}
        unidad={escala.unidad}
        decimales={escala.decimales}
        etiqueta={metrica === "distancia" ? "Distancia por semana" : "Duración por semana"}
        alto={170}
      />
    </div>
  );
}

/**
 * En qué unidad se rotula el eje, a partir de la magnitud de la serie.
 *
 * Horas y no minutos cuando las semanas son largas: en "Todas" se suman
 * los tres deportes y el eje salía rotulado "800 min" mientras la frase
 * de al lado decía "13 h 20 min" - había que dividir por 60 a ojo para
 * relacionar las dos cifras de la misma tarjeta. El umbral son 3 h, a
 * partir de las cuales "2.5 h" se lee mejor que "150 min".
 *
 * Exportada solo para poder probarla: en jsdom el `ResponsiveContainer`
 * de recharts mide 0x0 y no dibuja ninguna marca, así que la unidad del
 * eje no es observable desde el DOM (mismo motivo que `ejeY` en
 * `ui/TrendChart`).
 */
export function escalaEje(
  brutos: readonly number[],
  metrica: "distancia" | "duracion"
): { divisor: number; unidad: string; decimales: number } {
  if (metrica === "distancia") return { divisor: 1000, unidad: " km", decimales: 1 };
  if (Math.max(...brutos) >= 3 * 3600) return { divisor: 3600, unidad: " h", decimales: 1 };
  return { divisor: 60, unidad: " min", decimales: 0 };
}

/**
 * Qué ha pasado ESTA semana, y si es más o menos que la anterior.
 *
 * Es la única frase de la pestaña que da contexto temporal a la tabla:
 * antes decía "Última semana: 32.0 km" refiriéndose a la última semana
 * con datos - que un lunes es la semana pasada y no la que se está
 * viendo - y sin nada con lo que comparar, así que la cifra no respondía
 * si se está entrenando más o menos que de costumbre.
 *
 * Sin color: más volumen no es "bueno" ni "malo" sin saber en qué fase
 * del plan se está (para eso está la carga de entrenamiento, que sí
 * tiene referencia). El color codifica estado, y aquí no hay estado que
 * codificar (doctrina 1).
 */
function resumenSemana(
  estaSemana: WeeklyVolume,
  semanaAnterior: WeeklyVolume | undefined,
  metrica: "distancia" | "duracion"
): string {
  const bruto = (s: WeeklyVolume) =>
    metrica === "distancia" ? s.distancia_total_m : s.duracion_total_seg;
  const texto = (s: WeeklyVolume) =>
    metrica === "distancia" ? formatDistancia(s.distancia_total_m) : formatDuracion(s.duracion_total_seg);

  const actual = texto(estaSemana);
  if (estaSemana.num_sesiones === 0 || actual === null) {
    return "Esta semana todavía sin sesiones registradas.";
  }

  const valorActual = bruto(estaSemana);
  const valorAnterior = semanaAnterior ? bruto(semanaAnterior) : null;
  if (valorActual === null || valorAnterior === null || valorAnterior === 0) {
    return `Esta semana: ${actual}`;
  }

  const diferencia = valorActual - valorAnterior;
  const textoDiferencia =
    metrica === "distancia"
      ? formatDistancia(Math.abs(diferencia))
      : formatDuracion(Math.abs(diferencia));
  // Una diferencia que se redondea a nada no es una diferencia.
  if (textoDiferencia === null) return `Esta semana: ${actual}, igual que la anterior`;
  return `Esta semana: ${actual}, ${textoDiferencia} ${
    diferencia > 0 ? "más" : "menos"
  } que la anterior`;
}
