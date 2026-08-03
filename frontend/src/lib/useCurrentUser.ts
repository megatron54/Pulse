"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type User, type UserCreateInput } from "./api";

const STORAGE_KEY = "pulse_user_id";

/**
 * Mono-usuario v1 (ver docs/02-roadmap/02-plan-autonomo.md, Fase D):
 * el id del único usuario se guarda en localStorage tras crearlo. No
 * hay login real todavía - coherente con la auth v1 (API key, no
 * sesiones de usuario) del backend.
 */
export function useCurrentUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const storedId = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (!storedId) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const usuario = await api.getUser(Number(storedId));
      setUser(usuario);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Patrón estándar de "cargar datos al montar" (sincronizar con el
    // sistema externo localStorage+API): `load` es async y solo llama a
    // setState dentro de su propio cuerpo tras el await, no de forma
    // síncrona en el efecto. La regla react-hooks/set-state-in-effect
    // marca esto como falso positivo para este caso legítimo.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const createUser = useCallback(async (data: UserCreateInput) => {
    setError(null);
    try {
      const usuario = await api.createUser(data);
      localStorage.setItem(STORAGE_KEY, String(usuario.id));
      setUser(usuario);
      return usuario;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    }
  }, []);

  return { user, loading, error, createUser };
}
