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
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { FormField, fieldInputClass } from "./ui/FormField";

const DAY_LABELS: Record<DayOfWeek, string> = {
  mon: "Lunes",
  tue: "Martes",
  wed: "Miércoles",
  thu: "Jueves",
  fri: "Viernes",
  sat: "Sábado",
  sun: "Domingo",
};

const DAY_SHORT_LABELS: Record<DayOfWeek, string> = {
  mon: "L",
  tue: "M",
  wed: "X",
  thu: "J",
  fri: "V",
  sat: "S",
  sun: "D",
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

function addWeeks(dateStr: string, weeks: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + weeks * 7);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function WeeklyScheduleForm({
  userId,
  onCreated,
}: {
  userId: number;
  onCreated?: (block: TrainingBlock) => void;
}) {
  const [objetivo, setObjetivo] = useState("strength");
  const [fechaInicio, setFechaInicio] = useState(todayLocalDate());
  const [schedule, setSchedule] = useState<Partial<Record<DayOfWeek, SessionTypeValue>>>({
    mon: "strength_heavy",
    wed: "strength_hypertrophy",
    fri: "endurance_intervals",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(false);

  function updateDay(day: DayOfWeek, value: string) {
    setSchedule((prev) => {
      const next = { ...prev };
      if (value === "") {
        delete next[day];
      } else {
        next[day] = value as SessionTypeValue;
      }
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const block = await api.createTrainingBlock(userId, {
        fecha_inicio: fechaInicio,
        fecha_fin: addWeeks(fechaInicio, 6),
        objetivo_prioritario: objetivo,
        weekly_schedule: schedule,
      });
      setCreated(true);
      onCreated?.(block);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardTitle>Plan semanal (6 semanas)</CardTitle>
      <p className="text-sm text-text-secondary mb-4 -mt-2">
        Una vez creado, la app decide sola qué toca cada día combinándolo con tu recuperación -
        ya no hace falta elegirlo a mano en &quot;Sesión de hoy&quot;.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormField label="Objetivo prioritario del bloque" htmlFor="objetivo-bloque">
            <input
              id="objetivo-bloque"
              className={fieldInputClass}
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
              placeholder="ej. strength, hypertrophy, running, bjj"
            />
          </FormField>
          <FormField label="Fecha de inicio" htmlFor="fecha-inicio-bloque">
            <input
              id="fecha-inicio-bloque"
              type="date"
              className={fieldInputClass}
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
            />
          </FormField>
        </div>

        {/* Tira semanal tipo calendario (estilo Garmin Connect): un
            chip por día en vez de una lista vertical de <select>
            sueltos, misma jerarquía visual que un calendario real. */}
        <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
          {DAYS_OF_WEEK.map((day) => (
            <div
              key={day}
              className="flex flex-col gap-1.5 rounded-xl border border-surface-border bg-surface-muted p-2"
            >
              <span
                className="mx-auto flex size-6 items-center justify-center rounded-full bg-surface text-xs font-semibold text-foreground"
                title={DAY_LABELS[day]}
              >
                {DAY_SHORT_LABELS[day]}
              </span>
              <select
                aria-label={DAY_LABELS[day]}
                className="w-full rounded-lg border-0 bg-transparent px-1 py-1 text-center text-[11px] text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
                value={schedule[day] ?? ""}
                onChange={(e) => updateDay(day, e.target.value)}
              >
                <option value="">Descanso</option>
                {SESSION_TYPES.map((tipo) => (
                  <option key={tipo} value={tipo}>
                    {SESSION_LABELS[tipo]}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>

        {error && <p className="text-recovery-low text-sm">{error}</p>}
        <Button type="submit" disabled={submitting} className="self-start">
          {submitting ? "Creando..." : "Activar plan semanal"}
        </Button>
      </form>
      {created && (
        <p className="mt-3 text-recovery-high text-sm font-medium">Plan semanal activado.</p>
      )}
    </Card>
  );
}
