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
const UserContext = createContext<User | null>(null);

export function UserProvider({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  return <UserContext.Provider value={user}>{children}</UserContext.Provider>;
}

export function useUser(): User {
  const user = useContext(UserContext);
  if (!user) {
    throw new Error(
      "useUser() se usó fuera de <UserProvider> - AppShell debe envolver toda página que lo use."
    );
  }
  return user;
}
