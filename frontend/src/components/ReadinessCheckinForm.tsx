"use client";

import { useState } from "react";
import { api, ApiError, todayLocalDate, type ReadinessResult } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { RecoveryRing } from "./RecoveryRing";

const ZONA_POR_RESULTADO: Record<string, "green" | "yellow" | "red"> = {
  green: "green",
  yellow: "yellow",
  red: "red",
};

// Etiqueta categórica mostrada DENTRO del anillo - el motor de reglas
// de Pulse (Capa 1) es categórico (verde/amarillo/rojo), nunca emite un
// score continuo 0-100 como el de WHOOP. Mostrar un número fabricado
// en un anillo idéntico al de WHOOP induciría a pensar que es una
// medición real (hallazgo CRÍTICO de code-review) - por eso
// `RecoveryRing` se usa aquí en su modo categórico (`categoryLabel`),
// que muestra esta palabra en vez de un "%".
const ETIQUETA_ZONA: Record<string, string> = {
  green: "óptimo",
  yellow: "precaución",
  red: "alerta",
};

const inputClass =
  "border border-white/10 bg-black/30 rounded-lg px-3 py-2 text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-teal";

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
    "high" | "moderate" | "low" | "very_low" | ""
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
        training_readiness: trainingReadiness === "" ? null : trainingReadiness,
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
    <Card>
      <CardTitle>Check-in de recuperación</CardTitle>
      <p className="text-sm text-gray-400 mb-4 -mt-2">
        Manual mientras la sincronización con Garmin real siga pendiente (Fase H).
      </p>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          HRV hoy (ms)
          <input
            type="number"
            min={1}
            className={inputClass}
            value={hrvToday}
            onChange={(e) => setHrvToday(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          HRV baseline 28d (ms)
          <input
            type="number"
            min={1}
            className={inputClass}
            value={hrvBaseline}
            onChange={(e) => setHrvBaseline(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Body Battery (0-100)
          <input
            type="number"
            min={0}
            max={100}
            className={inputClass}
            value={bodyBattery}
            onChange={(e) => setBodyBattery(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Sueño (0-100)
          <input
            type="number"
            min={0}
            max={100}
            className={inputClass}
            value={sleepScore}
            onChange={(e) => setSleepScore(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Training Readiness
          <select
            className={inputClass}
            value={trainingReadiness}
            onChange={(e) =>
              setTrainingReadiness(e.target.value as typeof trainingReadiness)
            }
          >
            <option value="high">Alto</option>
            <option value="moderate">Moderado</option>
            <option value="low">Bajo</option>
            <option value="very_low">Muy bajo</option>
            <option value="">Mi reloj no lo calcula</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          ACWR
          <input
            type="number"
            step="0.1"
            min={0}
            className={inputClass}
            value={acwr}
            onChange={(e) => setAcwr(Number(e.target.value))}
          />
        </label>
        <label className="flex items-center gap-2 col-span-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={jointPain}
            onChange={(e) => setJointPain(e.target.checked)}
            className="h-4 w-4 accent-teal"
          />
          Dolor articular hoy
        </label>
        {error && <p className="text-red-400 text-sm col-span-2">{error}</p>}
        <Button type="submit" disabled={submitting} className="col-span-2">
          {submitting ? "Calculando..." : "Registrar check-in"}
        </Button>
      </form>
      {resultado && (
        <div className="mt-6 flex items-center justify-center">
          <RecoveryRing
            zone={ZONA_POR_RESULTADO[resultado.resultado]}
            categoryLabel={ETIQUETA_ZONA[resultado.resultado]}
            label="Recovery"
          />
        </div>
      )}
    </Card>
  );
}
