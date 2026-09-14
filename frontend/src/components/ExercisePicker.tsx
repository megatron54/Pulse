"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Exercise, type ExerciseCategory } from "@/lib/api";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { FormField, fieldInputClass } from "./ui/FormField";

/**
 * Selector/explorador del catálogo de ejercicios de wger (Fase E del
 * plan autónomo, cliente construido hace tiempo en
 * `backend/wger_client/` pero nunca conectado a ninguna pantalla hasta
 * ahora - ver 02-roadmap/03-vision-produccion.md).
 *
 * Alcance de esta primera versión: navegar el catálogo por categoría
 * (solo lectura). Todavía NO permite añadir un ejercicio a una sesión
 * concreta - eso requiere primero decidir el modelo de datos de
 * "sesión con ejercicios" en Pulse (hoy `session_service` solo decide
 * un `SessionType` + volumen, no una lista de ejercicios), que queda
 * como trabajo futuro explícito.
 */
export function ExercisePicker() {
  const [categorias, setCategorias] = useState<ExerciseCategory[] | null>(null);
  const [categoriaId, setCategoriaId] = useState<number | null>(null);
  const [ejercicios, setEjercicios] = useState<Exercise[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    let cancelado = false;
    api
      .getExerciseCategories()
      .then((datos) => {
        if (cancelado) return;
        setCategorias(datos);
        if (datos.length > 0) setCategoriaId(datos[0].id);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar el catálogo de ejercicios.",
        );
      });
    return () => {
      cancelado = true;
    };
  }, []);

  useEffect(() => {
    if (categoriaId === null) return;
    const id = categoriaId;
    let cancelado = false;

    async function buscar() {
      // Patrón ya establecido en useCurrentUser.ts: el reseteo de
      // estado de carga vive dentro de una función async invocada
      // desde el efecto, no directamente en su cuerpo síncrono - la
      // regla react-hooks/set-state-in-effect es un falso positivo
      // para este caso legítimo (mostrar "cargando" antes de que
      // resuelva la petición).
      setCargando(true);
      setEjercicios(null);
      try {
        const datos = await api.searchExercises(id, 2, 50);
        if (!cancelado) setEjercicios(datos);
      } catch (err) {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo buscar ejercicios en el catálogo.",
        );
      } finally {
        if (!cancelado) setCargando(false);
      }
    }

    buscar();
    return () => {
      cancelado = true;
    };
  }, [categoriaId]);

  return (
    <Card>
      <div className="mb-4">
        <h2 className="t-section text-ink">Catálogo de ejercicios</h2>
        <p className="t-secondary mt-1 max-w-prose text-pretty text-ink-3">
          Para consultar qué ejercicios hay por grupo muscular y con qué material. De momento es
          solo consulta: todavía no se pueden añadir a una sesión.
        </p>
      </div>
      {error && (
        <p role="alert" className="t-body mb-3 text-neg">
          {error}
        </p>
      )}
      {!error && categorias === null && <LoadingState lines={2} />}
      {!error && categorias && (
        <FormField label="Categoría de ejercicios" htmlFor="categoria-ejercicios">
          <select
            id="categoria-ejercicios"
            className={fieldInputClass}
            value={categoriaId ?? ""}
            onChange={(e) => setCategoriaId(Number(e.target.value))}
          >
            {categorias.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </FormField>
      )}
      <div className="mt-4">
        {cargando && <LoadingState lines={3} />}
        {!cargando && ejercicios && ejercicios.length === 0 && (
          <EmptyState message="No hay ejercicios en esta categoría." />
        )}
        {/* Una lista con filetes de 1px, no una tarjeta por ejercicio:
            con 50 resultados eran 50 contenedores con borde. */}
        {!cargando && ejercicios && ejercicios.length > 0 && (
          <ul className="divide-y divide-line">
            {ejercicios.map((ej) => (
              <li
                key={ej.id}
                className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-3 first:pt-0 last:pb-0"
              >
                <span className="t-body text-ink">{ej.nombre}</span>
                {ej.equipamiento.length > 0 && (
                  <span className="t-secondary text-ink-3">{ej.equipamiento.join(", ")}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
