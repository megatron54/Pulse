"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { api, ApiError, HABITOS, type Habito, type HabitCorrelation } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";

/**
 * Diario de hábitos correlacionado con recovery (Épica MUST-HAVE #3 de
 * 02-roadmap/03-vision-produccion.md, análogo al "Journal" de WHOOP).
 * Dos partes independientes en la misma tarjeta: (1) marcar los
 * hábitos de hoy, (2) consultar si un hábito concreto se correlaciona
 * con más días RED al día siguiente - solo si hay muestra suficiente
 * (ver services/habit_correlation_service.py en el backend).
 */
const _ETIQUETAS: Record<Habito, string> = {
  alcohol: "Alcohol",
  cafeina_tarde: "Cafeína por la tarde",
  comida_tardia: "Comida tardía",
  estres_alto: "Estrés alto",
  siesta: "Siesta",
  ayuno_intermitente: "Ayuno intermitente",
  doble_sesion: "Doble sesión de entreno",
  viaje: "Viaje",
};

function HabitCheckboxes({ userId }: { userId: number }) {
  const [seleccionados, setSeleccionados] = useState<Set<Habito>>(new Set());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardado, setGuardado] = useState(false);

  function toggle(habito: Habito) {
    setSeleccionados((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(habito)) {
        siguiente.delete(habito);
      } else {
        siguiente.add(habito);
      }
      return siguiente;
    });
    setGuardado(false);
  }

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      await api.setHabits(userId, Array.from(seleccionados));
      setGuardado(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron guardar los hábitos.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <p className="text-sm text-text-secondary mb-3">¿Ocurrió hoy alguno de estos?</p>
      <div className="grid grid-cols-2 gap-2">
        {HABITOS.map((habito) => (
          <label
            key={habito}
            className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer"
          >
            <input
              type="checkbox"
              checked={seleccionados.has(habito)}
              onChange={() => toggle(habito)}
              className="accent-teal"
            />
            {_ETIQUETAS[habito]}
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-recovery-low text-sm mt-2">
          {error}
        </p>
      )}
      <Button onClick={guardar} disabled={guardando} className="mt-4">
        {guardando ? (
          "Guardando..."
        ) : guardado ? (
          <>
            Guardado <Check aria-hidden="true" size={14} />
          </>
        ) : (
          "Guardar"
        )}
      </Button>
    </div>
  );
}

function HabitCorrelationView({ userId }: { userId: number }) {
  const [habitoElegido, setHabitoElegido] = useState<Habito | "">("");
  const [correlacion, setCorrelacion] = useState<HabitCorrelation | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSelect(habito: string) {
    setHabitoElegido(habito as Habito);
    setCorrelacion(null);
    setError(null);
    if (!habito) return;
    try {
      const resultado = await api.getHabitCorrelation(userId, habito as Habito);
      setCorrelacion(resultado);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo calcular la correlación.");
    }
  }

  return (
    <div className="mt-6 pt-6 border-t border-surface-border">
      <label className="flex flex-col gap-1 text-sm text-text-secondary">
        Ver correlación con recovery
        <select
          value={habitoElegido}
          onChange={(e) => onSelect(e.target.value)}
          className="border border-surface-border bg-surface-muted rounded-lg px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option value="">Elige un hábito...</option>
          {HABITOS.map((habito) => (
            <option key={habito} value={habito}>
              {_ETIQUETAS[habito]}
            </option>
          ))}
        </select>
      </label>
      {error && (
        <p role="alert" className="text-recovery-low text-sm mt-2">
          {error}
        </p>
      )}
      {correlacion && !correlacion.datos_suficientes && (
        <p className="text-sm text-text-secondary mt-3 italic">
          Todavía no hay suficientes datos para este hábito ({correlacion.dias_con_habito_con_dato}{" "}
          días con, {correlacion.dias_sin_habito_con_dato} sin). Necesitamos al menos 5 de cada.
        </p>
      )}
      {correlacion?.datos_suficientes && (
        <div className="mt-3 flex flex-col gap-1 text-sm">
          <p className="text-text-secondary">
            Días RED tras marcarlo:{" "}
            <span className="text-recovery-low font-semibold">
              {Math.round((correlacion.pct_red_con_habito ?? 0) * 100)}%
            </span>{" "}
            ({correlacion.dias_con_habito_con_dato} muestras)
          </p>
          <p className="text-text-secondary">
            Días RED sin marcarlo:{" "}
            <span className="text-text-secondary font-semibold">
              {Math.round((correlacion.pct_red_sin_habito ?? 0) * 100)}%
            </span>{" "}
            ({correlacion.dias_sin_habito_con_dato} muestras)
          </p>
        </div>
      )}
    </div>
  );
}

export function HabitJournalCard({ userId }: { userId: number }) {
  return (
    <Card>
      <CardTitle>Diario de hábitos</CardTitle>
      <HabitCheckboxes userId={userId} />
      <HabitCorrelationView userId={userId} />
    </Card>
  );
}
