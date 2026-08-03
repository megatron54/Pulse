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

const inputClass =
  "border border-white/10 bg-black/30 rounded-lg px-3 py-2 text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-teal";

const DAY_LABELS: Record<DayOfWeek, string> = {
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
      <p className="text-sm text-gray-400 mb-4 -mt-2">
        Una vez creado, la app decide sola qué toca cada día combinándolo con tu recuperación -
        ya no hace falta elegirlo a mano en &quot;Sesión de hoy&quot;.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Objetivo prioritario del bloque
          <input
            className={inputClass}
            value={objetivo}
            onChange={(e) => setObjetivo(e.target.value)}
            placeholder="ej. strength, hypertrophy, running, bjj"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Fecha de inicio
          <input
            type="date"
            className={inputClass}
            value={fechaInicio}
            onChange={(e) => setFechaInicio(e.target.value)}
          />
        </label>
        <div className="grid grid-cols-1 gap-2">
          {DAYS_OF_WEEK.map((day) => (
            <label key={day} className="flex items-center gap-2 text-sm text-gray-300">
              <span className="w-24">{DAY_LABELS[day]}</span>
              <select
                className={`${inputClass} flex-1`}
                value={schedule[day] ?? ""}
                onChange={(e) => updateDay(day, e.target.value)}
              >
                <option value="">— sin plan (descanso implícito) —</option>
                {SESSION_TYPES.map((tipo) => (
                  <option key={tipo} value={tipo}>
                    {SESSION_LABELS[tipo]}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="bg-teal text-black font-semibold rounded-lg px-4 py-2.5 disabled:bg-surface disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:scale-100 self-start transition-transform hover:scale-[1.02] active:scale-[0.98]"
        >
          {submitting ? "Creando..." : "Activar plan semanal"}
        </button>
      </form>
      {created && (
        <p className="mt-3 text-[#16EC06] text-sm font-medium">Plan semanal activado.</p>
      )}
    </Card>
  );
}
