"use client";

import { useState } from "react";
import { api, ApiError, HABITOS, type Habito, type HabitCorrelation } from "@/lib/api";
import { plural } from "@/lib/fechas";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { DataList, DataRow } from "./ui/DataList";
import { FormField, fieldInputClass } from "./ui/FormField";

const ETIQUETAS: Record<Habito, string> = {
  alcohol: "Alcohol",
  cafeina_tarde: "Cafeína por la tarde",
  comida_tardia: "Comida tardía",
  estres_alto: "Estrés alto",
  siesta: "Siesta",
  ayuno_intermitente: "Ayuno intermitente",
  doble_sesion: "Doble sesión de entreno",
  viaje: "Viaje",
};

/** Mínimo de días en cada grupo que exige el backend para dar una
 *  correlación (ver `services/habit_correlation_service.py`). */
const MUESTRA_MINIMA = 5;

/**
 * Diario de hábitos y su correlación con la recuperación (Entrenamiento
 * › Recuperación).
 *
 * v3 arregla dos cosas de fondo además del estilo:
 *
 *  - **"Días RED"** era el nombre interno de la zona de recuperación en
 *    la interfaz, en inglés y en mayúsculas. El usuario ve "días con
 *    recuperación baja", que es lo mismo dicho en su idioma.
 *  - **Los dos porcentajes no se comparaban.** Estaban en dos líneas
 *    sueltas, uno de ellos en rojo "porque es el malo", y el usuario
 *    tenía que restar mentalmente. Ahora la tarjeta dice la conclusión:
 *    cuánto más (o menos) frecuente es un día malo tras ese hábito.
 *
 * Se mantiene intacta la regla honesta del backend: sin muestra
 * suficiente no se da ningún porcentaje, y se dice cuántos días faltan.
 */
export function HabitJournalCard({ userId }: { userId: number }) {
  return (
    <Card plano>
      <div className="p-5">
        <h2 className="t-section text-ink">Diario de hábitos</h2>
        <p className="t-secondary mt-1 max-w-prose text-pretty text-ink-3">
          Lo que marcas aquí se cruza con tu recuperación del día siguiente. Con suficientes días,
          Pulse puede decirte qué te pasa factura.
        </p>
        <div className="mt-4">
          <HabitosDeHoy userId={userId} />
        </div>
      </div>
      <CorrelacionSeccion userId={userId} />
    </Card>
  );
}

function HabitosDeHoy({ userId }: { userId: number }) {
  const [seleccionados, setSeleccionados] = useState<Set<Habito>>(new Set());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardado, setGuardado] = useState(false);

  function alternar(habito: Habito) {
    setSeleccionados((previo) => {
      const siguiente = new Set(previo);
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
      <h3 className="t-micro mb-2 text-ink-3">¿Ha pasado hoy alguna de estas cosas?</h3>
      <div className="flex flex-wrap gap-2">
        {HABITOS.map((habito) => {
          const activo = seleccionados.has(habito);
          return (
            <button
              key={habito}
              type="button"
              aria-pressed={activo}
              onClick={() => alternar(habito)}
              // Mismo lenguaje que ChipFilter: el estado marcado se ve
              // por relleno Y por borde, no solo por color de fondo.
              className={`t-body min-h-11 whitespace-nowrap rounded-md border px-3.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ink ${
                activo
                  ? "border-action bg-action font-medium text-action-ink"
                  : "border-line bg-surface text-ink-2 hover:text-ink"
              }`}
            >
              {ETIQUETAS[habito]}
            </button>
          );
        })}
      </div>
      {error && (
        <p role="alert" className="t-body mt-3 text-neg">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <Button onClick={guardar} disabled={guardando}>
          {guardando ? "Guardando…" : "Guardar el día"}
        </Button>
        {guardado && !guardando && (
          <p role="status" className="t-body text-pos">
            Guardado.
          </p>
        )}
      </div>
    </div>
  );
}

function CorrelacionSeccion({ userId }: { userId: number }) {
  const [habitoElegido, setHabitoElegido] = useState<Habito | "">("");
  const [correlacion, setCorrelacion] = useState<HabitCorrelation | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function elegir(habito: string) {
    setHabitoElegido(habito as Habito);
    setCorrelacion(null);
    setError(null);
    if (!habito) return;
    try {
      setCorrelacion(await api.getHabitCorrelation(userId, habito as Habito));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo calcular la correlación.");
    }
  }

  const etiqueta = habitoElegido ? ETIQUETAS[habitoElegido].toLowerCase() : "";

  return (
    <section className="border-t border-line px-5 py-4">
      <h3 className="t-section mb-3 text-ink">Qué te pasa factura</h3>
      <FormField label="Ver correlación con tu recuperación" htmlFor="habito-correlacion">
        <select
          id="habito-correlacion"
          value={habitoElegido}
          onChange={(e) => elegir(e.target.value)}
          className={fieldInputClass}
        >
          <option value="">Elige un hábito…</option>
          {HABITOS.map((habito) => (
            <option key={habito} value={habito}>
              {ETIQUETAS[habito]}
            </option>
          ))}
        </select>
      </FormField>

      {error && (
        <p role="alert" className="t-body mt-3 text-neg">
          {error}
        </p>
      )}

      {correlacion && !correlacion.datos_suficientes && (
        <p className="t-body mt-4 max-w-prose text-pretty text-ink-2">
          Todavía no hay días suficientes para decir nada honesto sobre{" "}
          {etiqueta}: hacen falta {MUESTRA_MINIMA} días con y {MUESTRA_MINIMA} sin, y por ahora hay{" "}
          {plural(correlacion.dias_con_habito_con_dato, "día", "días")} con y{" "}
          {plural(correlacion.dias_sin_habito_con_dato, "día", "días")} sin.
        </p>
      )}

      {correlacion?.datos_suficientes && (
        <Veredicto correlacion={correlacion} etiqueta={etiqueta} />
      )}
    </section>
  );
}

function Veredicto({
  correlacion,
  etiqueta,
}: {
  correlacion: HabitCorrelation;
  etiqueta: string;
}) {
  const con = Math.round((correlacion.pct_red_con_habito ?? 0) * 100);
  const sin = Math.round((correlacion.pct_red_sin_habito ?? 0) * 100);
  const diferencia = con - sin;

  return (
    <div className="mt-4">
      {/* La conclusión primero y en palabras: el color solo refuerza lo
          que la frase ya dice (WCAG 1.4.1). */}
      <p
        className={`t-body max-w-prose text-pretty ${
          diferencia >= 15 ? "text-warn" : diferencia <= -15 ? "text-pos" : "text-ink-2"
        }`}
      >
        {diferencia >= 15 &&
          `Tras un día con ${etiqueta} amaneces con la recuperación baja ${diferencia} puntos más a menudo.`}
        {diferencia <= -15 &&
          `Tras un día con ${etiqueta} amaneces con la recuperación baja ${Math.abs(diferencia)} puntos menos a menudo.`}
        {diferencia > -15 &&
          diferencia < 15 &&
          `Con ${etiqueta} o sin ello, tu recuperación del día siguiente se comporta parecido.`}
      </p>
      <div className="mt-3">
        <DataList>
          <DataRow
            label="Días con recuperación baja tras marcarlo"
            nota={`${plural(correlacion.dias_con_habito_con_dato, "día medido", "días medidos")}`}
          >
            <span className="tabular">{con} %</span>
          </DataRow>
          <DataRow
            label="Días con recuperación baja sin marcarlo"
            nota={`${plural(correlacion.dias_sin_habito_con_dato, "día medido", "días medidos")}`}
          >
            <span className="tabular">{sin} %</span>
          </DataRow>
        </DataList>
      </div>
      <p className="t-secondary mt-3 max-w-prose text-pretty text-ink-3">
        Es una correlación con tu propia muestra, no una causa demostrada.
      </p>
    </div>
  );
}
