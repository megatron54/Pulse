"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, todayLocalDate, type TrainingBlock } from "@/lib/api";
import { fechaCorta } from "@/lib/fechas";
import { nombreObjetivo } from "@/lib/objetivosEntrenamiento";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { Table, Td } from "./ui/Table";

/** Un plan cubre el día de hoy, ya terminó, o aún no ha empezado. Son
 *  tres estados distintos con tres consecuencias distintas, y sin
 *  distinguirlos "tengo 4 planes" no dice nada útil. */
type Estado = "activo" | "futuro" | "terminado";

const ETIQUETA_ESTADO: Record<Estado, string> = {
  activo: "En curso",
  futuro: "Aún no empieza",
  terminado: "Terminado",
};

function estadoDe(plan: TrainingBlock, hoy: string): Estado {
  if (plan.fecha_fin < hoy) return "terminado";
  if (plan.fecha_inicio > hoy) return "futuro";
  return "activo";
}

/** Dos planes se pisan si sus rangos de fechas se cruzan (comparación
 *  directa de cadenas ISO: `YYYY-MM-DD` ordena igual como texto que
 *  como fecha). */
function seSolapan(a: TrainingBlock, b: TrainingBlock): boolean {
  return a.fecha_inicio <= b.fecha_fin && b.fecha_inicio <= a.fecha_fin;
}

/**
 * Los planes de entrenamiento del usuario, y si alguno se pisa con otro.
 *
 * Existe por un fallo real y confuso: dos bloques creados sobre las
 * mismas fechas dejaban a "Hoy" sin poder decidir la sesión, porque el
 * backend no desambigua en silencio cuál de los dos manda (ver
 * `repositories.training_block_repository.get_planned_session_for_date`).
 * El usuario veía "no se puede calcular la sesión" sin ninguna pista de
 * que tenía dos planes solapados, y la aplicación no le ofrecía ninguna
 * forma de verlos ni de borrar uno: la única salida era entrar a la base
 * de datos a mano.
 *
 * El solapamiento se marca en la fila implicada y no solo con un aviso
 * general arriba: con cuatro planes en la tabla, "tienes planes que se
 * pisan" obliga a comparar fechas a ojo para saber cuáles.
 */
export function PlanesActivosCard({
  userId,
  refreshKey = 0,
}: {
  userId: number;
  refreshKey?: number;
}) {
  const [planes, setPlanes] = useState<TrainingBlock[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  const recargar = useCallback(() => setIntentos((n) => n + 1), []);

  useEffect(() => {
    let cancelado = false;
    api
      .listTrainingBlocks(userId)
      .then((r) => {
        if (cancelado) return;
        setError(null);
        setPlanes(r);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudieron cargar tus planes.",
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos, refreshKey]);

  if (error) {
    return (
      <Card>
        <h2 className="t-section mb-4 text-ink">Mis planes</h2>
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            recargar();
          }}
        />
      </Card>
    );
  }

  if (planes === null) {
    return (
      <Card>
        <h2 className="t-section mb-4 text-ink">Mis planes</h2>
        <LoadingState lines={3} />
      </Card>
    );
  }

  if (planes.length === 0) {
    return (
      <Card>
        <h2 className="t-section mb-4 text-ink">Mis planes</h2>
        <EmptyState message="Todavía no has creado ningún plan. Rellena el plan semanal de abajo y Pulse podrá decidir qué te toca entrenar cada día." />
      </Card>
    );
  }

  const hoy = todayLocalDate();
  const solapados = new Set(
    planes
      .filter((p) => planes.some((otro) => otro.id !== p.id && seSolapan(p, otro)))
      .map((p) => p.id),
  );

  return (
    <Card plano>
      <div className="p-5 pb-0">
        <h2 className="t-section text-ink">Mis planes</h2>
        {solapados.size > 0 && (
          // Color como información y nada más (doctrina 1): el aviso no
          // lleva fondo ni borde de color, solo la tinta de "atención"
          // en el texto que de verdad avisa.
          <p className="t-body mt-2 max-w-prose text-pretty text-warn">
            {solapados.size === 2
              ? "Dos de tus planes se pisan en las mismas fechas, así que Pulse no sabe cuál manda y no puede decidir la sesión del día. Borra el que ya no sigas."
              : "Varios de tus planes se pisan en las mismas fechas, así que Pulse no sabe cuál manda y no puede decidir la sesión del día. Borra los que ya no sigas."}
          </p>
        )}
      </div>
      {/* `pt-4` y no un `gap`: el encabezado de la tabla quedaba pegado
          al párrafo de aviso y las dos líneas se leían como un bloque
          de texto continuo. */}
      <div className="px-5 pb-1 pt-4">
        <Table
          etiqueta="Planes de entrenamiento"
          cabeceras={[
            { clave: "plan", label: "Plan" },
            { clave: "estado", label: "Estado" },
            { clave: "accion", label: "" },
          ]}
        >
          {planes.map((plan) => {
            const estado = estadoDe(plan, hoy);
            return (
              <tr key={plan.id}>
                <Td envolver>
                  <span className="block">{nombreObjetivo(plan.objetivo_prioritario)}</span>
                  {/* La fecha bajo el nombre no es una línea partida:
                      es otro dato (doctrina 4). */}
                  <span className="t-secondary block text-ink-3">
                    {fechaCorta(plan.fecha_inicio)} – {fechaCorta(plan.fecha_fin)}
                  </span>
                </Td>
                <Td secundaria envolver>
                  <span className={estado === "activo" ? "text-ink" : undefined}>
                    {ETIQUETA_ESTADO[estado]}
                  </span>
                  {solapados.has(plan.id) && (
                    <span className="block text-warn">Se pisa con otro plan</span>
                  )}
                </Td>
                <td className="py-3 pr-4 text-right align-top last:pr-0">
                  <BorrarPlan userId={userId} plan={plan} alBorrar={recargar} />
                </td>
              </tr>
            );
          })}
        </Table>
      </div>
    </Card>
  );
}

/**
 * Borrado en dos pasos, a propósito: se lleva por delante el plan
 * semanal completo de varias semanas y no hay deshacer. Un único botón
 * "Borrar" a un clic de distancia, en una tabla donde las filas se
 * parecen entre sí, es demasiado fácil de pulsar en la fila
 * equivocada.
 *
 * La confirmación nombra el plan en vez de decir "¿seguro?": lo que hay
 * que verificar antes de aceptar es exactamente CUÁL se va a borrar.
 */
function BorrarPlan({
  userId,
  plan,
  alBorrar,
}: {
  userId: number;
  plan: TrainingBlock;
  alBorrar: () => void;
}) {
  const [confirmando, setConfirmando] = useState(false);
  const [fallo, setFallo] = useState(false);
  const [borrando, setBorrando] = useState(false);

  async function borrar() {
    setBorrando(true);
    setFallo(false);
    try {
      await api.deleteTrainingBlock(userId, plan.id);
      alBorrar();
    } catch {
      setFallo(true);
      setBorrando(false);
      setConfirmando(false);
    }
  }

  if (!confirmando) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Button variant="ghost" onClick={() => setConfirmando(true)}>
          Borrar
        </Button>
        {fallo && (
          <p role="alert" className="t-secondary text-neg">
            No se pudo borrar. Vuelve a intentarlo.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <p className="t-secondary text-pretty text-ink-2">
        ¿Borrar «{nombreObjetivo(plan.objetivo_prioritario)}» ({fechaCorta(plan.fecha_inicio)} –{" "}
        {fechaCorta(plan.fecha_fin)})?
      </p>
      <div className="flex items-center gap-1">
        <Button variant="ghost" onClick={() => setConfirmando(false)} disabled={borrando}>
          Cancelar
        </Button>
        <Button onClick={borrar} disabled={borrando}>
          {borrando ? "Borrando…" : "Sí, borrar"}
        </Button>
      </div>
    </div>
  );
}
