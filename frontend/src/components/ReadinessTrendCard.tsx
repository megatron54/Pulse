"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type ReadinessResult } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { fechaCorta, plural } from "@/lib/fechas";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

type Zona = "green" | "yellow" | "red";

/** Altura de la barra ADEMÁS del color: el nivel no debe depender solo
 *  del color (WCAG 1.4.1), y la altura ordena los tres estados de forma
 *  evidente sin leer la leyenda.
 *
 *  La altura crece con la GRAVEDAD, no con lo bueno que sea el día. En
 *  la captura de la auditoría era al contrario (óptima 16px, baja 1px) y
 *  el resultado era que los diez días de recuperación baja del mes -
 *  justo lo que hay que ver - eran rayas de un píxel que desaparecían
 *  entre las barras verdes, y encima idénticas en forma al marcador de
 *  "sin datos". Ninguna altura baja de 6px por el mismo motivo. */
const NIVEL: Record<Zona, { label: string; color: string; alto: string }> = {
  green: { label: "Recuperación óptima", color: "bg-pos", alto: "h-1.5" },
  yellow: { label: "Recuperación media", color: "bg-warn", alto: "h-2.5" },
  red: { label: "Recuperación baja", color: "bg-neg", alto: "h-3.5" },
};

const CABECERAS_SEMANA = ["L", "M", "X", "J", "V", "S", "D"] as const;
const DIAS_SEMANA_COMPLETOS = [
  "lunes",
  "martes",
  "miércoles",
  "jueves",
  "viernes",
  "sábado",
  "domingo",
] as const;

const MS_POR_DIA = 86_400_000;

function aFechaLocal(iso: string): Date {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function aIso(fecha: Date): string {
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}-${String(
    fecha.getDate()
  ).padStart(2, "0")}`;
}

/** Índice 0..6 con el lunes primero (getDay() pone el domingo en 0). */
function indiceSemana(fecha: Date): number {
  return (fecha.getDay() + 6) % 7;
}

/**
 * Tendencia de recuperación de los últimos 30 días, en Entrenamiento ›
 * Recuperación.
 *
 * Rehecha entera. La versión de v2 vivía en la pantalla de Hoy y el
 * usuario la señaló sin rodeos: "la tendencia de readiness en pantalla
 * de hoy no aporta nada, no se entiende". Tenía razón y las causas eran
 * concretas:
 *
 *  - 30 círculos de color en `flex-wrap`, sin eje ni fechas: el día 27
 *    caía debajo del día 1, así que la fila no era una línea temporal
 *    aunque lo pareciera.
 *  - El significado de cada círculo solo existía en un `title`, es
 *    decir, al pasar el cursor: inexistente en móvil.
 *  - Una tendencia de 30 días no responde "¿cómo estoy hoy?", que es la
 *    única pregunta de esa pantalla.
 *
 * Ahora es un calendario real: columnas por día de la semana con su
 * cabecera, filas por semana, el número de cada día escrito, y una
 * barra cuya ALTURA además del color codifica el nivel. Los días sin
 * dato se quedan vacíos en su casilla en vez de desaparecer: ver un
 * hueco es la información de que ese día no se sincronizó (doctrina 6).
 */
export function ReadinessTrendCard({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  /** Al cambiar, vuelve a pedir el historial (tras un check-in nuevo). */
  refreshKey?: number;
}) {
  const [historial, setHistorial] = useState<ReadinessResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getReadinessHistory(userId, 30)
      .then((datos) => {
        if (!cancelado) setHistorial(datos);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar el historial de recuperación."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey, intentos]);

  const encabezado = (
    <div className="mb-4">
      <h2 className="t-section text-ink">Recuperación día a día</h2>
      <p className="t-secondary mt-1 text-ink-3">Últimos 30 días.</p>
    </div>
  );

  if (error) {
    return (
      <Card>
        {encabezado}
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      </Card>
    );
  }

  if (historial === null) {
    return (
      <Card>
        {encabezado}
        <LoadingState lines={3} />
      </Card>
    );
  }

  const diario = dedupeUltimaPorDia(historial);

  if (diario.length === 0) {
    return (
      <Card>
        {encabezado}
        <EmptyState message="Todavía no hay ningún día con recuperación calculada. Se calcula sola con cada sincronización de Garmin." />
      </Card>
    );
  }

  const porFecha = new Map<string, Zona>(diario.map((d) => [d.fecha, d.resultado]));
  const fechas = diario.map((d) => d.fecha).sort();
  const primera = aFechaLocal(fechas[0]);
  const ultima = aFechaLocal(fechas[fechas.length - 1]);

  // La rejilla arranca el lunes de la primera semana con dato y termina
  // el domingo de la última: así cada columna es SIEMPRE el mismo día de
  // la semana, que es lo que permite leerlo como un calendario.
  const inicio = new Date(primera.getTime() - indiceSemana(primera) * MS_POR_DIA);
  const fin = new Date(ultima.getTime() + (6 - indiceSemana(ultima)) * MS_POR_DIA);

  const celdas: { iso: string; dia: number; zona: Zona | null; enPeriodo: boolean }[] = [];
  for (let t = inicio.getTime(); t <= fin.getTime(); t += MS_POR_DIA) {
    const fecha = new Date(t);
    const iso = aIso(fecha);
    celdas.push({
      iso,
      dia: fecha.getDate(),
      zona: porFecha.get(iso) ?? null,
      // Las casillas que completan la primera y la última semana caen
      // FUERA del periodo: pintarlas como "sin datos" hacía parecer que
      // esos días habían fallado al sincronizar (los seis primeros
      // huecos de la captura de auditoría).
      enPeriodo: iso >= fechas[0] && iso <= fechas[fechas.length - 1],
    });
  }

  const totales = (["green", "yellow", "red"] as const).map((zona) => ({
    zona,
    dias: diario.filter((d) => d.resultado === zona).length,
  }));

  return (
    <Card>
      {encabezado}

      <div role="grid" aria-label="Recuperación por día" className="flex flex-col gap-1">
        <div role="row" className="grid grid-cols-7 gap-1">
          {CABECERAS_SEMANA.map((inicial, i) => (
            <div
              key={inicial}
              role="columnheader"
              aria-label={DIAS_SEMANA_COMPLETOS[i]}
              className="t-micro pb-1 text-center text-ink-3"
            >
              {inicial}
            </div>
          ))}
        </div>
        {Array.from({ length: celdas.length / 7 }, (_, semana) => (
          <div role="row" key={semana} className="grid grid-cols-7 gap-1">
            {celdas.slice(semana * 7, semana * 7 + 7).map((celda) => (
              <Celda key={celda.iso} {...celda} />
            ))}
          </div>
        ))}
      </div>

      {/* Leyenda con las cifras escritas: es también el resumen del mes,
          y hace que el significado de cada altura/color exista como
          texto y no solo como forma. */}
      <dl className="mt-4 divide-y divide-line">
        {totales.map(({ zona, dias }) => (
          <div key={zona} className="flex items-baseline justify-between gap-6 py-2">
            <dt className="t-body flex items-center gap-2 text-ink-2">
              {/* `w-4`, no `w-2`: la muestra de la leyenda tiene que
                  parecerse a la marca del calendario, y con 2px de ancho
                  la barra verde salía vertical (8x16) mientras que en la
                  rejilla es horizontal y ancha. */}
              <span
                aria-hidden="true"
                className={`w-4 rounded-sm ${NIVEL[zona].color} ${NIVEL[zona].alto}`}
              />
              {NIVEL[zona].label}
            </dt>
            <dd className="t-body tabular text-ink">{plural(dias, "día", "días")}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function Celda({
  iso,
  dia,
  zona,
  enPeriodo,
}: {
  iso: string;
  dia: number;
  zona: Zona | null;
  enPeriodo: boolean;
}) {
  const nivel = zona ? NIVEL[zona] : null;

  // Fuera del periodo la casilla existe solo para que la columna siga
  // siendo el mismo día de la semana: sin borde, sin barra y con el
  // número atenuado, para que no se lea como un día que falta.
  if (!enPeriodo) {
    return (
      <div
        role="gridcell"
        data-testid="readiness-fuera"
        aria-label={`${fechaCorta(iso)}: fuera del periodo`}
        className="flex h-11 flex-col items-center justify-end py-1 opacity-40"
      >
        <span className="t-micro tabular text-ink-3">{dia}</span>
      </div>
    );
  }

  return (
    <div
      role="gridcell"
      data-testid="readiness-dia"
      aria-label={`${fechaCorta(iso)}: ${nivel ? nivel.label.toLowerCase() : "sin datos"}`}
      className="flex h-11 flex-col items-center justify-end gap-1 rounded border border-line py-1"
    >
      <span className="t-micro tabular text-ink-3">{dia}</span>
      {nivel ? (
        <span aria-hidden="true" className={`w-full rounded-sm ${nivel.color} ${nivel.alto}`} />
      ) : (
        // Hueco real: ese día no tiene dato, y no es un cero. Se marca
        // con una línea discontinua y no con una barra gris: una barra,
        // aunque fuese gris, competía en forma con las de nivel y a un
        // píxel era indistinguible de un día de recuperación baja.
        <span aria-hidden="true" className="w-full border-b border-dashed border-line-strong" />
      )}
    </div>
  );
}
