"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type GarminHealthDay } from "@/lib/api";
import { fechaRelativa, plural } from "@/lib/fechas";
import { TrendChart } from "./ui/TrendChart";
import { SegmentedControl } from "./ui/SegmentedControl";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

const RANGOS = [
  { dias: 7, label: "7 días" },
  { dias: 30, label: "30 días" },
  { dias: 90, label: "90 días" },
] as const;

type Campo = keyof Pick<
  GarminHealthDay,
  "hrv_value" | "body_battery_am" | "sleep_score" | "stress_avg" | "resting_hr" | "vo2max"
>;

/** Cada métrica con su nombre en español, su unidad y una frase que dice
 *  qué es. v2 titulaba "VFC (HRV)", "Sueño (score)", "VO2max" sin
 *  explicar ninguna: son las siglas del proveedor, no información. */
const METRICAS: readonly {
  campo: Campo;
  titulo: string;
  unidad: string;
  decimales: number;
  explicacion: string;
  /** Límites físicos de la métrica, cuando los tiene: el eje de la
   *  gráfica no debe rotular un Body Battery de -8 ni de 102. */
  rango?: readonly [number, number];
}[] = [
  {
    campo: "hrv_value",
    titulo: "Variabilidad cardíaca",
    unidad: " ms",
    decimales: 0,
    explicacion: "Cuánto varía el tiempo entre latidos por la noche. Es la señal principal de recuperación: cuando baja varios días seguidos, el cuerpo está acumulando fatiga.",
  },
  {
    campo: "body_battery_am",
    titulo: "Body Battery al despertar",
    unidad: "",
    decimales: 0,
    explicacion: "La estimación de energía disponible de Garmin al levantarte, de 0 a 100.",
    rango: [0, 100],
  },
  {
    campo: "sleep_score",
    titulo: "Calidad del sueño",
    unidad: "",
    decimales: 0,
    explicacion: "Puntuación de Garmin de 0 a 100 combinando duración, fases y descanso.",
    rango: [0, 100],
  },
  {
    campo: "stress_avg",
    titulo: "Estrés medio del día",
    unidad: "",
    decimales: 0,
    explicacion: "Media diaria de 0 a 100 estimada a partir del pulso y su variabilidad.",
    rango: [0, 100],
  },
  {
    campo: "resting_hr",
    titulo: "Pulso en reposo",
    unidad: " ppm",
    decimales: 0,
    explicacion: "Subidas sostenidas suelen acompañar a fatiga, falta de sueño o una infección.",
  },
  {
    campo: "vo2max",
    titulo: "VO₂ máx",
    unidad: " ml/kg/min",
    decimales: 1,
    explicacion: "Estimación de tu capacidad aeróbica. Se mueve despacio: cambios de semanas, no de días.",
  },
];

/**
 * Entrenamiento › Recuperación: histórico completo de recovery de Garmin
 * (Design System v3).
 *
 * Cambios respecto a v2, por hallazgos de la auditoría:
 *
 *  - **Un solo color de datos.** Cada gráfica llevaba el suyo (verde
 *    neón, azul, violeta, rojo), lo que sugería una semántica que no
 *    existe: el color no significaba nada porque las seis series son
 *    igual de neutras. Sigue en `TrendChart`.
 *  - **Nombres y explicaciones en español.** "VFC (HRV)" y "VO2max" no
 *    dicen al usuario qué está mirando ni si subir es bueno.
 *  - **Sin tarjeta por métrica**: una sola tarjeta con secciones
 *    separadas por una línea de 1px (doctrina 2).
 *  - **Rango en palabras** ("30 días") en vez de "30d", que en el
 *    control segmentado se leía como una abreviatura técnica.
 *
 * Se mantiene intacta la regla de "lo desconocido no es cero": una
 * métrica sin ningún dato en la ventana (ej. VO₂ máx en un reloj que no
 * lo calcula) no se dibuja en absoluto, nunca a cero.
 */
export function GarminHealthHistoryCard({ userId }: { userId: number }) {
  const [dias, setDias] = useState<(typeof RANGOS)[number]["dias"]>(90);
  const [historial, setHistorial] = useState<GarminHealthDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminHealthHistory(userId, dias)
      .then((datos) => {
        if (cancelado) return;
        setHistorial(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar el historial de recovery."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, dias, intentos]);

  // El backend devuelve más reciente primero (un punto por día, ya
  // deduplicado) y las gráficas esperan orden ascendente.
  const cronologico = historial ? [...historial].reverse() : [];

  const encabezado = (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
      <h2 className="t-section text-ink">Histórico de recuperación</h2>
      <SegmentedControl
        options={RANGOS.map((rango) => ({ value: String(rango.dias), label: rango.label }))}
        value={String(dias)}
        onChange={(v) => setDias(Number(v) as (typeof RANGOS)[number]["dias"])}
        ariaLabel="Rango temporal"
      />
    </div>
  );

  if (error) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
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
        <div className="mb-4">{encabezado}</div>
        <LoadingState lines={4} />
      </Card>
    );
  }

  if (historial.length === 0) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <EmptyState message="Garmin no ha sincronizado ningún día en esta ventana. Comprueba la conexión en Perfil › Conexiones o prueba con un rango más amplio." />
      </Card>
    );
  }

  return (
    <Card plano>
      <div className="p-5">
        {encabezado}
        {/* "90 días con datos en los últimos 90" era un trabalenguas.
            Solo se menciona la ventana cuando falta algún día en ella,
            que es cuando el número informa de algo. */}
        <p className="t-secondary mt-2 text-ink-3">
          {historial.length === dias
            ? `${plural(dias, "día", "días")}, todos con datos.`
            : `${plural(historial.length, "día con datos", "días con datos")} de los últimos ${dias}.`}
        </p>
      </div>
      {METRICAS.map((metrica) => (
        <MetricaSeccion key={metrica.campo} {...metrica} datos={cronologico} />
      ))}
      <FasesSuenoSeccion datos={cronologico} />
    </Card>
  );
}

/** Fases de sueño de la última noche con datos. Una barra apilada y no
 *  una tendencia porque lo que importa es la PROPORCIÓN entre fases de
 *  una noche concreta.
 *
 *  v3: los cuatro colores independientes (índigo, violeta, lila, gris)
 *  se sustituyen por una escala del mismo color de datos. Las fases son
 *  una sola magnitud dividida en partes, y una escala lo dice; cuatro
 *  colores distintos sugieren cuatro cosas sin relación. */
const FASES_SUENO = [
  { campo: "deep_sleep_seg", label: "Profundo", opacidad: 1 },
  { campo: "rem_sleep_seg", label: "REM", opacidad: 0.7 },
  { campo: "light_sleep_seg", label: "Ligero", opacidad: 0.42 },
  { campo: "awake_sleep_seg", label: "Despierto", opacidad: 0.18 },
] as const;

function FasesSuenoSeccion({ datos }: { datos: GarminHealthDay[] }) {
  const ultimoConFases = [...datos].reverse().find((d) => d.deep_sleep_seg != null);
  if (!ultimoConFases) return null;

  const segundos = FASES_SUENO.map((fase) => ultimoConFases[fase.campo] ?? 0);
  const total = segundos.reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  return (
    <section className="border-t border-line px-5 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="t-section text-ink">Fases de sueño</h3>
        <span className="t-body tabular text-ink">{horasYMinutos(total)}</span>
      </div>
      <p className="t-secondary mt-1 text-ink-3">
        Noche de {fechaRelativa(ultimoConFases.fecha).toLowerCase()}.
      </p>
      <div className="mt-3 flex h-2 w-full overflow-hidden rounded-full bg-canvas">
        {FASES_SUENO.map((fase, i) => {
          const valor = segundos[i];
          if (valor === 0) return null;
          return (
            <div
              key={fase.campo}
              style={{
                width: `${(valor / total) * 100}%`,
                backgroundColor: "var(--data)",
                opacity: fase.opacidad,
              }}
            />
          );
        })}
      </div>
      {/* Leyenda con la cifra escrita: la barra sola obligaba a pasar el
          cursor por encima (`title`), imposible en móvil. */}
      <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(7rem,1fr))] gap-x-6 gap-y-2">
        {FASES_SUENO.map((fase, i) => {
          const valor = segundos[i];
          if (valor === 0) return null;
          return (
            <div key={fase.campo} className="flex items-baseline gap-2">
              <span
                aria-hidden="true"
                className="size-2 shrink-0 translate-y-[-1px] rounded-full"
                style={{ backgroundColor: "var(--data)", opacity: fase.opacidad }}
              />
              <dt className="t-secondary text-ink-2">{fase.label}</dt>
              <dd className="t-secondary tabular ml-auto text-ink">{horasYMinutos(valor)}</dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

function horasYMinutos(segundos: number): string {
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`;
}

function MetricaSeccion({
  titulo,
  unidad,
  decimales,
  explicacion,
  datos,
  campo,
  rango,
}: {
  titulo: string;
  unidad: string;
  decimales: number;
  explicacion: string;
  datos: GarminHealthDay[];
  campo: Campo;
  rango?: readonly [number, number];
}) {
  const puntos = datos
    // `!= null` (laxo) en vez de `!== null`: defensa en profundidad si
    // el backend alguna vez omitiera la clave del todo (undefined) en
    // vez de mandar null explícito - el tipo GarminHealthDay lo
    // garantiza hoy, pero request() hace JSON.parse crudo sin validar
    // el payload en runtime (hallazgo de @code-reviewer).
    .filter((d) => d[campo] != null)
    .map((d) => ({ fecha: d.fecha, valor: d[campo] as number }));

  // "Lo desconocido no es cero": si NINGÚN día de la ventana tiene este
  // campo, la sección no existe.
  if (puntos.length === 0) return null;

  const ultimo = puntos[puntos.length - 1];

  return (
    <section className="border-t border-line px-5 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="t-section text-ink">{titulo}</h3>
        <span className="t-body tabular text-ink">
          {ultimo.valor.toFixed(decimales)}
          {unidad}
          <span className="t-secondary text-ink-3"> · {fechaRelativa(ultimo.fecha).toLowerCase()}</span>
        </span>
      </div>
      <p className="t-secondary mt-1 max-w-prose text-pretty text-ink-3">{explicacion}</p>
      {/* Con menos de dos días no hay tendencia: la cifra de arriba ya
          lo dice todo y una gráfica de un punto era otro hallazgo de la
          auditoría. */}
      {puntos.length >= 2 && (
        <div className="mt-3">
          <TrendChart
            data={puntos}
            unidad={unidad}
            decimales={decimales}
            rango={rango}
            etiqueta={titulo}
            alto={150}
          />
        </div>
      )}
    </section>
  );
}
