"use client";

import { useState } from "react";
import {
  api,
  ApiError,
  DAYS_OF_WEEK,
  SESSION_TYPES,
  todayLocalDate,
  type DayOfWeek,
  type SessionTypeValue,
  type TrainingBlock,
} from "@/lib/api";
import { fechaCorta } from "@/lib/fechas";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { FormField, fieldInputClass } from "./ui/FormField";

const DIAS: Record<DayOfWeek, string> = {
  mon: "Lunes",
  tue: "Martes",
  wed: "Miércoles",
  thu: "Jueves",
  fri: "Viernes",
  sat: "Sábado",
  sun: "Domingo",
};

const SESSION_LABELS: Record<SessionTypeValue, string> = {
  rest: "Descanso",
  active_recovery: "Recuperación activa",
  strength_heavy: "Fuerza pesada",
  strength_hypertrophy: "Hipertrofia",
  endurance_intervals: "Intervalos de resistencia",
  endurance_long: "Resistencia larga",
  martial_arts_technical: "Artes marciales (técnica)",
  martial_arts_sparring: "Artes marciales (sparring)",
};

/** El backend acepta texto libre (`String(50)`), pero pedirle al usuario
 *  que escriba "strength, hypertrophy, running, bjj" - el placeholder de
 *  v2 - es pedirle que adivine el vocabulario interno en inglés. */
const OBJETIVOS = [
  { valor: "fuerza", label: "Ganar fuerza" },
  { valor: "hipertrofia", label: "Ganar masa muscular" },
  { valor: "resistencia", label: "Mejorar resistencia" },
  { valor: "artes_marciales", label: "Artes marciales" },
  { valor: "recomposicion", label: "Recomposición corporal" },
  { valor: "mantenimiento", label: "Mantenerme" },
] as const;

const DURACIONES = [4, 6, 8, 12] as const;

function sumarSemanas(fechaIso: string, semanas: number): string {
  const d = new Date(fechaIso + "T00:00:00");
  d.setDate(d.getDate() + semanas * 7);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
}

/**
 * Crear el plan semanal de un bloque de entrenamiento (Design System
 * v3).
 *
 * La tira de 7 chips de v2 (uno por día, con la inicial del día y un
 * `<select>` de 11px dentro de una caja de ~46px) es el ejemplo más
 * claro de la queja del usuario, "hay muchas palabras que se cortan":
 * "Intervalos de resistencia" era ilegible ahí dentro. Ahora es una
 * fila por día con el nombre completo del día y el desplegable a ancho
 * real: siete filas ocupan más alto, pero se leen.
 *
 * El objetivo del bloque pasa de texto libre en inglés a una lista de
 * opciones en español, y la duración deja de estar fijada a 6 semanas
 * en el código.
 */
export function WeeklyScheduleForm({
  userId,
  onCreated,
}: {
  userId: number;
  onCreated?: (block: TrainingBlock) => void;
}) {
  const [objetivo, setObjetivo] = useState<string>("fuerza");
  const [semanas, setSemanas] = useState<number>(6);
  const [fechaInicio, setFechaInicio] = useState(todayLocalDate());
  const [plan, setPlan] = useState<Partial<Record<DayOfWeek, SessionTypeValue>>>({
    mon: "strength_heavy",
    wed: "strength_hypertrophy",
    fri: "endurance_intervals",
  });
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [creado, setCreado] = useState<TrainingBlock | null>(null);

  function cambiarDia(dia: DayOfWeek, valor: string) {
    setPlan((previo) => {
      const siguiente = { ...previo };
      if (valor === "") {
        delete siguiente[dia];
      } else {
        siguiente[dia] = valor as SessionTypeValue;
      }
      return siguiente;
    });
  }

  const fechaFin = sumarSemanas(fechaInicio, semanas);
  const diasConEntreno = DAYS_OF_WEEK.filter((dia) => plan[dia]).length;

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const bloque = await api.createTrainingBlock(userId, {
        fecha_inicio: fechaInicio,
        fecha_fin: fechaFin,
        objetivo_prioritario: objetivo,
        weekly_schedule: plan,
      });
      setCreado(bloque);
      onCreated?.(bloque);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Card>
      <div className="mb-4">
        <h2 className="t-section text-ink">Plan semanal</h2>
        <p className="t-secondary mt-1 max-w-prose text-pretty text-ink-3">
          Di qué entrenas cada día de una semana tipo. A partir de ahí Pulse decide solo qué toca
          hoy, ajustando el volumen a tu recuperación: no tendrás que elegirlo a mano.
        </p>
      </div>

      <form onSubmit={enviar} className="flex flex-col gap-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Objetivo del bloque" htmlFor="objetivo-bloque">
            <select
              id="objetivo-bloque"
              className={fieldInputClass}
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
            >
              {OBJETIVOS.map((o) => (
                <option key={o.valor} value={o.valor}>
                  {o.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Empieza el" htmlFor="fecha-inicio-bloque">
            <input
              id="fecha-inicio-bloque"
              type="date"
              className={fieldInputClass}
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
            />
          </FormField>
          <FormField label="Duración" htmlFor="duracion-bloque">
            <select
              id="duracion-bloque"
              className={fieldInputClass}
              value={semanas}
              onChange={(e) => setSemanas(Number(e.target.value))}
            >
              {DURACIONES.map((n) => (
                <option key={n} value={n}>
                  {n} semanas
                </option>
              ))}
            </select>
          </FormField>
        </div>

        {/* Una fila por día, con el nombre del día completo y el
            desplegable a ancho real: nada se corta (doctrina 4). */}
        <div>
          <h3 className="t-micro mb-2 text-ink-3">Semana tipo</h3>
          <dl className="divide-y divide-line">
            {DAYS_OF_WEEK.map((dia) => (
              <div key={dia} className="flex items-center gap-4 py-2.5">
                {/* Ancho fijo para el nombre del día: con `justify-between`
                    el borde izquierdo de cada desplegable caía donde
                    acabara su etiqueta ("Lunes" / "Miércoles"), y los
                    siete quedaban desalineados en escalera. */}
                <label htmlFor={`dia-${dia}`} className="t-body w-24 shrink-0 text-ink-2">
                  {DIAS[dia]}
                </label>
                <select
                  id={`dia-${dia}`}
                  // `flex-1` y no `max-w-[60%]`: a 390px ese 60% son
                  // 160px y "Intervalos de resistencia" quedaba cortado
                  // por la flecha del desplegable - la misma queja de
                  // palabras cortadas, un nivel más abajo. El nombre del
                  // día ocupa poco, así que el desplegable se queda con
                  // todo el resto de la fila (tope en escritorio, donde
                  // un desplegable de 700px sería absurdo).
                  className="t-body min-h-9 min-w-0 flex-1 rounded-md border border-line bg-surface px-2.5 text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-ink sm:max-w-[22rem]"
                  value={plan[dia] ?? ""}
                  onChange={(e) => cambiarDia(dia, e.target.value)}
                >
                  <option value="">Descanso</option>
                  {SESSION_TYPES.filter((tipo) => tipo !== "rest").map((tipo) => (
                    <option key={tipo} value={tipo}>
                      {SESSION_LABELS[tipo]}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </dl>
        </div>

        <p className="t-secondary text-ink-3">
          {diasConEntreno === 0
            ? "Ahora mismo el plan es de descanso los siete días."
            : `${diasConEntreno} días de entreno por semana, del ${fechaCorta(fechaInicio)} al ${fechaCorta(fechaFin)}.`}
        </p>

        {error && (
          <p role="alert" className="t-body text-neg">
            {error}
          </p>
        )}
        <div>
          <Button type="submit" disabled={enviando}>
            {enviando ? "Activando…" : "Activar plan"}
          </Button>
        </div>
      </form>

      {creado && (
        <p role="status" className="t-body mt-4 text-pos">
          Plan activado del {fechaCorta(creado.fecha_inicio)} al {fechaCorta(creado.fecha_fin)}. Ya
          puedes ver la sesión de hoy en la pantalla de inicio.
        </p>
      )}
    </Card>
  );
}
