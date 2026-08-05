"use client";

import { useState } from "react";
import { api, ApiError, SESSION_TYPES, todayLocalDate, type DailySessionResult, type SessionTypeValue } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";

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

const inputClass =
  "border border-white/10 bg-black/30 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-strain";

export function DailySessionCard({ userId }: { userId: number }) {
  const [modoAutomatico, setModoAutomatico] = useState(true);
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
        ...(modoAutomatico ? {} : { planned_session: plannedSession }),
      });
      setResultado(r);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 400
            ? modoAutomatico
              ? "No hay readiness de hoy o no tienes un plan semanal activo. Haz el check-in y/o activa un plan semanal abajo (o elige manualmente)."
              : "Necesitas hacer el check-in de recuperación de hoy primero."
            : err.message
          : String(err)
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardTitle>Sesión de hoy</CardTitle>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={modoAutomatico}
            onChange={(e) => setModoAutomatico(e.target.checked)}
            className="h-4 w-4 accent-strain"
          />
          Derivar automáticamente de mi plan semanal
        </label>
        {!modoAutomatico && (
          <label className="flex flex-col gap-1 text-sm text-gray-300">
            ¿Qué tocaba hoy según tu plan?
            <select
              className={inputClass}
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
        )}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <Button type="submit" variant="strain" disabled={submitting} className="self-start">
          {submitting ? "Consultando..." : "Ver decisión del coach"}
        </Button>
      </form>
      {resultado && (
        <div className="mt-5 p-5 rounded-xl bg-black/30 border border-strain/20">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="font-display text-4xl font-bold text-strain">
              {resultado.volume_pct}%
            </span>
            <span className="text-lg font-semibold text-white">
              {LABELS[resultado.session_type as SessionTypeValue] ?? resultado.session_type}
            </span>
            {resultado.intensity_rpe_cap !== null && (
              <span className="text-sm text-gray-400">RPE máx {resultado.intensity_rpe_cap}</span>
            )}
          </div>
          <div className="mt-3 h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-strain transition-all duration-700 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, resultado.volume_pct))}%` }}
            />
          </div>
          <p className="text-sm text-gray-300 mt-4">{resultado.narrative_text}</p>
          <p className="text-xs text-gray-400 mt-2 uppercase tracking-wide">
            Explicación generada por: {resultado.narrative_source === "llm" ? "IA (Gemini)" : "plantilla"}
          </p>
        </div>
      )}
    </Card>
  );
}
