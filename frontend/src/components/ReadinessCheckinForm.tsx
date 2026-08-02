"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type ReadinessResult } from "@/lib/api";

const READINESS_COLORS: Record<string, string> = {
  green: "bg-green-100 text-green-800",
  yellow: "bg-yellow-100 text-yellow-800",
  red: "bg-red-100 text-red-800",
};

export function ReadinessCheckinForm({
  userId,
  onResult,
}: {
  userId: number;
  onResult?: (r: ReadinessResult) => void;
}) {
  const [hrvToday, setHrvToday] = useState(65);
  const [hrvBaseline, setHrvBaseline] = useState(65);
  const [bodyBattery, setBodyBattery] = useState(80);
  const [sleepScore, setSleepScore] = useState(85);
  const [trainingReadiness, setTrainingReadiness] = useState<
    "high" | "moderate" | "low" | "very_low"
  >("high");
  const [acwr, setAcwr] = useState(1.0);
  const [jointPain, setJointPain] = useState(false);
  const [resultado, setResultado] = useState<ReadinessResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResultado(null);
    try {
      const r = await api.manualReadinessCheckin(userId, {
        target_date: todayLocalDate(),
        hrv_today: hrvToday,
        hrv_baseline_28d: hrvBaseline,
        hrv_trend_7d: 0,
        body_battery_am: bodyBattery,
        training_readiness: trainingReadiness,
        sleep_score: sleepScore,
        acwr,
        joint_pain_flag: jointPain,
      });
      setResultado(r);
      onResult?.(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border rounded-lg p-6">
      <h2 className="text-lg font-semibold mb-1">Check-in de recuperación</h2>
      <p className="text-sm text-gray-500 mb-4">
        Manual mientras la sincronización con Garmin real siga pendiente (Fase H).
      </p>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          HRV hoy (ms)
          <input
            type="number"
            min={1}
            className="border rounded px-2 py-1"
            value={hrvToday}
            onChange={(e) => setHrvToday(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1">
          HRV baseline 28d (ms)
          <input
            type="number"
            min={1}
            className="border rounded px-2 py-1"
            value={hrvBaseline}
            onChange={(e) => setHrvBaseline(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1">
          Body Battery (0-100)
          <input
            type="number"
            min={0}
            max={100}
            className="border rounded px-2 py-1"
            value={bodyBattery}
            onChange={(e) => setBodyBattery(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1">
          Sueño (0-100)
          <input
            type="number"
            min={0}
            max={100}
            className="border rounded px-2 py-1"
            value={sleepScore}
            onChange={(e) => setSleepScore(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1">
          Training Readiness
          <select
            className="border rounded px-2 py-1"
            value={trainingReadiness}
            onChange={(e) =>
              setTrainingReadiness(e.target.value as typeof trainingReadiness)
            }
          >
            <option value="high">Alto</option>
            <option value="moderate">Moderado</option>
            <option value="low">Bajo</option>
            <option value="very_low">Muy bajo</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          ACWR
          <input
            type="number"
            step="0.1"
            min={0}
            className="border rounded px-2 py-1"
            value={acwr}
            onChange={(e) => setAcwr(Number(e.target.value))}
          />
        </label>
        <label className="flex items-center gap-2 col-span-2">
          <input
            type="checkbox"
            checked={jointPain}
            onChange={(e) => setJointPain(e.target.checked)}
          />
          Dolor articular hoy
        </label>
        {error && <p className="text-red-600 text-sm col-span-2">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="bg-black text-white rounded px-4 py-2 disabled:opacity-50 col-span-2"
        >
          {submitting ? "Calculando..." : "Registrar check-in"}
        </button>
      </form>
      {resultado && (
        <div
          className={`mt-4 p-3 rounded text-sm font-medium ${READINESS_COLORS[resultado.resultado]}`}
        >
          Readiness de hoy: {resultado.resultado.toUpperCase()}
        </div>
      )}
    </div>
  );
}
