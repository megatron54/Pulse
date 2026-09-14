"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, type GarminHealthDay } from "@/lib/api";
import { fechaRelativa, plural } from "@/lib/fechas";
import { METRICAS_SALUD, type MetricaSalud } from "@/lib/metricasSalud";
import { TrendChart } from "./ui/TrendChart";
import { SegmentedControl } from "./ui/SegmentedControl";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { FasesSueno, horasYMinutos, segundosDormidos } from "./ui/FasesSueno";

const RANGOS = [
  { dias: 7, label: "7 días" },
  { dias: 30, label: "30 días" },
  { dias: 90, label: "90 días" },
] as const;

/**
 * Entrenamiento › Recuperación: histórico completo de recovery de Garmin
 * (Design System v3).
 *
 * Cambios respecto a v2, por hallazgos de la auditoría:
 *
 *  - **Un solo color de datos.** Cada gráfica llevaba el suyo (verde
 *    neón, azul, violeta, rojo), lo que sugería una semántica que no
 *    existe: el color no significaba nada porque todas las series son
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
 *
 * Los nombres, unidades y explicaciones ya no viven aquí: están en
 * `@/lib/metricasSalud`, compartidos con la página de detalle de cada
 * métrica, a la que llevan los títulos de sección.
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
      {METRICAS_SALUD.map((metrica) => (
        <MetricaSeccion key={metrica.campo} metrica={metrica} datos={cronologico} />
      ))}
      <FasesSuenoSeccion datos={cronologico} />
    </Card>
  );
}

/** Fases de la última noche con datos. El detalle noche a noche (y el
 *  poder elegir cuál mirar) vive en `/salud/sueno`, a un enlace de
 *  aquí: esta tarjeta responde "cómo voy", no "qué pasó el martes". */
function FasesSuenoSeccion({ datos }: { datos: GarminHealthDay[] }) {
  const ultimoConFases = [...datos].reverse().find((d) => d.deep_sleep_seg != null);
  if (!ultimoConFases) return null;

  const total =
    segundosDormidos(ultimoConFases) + (ultimoConFases.awake_sleep_seg ?? 0);
  if (total === 0) return null;

  return (
    <section className="border-t border-line px-5 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="t-section text-ink">Fases de sueño</h3>
        <span className="t-body tabular text-ink">{horasYMinutos(total)}</span>
      </div>
      <p className="t-secondary mt-1 text-ink-3">
        Noche de {fechaRelativa(ultimoConFases.fecha).toLowerCase()}. Las demás noches, en{" "}
        <Link href="/salud/sueno" className="text-ink-2 underline underline-offset-4">
          el detalle del sueño
        </Link>
        .
      </p>
      <div className="mt-3">
        <FasesSueno dia={ultimoConFases} />
      </div>
    </section>
  );
}

/** Una métrica de la ventana: última cifra, qué es, y su tendencia.
 *  El título es un enlace a `/salud/<slug>`, donde está el día a día en
 *  una tabla y se puede elegir la ventana: aquí la gráfica responde "por
 *  dónde voy", no "cuánto dormí el martes". */
function MetricaSeccion({
  metrica,
  datos,
}: {
  metrica: MetricaSalud;
  datos: GarminHealthDay[];
}) {
  const { slug, campo, titulo, unidad, decimales, explicacion, rango } = metrica;
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
        <h3 className="t-section text-ink">
          <Link href={`/salud/${slug}`} className="underline-offset-4 hover:underline">
            {titulo}
          </Link>
        </h3>
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
