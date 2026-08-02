"use client";

import { useState } from "react";
import { api, ApiError, SESSION_TYPES, todayLocalDate, type DailySessionResult, type SessionTypeValue } from "@/lib/api";

const LABELS: Record<SessionTypeValue, string> = {
  rest: "Descanso",
  active_recovery: "Recuperación activa",
  strength_heavy: "Fuerza pesada",
  strength_hypertrophy: "Hipertrofia",
  endurance_intervals: "Intervalos de resistencia",
  endurance_long: "Resistencia larga",
  martial_arts_technical: "Artes marciales (técnica)",
  martial_arts_sparring: "Artes marciales (sparring)",
};

export function DailySessionCard({ userId }: { userId: number }) {
  const [plannedSession, setPlannedSession] = useState<SessionTypeValue>("strength_heavy");
  const [resultado, setResultado] = useState<DailySessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResultado(null);
    try {
      const r = await api.getDailySession(userId, {
        target_date: todayLocalDate(),
        planned_session: plannedSession,
      });
      setResultado(r);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 400
            ? "Necesitas hacer el check-in de recuperación de hoy primero."
            : err.message
          : String(err)
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-4">Sesión de hoy</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          ¿Qué tocaba hoy según tu plan?
          <select
            className="border rounded px-2 py-1"
            value={plannedSession}
            onChange={(e) => setPlannedSession(e.target.value as SessionTypeValue)}
          >
            {SESSION_TYPES.map((tipo) => (
              <option key={tipo} value={tipo}>
                {LABELS[tipo]}
              </option>
            ))}
          </select>
        </label>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="bg-black text-white rounded px-4 py-2 disabled:opacity-50 self-start"
        >
          {submitting ? "Consultando..." : "Ver decisión del coach"}
        </button>
      </form>
      {resultado && (
        <div className="mt-4 p-4 bg-gray-50 rounded">
          <p className="font-semibold">
            {LABELS[resultado.session_type as SessionTypeValue] ?? resultado.session_type} al{" "}
            {resultado.volume_pct}%
            {resultado.intensity_rpe_cap !== null && ` (RPE máx ${resultado.intensity_rpe_cap})`}
          </p>
          <p className="text-sm text-gray-700 mt-2">{resultado.narrative_text}</p>
          <p className="text-xs text-gray-400 mt-1">
            Explicación generada por: {resultado.narrative_source === "llm" ? "IA (Gemini)" : "plantilla"}
          </p>
        </div>
      )}
    </div>
  );
}
