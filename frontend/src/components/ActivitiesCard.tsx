"use client";

import { Fragment, useEffect, useState } from "react";
import { api, ApiError, type GarminActivity } from "@/lib/api";
import { formatDistancia, formatDuracion, nombreActividad } from "@/lib/activityFormat";
import { fechaRelativa, plural } from "@/lib/fechas";
import { IconoDeporte } from "@/lib/iconosDeporte";
import { CoachNarrativeBlock } from "./CoachNarrativeBlock";
import { ExerciseSetsDetail } from "./ExerciseSetsDetail";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { Table, Td, TdNum } from "./ui/Table";
import { WeeklyVolumeChart } from "./WeeklyVolumeChart";

const DIAS_VENTANA = 90;

/**
 * Sesiones de entrenamiento (Design System v3).
 *
 * Unifica `GarminActivitiesCard` (vista sin filtrar) y
 * `SportActivityHistoryCard` (vista por deporte), que eran dos
 * componentes casi idénticos: el segundo era el primero más una
 * narrativa, una gráfica de volumen y el desglose de series. Ahora es un
 * solo componente y `categoria` decide qué añadir.
 *
 * Lo que cambia respecto a v2, todo por hallazgos de la auditoría:
 *
 *  - **Tabla real, no 40 tarjetas.** Cada actividad era una tarjeta con
 *    borde propio, un chip de color con el icono del deporte y las
 *    etiquetas "DURACIÓN"/"DISTANCIA" repetidas en cada fila.
 *  - **Sin "0.0 km" en las sesiones de fuerza**, y sin la columna
 *    entera cuando ninguna sesión de la lista tiene distancia.
 *  - **Nombres en español** ("Fuerza", no "strength training") y
 *    **fechas humanas** ("Hoy", "Ayer", "12 sep", no "2026-08-01").
 *  - **El desglose de series se abre con un botón real**
 *    (`aria-expanded`), no con un `onClick` en un `div`, que era
 *    invisible para el teclado y para un lector de pantalla.
 */
export function ActivitiesCard({
  userId,
  categoria,
  titulo,
  mensajeVacio,
}: {
  userId: number;
  categoria?: "running" | "ciclismo" | "gimnasio";
  titulo: string;
  mensajeVacio: string;
}) {
  const [actividades, setActividades] = useState<GarminActivity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);
  const [expandida, setExpandida] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    api
      .getGarminActivities(userId, DIAS_VENTANA, undefined, categoria)
      .then((datos) => {
        if (cancelado) return;
        setActividades(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el historial.");
      });
    return () => {
      cancelado = true;
    };
  }, [userId, categoria, intentos]);

  if (error) {
    return (
      <Card>
        <Encabezado titulo={titulo} />
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

  if (actividades === null) {
    return (
      <Card>
        <Encabezado titulo={titulo} />
        <LoadingState lines={3} />
      </Card>
    );
  }

  if (actividades.length === 0) {
    return (
      <Card>
        <Encabezado titulo={titulo} />
        <EmptyState message={mensajeVacio} />
      </Card>
    );
  }

  // La columna solo existe si alguna sesión tiene ese dato: una columna
  // "Distancia" entera de guiones en una lista de fuerza ocupa sitio sin
  // informar de nada.
  const hayDistancia = actividades.some((a) => formatDistancia(a.distancia_m) !== null);
  const hayPulso = actividades.some((a) => a.hr_avg !== null);
  const esGimnasio = categoria === "gimnasio";

  // Cuatro columnas y no cinco: la fecha va bajo el nombre de la sesión.
  // Cinco no caben a 390px de ninguna manera - descontando márgenes,
  // gotera y las tres columnas de cifras (que no se pueden partir),
  // al nombre le quedaban 40px y "Natación en piscina" salía en tres
  // líneas, con las filas de altos desiguales. La fecha debajo no es
  // una línea partida: es otro dato (doctrina 4).
  //
  // Y "Pulso" en vez de "FC media": una cabecera de una palabra, en el
  // mismo vocabulario que el resto de la app ("Pulso reposo" en Hoy).
  const cabeceras = [
    { clave: "sesion", label: "Sesión" },
    { clave: "duracion", label: "Duración", numerica: true },
    ...(hayDistancia ? [{ clave: "distancia", label: "Distancia", numerica: true }] : []),
    ...(hayPulso ? [{ clave: "pulso", label: "Pulso", numerica: true }] : []),
  ];

  return (
    <Card plano>
      <div className="p-5">
        <Encabezado
          titulo={titulo}
          detalle={`${plural(actividades.length, "sesión", "sesiones")} en ${DIAS_VENTANA} días`}
        />
        {categoria && <CoachNarrativeBlock userId={userId} categoria={categoria} />}
      </div>

      {/* Orden de lectura: qué significa (narrativa, cuando hay deporte
          concreto) → cuánto llevo esta semana → cada sesión. La gráfica
          estaba al final, detrás de 27 filas de tabla, donde no la veía
          nadie. También en "Todas" (sin `categoria`), donde la pestaña
          se acababa en la fila 27 sin decir en ningún momento cuánto se
          había entrenado esta semana. En esa vista la métrica es la
          duración: sumar los kilómetros de una carrera con los de una
          salida en bici da una cifra que no significa nada. */}
      <WeeklyVolumeChart
        userId={userId}
        categoria={categoria}
        metrica={categoria && !esGimnasio ? "distancia" : "duracion"}
      />

      <div className="border-t border-line px-5 pb-5 pt-1">
        <Table cabeceras={cabeceras} etiqueta={`Sesiones de ${titulo.toLowerCase()}`}>
          {actividades.map((act) => {
            const abierta = expandida === act.activity_id;
            const nombre = nombreActividad(act.tipo);
            return (
              <Fragment key={act.activity_id}>
                <tr>
                  <Td envolver>
                    {/* El icono identifica el deporte de la fila (regla
                        cero: iconos solo cuando identifican algo). En una
                        lista de 27 sesiones mezcladas es lo que permite
                        localizar las carreras sin leerlas todas. */}
                    <span className="flex items-baseline gap-2">
                      <IconoDeporte tipo={act.tipo} />
                      {esGimnasio ? (
                        <button
                          type="button"
                          aria-expanded={abierta}
                          onClick={() => setExpandida(abierta ? null : act.activity_id)}
                          className="t-body rounded text-left text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
                        >
                          {nombre}
                        </button>
                      ) : (
                        nombre
                      )}
                    </span>
                    <span className="t-secondary block text-ink-3">{fechaRelativa(act.fecha)}</span>
                  </Td>
                  <TdNum>{formatDuracion(act.duracion_seg)}</TdNum>
                  {hayDistancia && <TdNum>{formatDistancia(act.distancia_m)}</TdNum>}
                  {hayPulso && <TdNum>{act.hr_avg !== null ? `${act.hr_avg} ppm` : null}</TdNum>}
                </tr>
                {abierta && (
                  <tr>
                    <td colSpan={cabeceras.length} className="pb-4">
                      <ExerciseSetsDetail userId={userId} activityId={act.activity_id} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </Table>
      </div>
    </Card>
  );
}

function Encabezado({ titulo, detalle }: { titulo: string; detalle?: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
      <h2 className="t-section text-ink">{titulo}</h2>
      {detalle && <span className="t-secondary text-ink-3">{detalle}</span>}
    </div>
  );
}
