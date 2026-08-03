"use client";

import { useCurrentUser } from "@/lib/useCurrentUser";
import { UserProvider } from "@/lib/UserContext";
import { OnboardingForm } from "@/components/OnboardingForm";
import { Nav } from "@/components/Nav";

/**
 * Envoltorio raíz de la app (rediseño de arquitectura de información):
 * gestiona el estado de "cargando / sin usuario / con usuario" UNA
 * sola vez, en vez de que cada página repita `useCurrentUser`. Una vez
 * hay usuario, expone `UserContext` y monta la navegación - ninguna
 * página bajo este componente necesita preocuparse por el caso "sin
 * usuario todavía".
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, error, createUser } = useCurrentUser();

  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center text-gray-400">
        Cargando...
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex-1 flex flex-col justify-center p-8">
        <h1 className="font-display text-3xl font-bold text-center mb-8 tracking-wide text-white">
          PULSE
        </h1>
        {error && <p className="text-red-400 text-sm text-center mb-4">{error}</p>}
        <OnboardingForm onCreate={createUser} />
      </main>
    );
  }

  return (
    <UserProvider user={user}>
      <div className="flex flex-1 min-h-0">
        <Nav />
        <div className="flex-1 overflow-y-auto pb-[calc(4.5rem+env(safe-area-inset-bottom))] md:pb-0">
          {children}
        </div>
      </div>
    </UserProvider>
  );
}
