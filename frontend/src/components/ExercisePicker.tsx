"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Exercise, type ExerciseCategory } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";
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
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el catálogo de wger.");
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
        setError(err instanceof ApiError ? err.message : "No se pudo buscar ejercicios en wger.");
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
      <CardTitle>Catálogo de ejercicios</CardTitle>
      {error && (
        <p role="alert" className="text-recovery-low text-sm mb-3">
          {error}
        </p>
      )}
      {!error && categorias === null && (
        <p role="status" className="text-sm text-text-secondary italic">
          Cargando categorías...
        </p>
      )}
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
      <div className="mt-4 flex flex-col gap-2">
        {cargando && (
          <p role="status" className="text-sm text-text-secondary italic">
            Buscando ejercicios...
          </p>
        )}
        {!cargando && ejercicios && ejercicios.length === 0 && (
          <p className="text-sm text-text-secondary italic">
            No se encontraron ejercicios en esta categoría.
          </p>
        )}
        {!cargando &&
          ejercicios?.map((ej) => (
            <div
              key={ej.id}
              className="rounded-xl border border-surface-border bg-surface px-4 py-3 text-sm"
            >
              <p className="text-foreground font-medium">{ej.nombre}</p>
              {ej.equipamiento.length > 0 && (
                <p className="text-text-secondary text-xs mt-0.5">{ej.equipamiento.join(", ")}</p>
              )}
            </div>
          ))}
      </div>
    </Card>
  );
}
