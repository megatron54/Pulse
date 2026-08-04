"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type DailyFoodLog, type Ingredient } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";

/**
 * Diario de comidas real (petición explícita del usuario: "input
 * diario" tipo MyFitnessPal en Nutrición - ver 02-roadmap/
 * 03-vision-produccion.md, épica de food log). El diario vive en el
 * propio wger del usuario (nunca duplicado en la base de datos de
 * Pulse) - por eso el primer paso es conectar el token permanente que
 * el usuario genera él mismo desde la web de wger (Pulse nunca ve su
 * contraseña).
 */
const inputClass =
  "border border-white/10 bg-black/30 rounded-lg px-3 py-2 text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-teal";

function WgerConnectForm({
  userId,
  onConectado,
}: {
  userId: number;
  onConectado: () => void;
}) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.saveWgerToken(userId, token);
      onConectado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el token.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <p className="text-sm text-gray-400">
        Conecta tu cuenta de wger para registrar tus comidas reales. Genera un token
        permanente desde la página &quot;API key&quot; de tu wger (nunca pedimos tu
        contraseña).
      </p>
      <label className="flex flex-col gap-1 text-sm text-gray-300">
        Token de wger
        <input
          type="password"
          className={inputClass}
          value={token}
          onChange={(e) => setToken(e.target.value)}
          required
        />
      </label>
      {error && (
        <p role="alert" className="text-red-400 text-sm">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={guardando}
        className="bg-teal text-black font-semibold rounded-lg px-4 py-2.5 disabled:bg-surface disabled:text-gray-400 disabled:cursor-not-allowed self-start transition-transform hover:scale-[1.02] active:scale-[0.98]"
      >
        {guardando ? "Conectando..." : "Conectar"}
      </button>
    </form>
  );
}

function IngredientSearchAndLog({ userId, onRegistrado }: { userId: number; onRegistrado: () => void }) {
  const [query, setQuery] = useState("");
  const [resultados, setResultados] = useState<Ingredient[] | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    setBuscando(true);
    setError(null);
    try {
      const datos = await api.searchIngredients(userId, query);
      setResultados(datos);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo buscar en wger.");
    } finally {
      setBuscando(false);
    }
  }

  async function registrar(ingredientId: number) {
    try {
      await api.createFoodLogEntry(userId, ingredientId, 100);
      onRegistrado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la comida.");
    }
  }

  return (
    <div className="mt-4">
      <form onSubmit={buscar} className="flex gap-2">
        <input
          type="text"
          placeholder="Buscar alimento..."
          className={`${inputClass} flex-1`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="submit"
          disabled={buscando}
          className="bg-teal text-black font-semibold rounded-lg px-4 py-2 disabled:bg-surface disabled:text-gray-400"
        >
          Buscar
        </button>
      </form>
      {error && (
        <p role="alert" className="text-red-400 text-sm mt-2">
          {error}
        </p>
      )}
      <div className="flex flex-col gap-2 mt-3">
        {resultados?.map((ing) => (
          <div
            key={ing.id}
            className="flex items-center justify-between rounded-lg bg-black/30 px-3 py-2 text-sm"
          >
            <div>
              <p className="text-white">{ing.nombre}</p>
              <p className="text-gray-400 text-xs">{ing.kcal_100g.toFixed(0)} kcal/100g</p>
            </div>
            <button
              onClick={() => registrar(ing.id)}
              className="text-teal text-xs font-semibold uppercase tracking-wide"
            >
              Añadir 100g
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FoodLogCard({ userId }: { userId: number }) {
  const [diario, setDiario] = useState<DailyFoodLog | null>(null);
  const [conectado, setConectado] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getFoodLog(userId)
      .then((datos) => {
        if (cancelado) return;
        setDiario(datos);
        setConectado(true);
      })
      .catch((err) => {
        if (cancelado) return;
        if (err instanceof ApiError && err.status === 404) {
          setConectado(false);
        } else {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el diario.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [userId, refreshKey]);

  return (
    <Card>
      <CardTitle>Diario de comidas</CardTitle>
      {error && (
        <p role="alert" className="text-red-400 text-sm">
          {error}
        </p>
      )}
      {!error && conectado === null && (
        <p role="status" className="text-sm text-gray-400 italic">
          Cargando...
        </p>
      )}
      {!error && conectado === false && (
        <WgerConnectForm userId={userId} onConectado={() => setRefreshKey((k) => k + 1)} />
      )}
      {!error && conectado === true && diario && (
        <>
          <p className="font-display text-3xl font-bold text-white">
            {Math.round(diario.kcal_total)}
            <span className="text-base text-gray-400 font-sans font-normal ml-2">
              kcal hoy
            </span>
          </p>
          {diario.entradas_omitidas > 0 && (
            <p className="text-sm text-recovery-medium mt-2">
              {diario.entradas_omitidas} entradas no se pudieron cargar desde wger.
            </p>
          )}
          <div className="flex flex-col gap-2 mt-3">
            {diario.entradas.map((entrada, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-gray-300">
                  <span>{entrada.nombre}</span> ({entrada.amount_grams.toFixed(0)}g)
                </span>
                <span className="text-gray-400">{entrada.kcal.toFixed(0)} kcal</span>
              </div>
            ))}
          </div>
          <IngredientSearchAndLog
            userId={userId}
            onRegistrado={() => setRefreshKey((k) => k + 1)}
          />
        </>
      )}
    </Card>
  );
}
