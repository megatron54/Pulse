"use client";

import { createContext, useContext } from "react";
import type { User } from "./api";

/**
 * Contexto del usuario actual, provisto por `AppShell` una vez que
 * `useCurrentUser` confirma que hay sesión (mono-usuario, ver
 * `useCurrentUser.ts`). Evita que cada página tenga que repetir la
 * lógica de "cargando / sin usuario / con usuario" - `AppShell` ya
 * garantiza que ninguna página se monta sin un usuario válido.
 */
type ContextoUsuario = {
  user: User;
  /** Publica el usuario ya actualizado (tras un PATCH en Perfil). */
  onUserChange: (usuario: User) => void;
};

const UserContext = createContext<ContextoUsuario | null>(null);

export function UserProvider({
  user,
  onUserChange,
  children,
}: {
  user: User;
  onUserChange: (usuario: User) => void;
  children: React.ReactNode;
}) {
  return (
    <UserContext.Provider value={{ user, onUserChange }}>{children}</UserContext.Provider>
  );
}

function useContexto(): ContextoUsuario {
  const contexto = useContext(UserContext);
  if (!contexto) {
    throw new Error(
      "useUser() se usó fuera de <UserProvider> - AppShell debe envolver toda página que lo use."
    );
  }
  return contexto;
}

export function useUser(): User {
  return useContexto().user;
}

/**
 * Setter del usuario del contexto, para cuando la propia app cambia el
 * perfil (Perfil > Tus datos). Sin esto, tras guardar un cambio la
 * cabecera seguiría saludando con el nombre viejo hasta recargar la
 * página entera.
 */
export function useSetUser(): (usuario: User) => void {
  return useContexto().onUserChange;
}
