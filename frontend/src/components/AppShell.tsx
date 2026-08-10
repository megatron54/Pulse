"use client";

import { useCurrentUser } from "@/lib/useCurrentUser";
import { UserProvider } from "@/lib/UserContext";
import { OnboardingForm } from "@/components/OnboardingForm";
import { Nav } from "@/components/Nav";
import { Skeleton } from "@/components/ui/Skeleton";

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
    // Hallazgo H1 de la auditoría UI/UX: esta es la PRIMERA pantalla
    // que ve cualquier usuario en cada carga de la app (mono-usuario
    // vía localStorage) - antes era un texto plano "Cargando...", sin
    // ningún indicador visual de progreso. Reutiliza `Skeleton` (mismo
    // shimmer que `LoadingState`, en vez de `animate-pulse` de
    // Tailwind - hallazgo MEDIUM de code-review: la versión anterior
    // no respetaba `prefers-reduced-motion`, `Skeleton` sí).
    return (
      <main className="flex-1 flex flex-col items-center justify-center gap-6 p-8">
        <div className="w-full max-w-2xl flex flex-col gap-4" role="status" aria-label="Cargando">
          <Skeleton className="h-8 w-32 mx-auto" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-24 w-full rounded-2xl" />
          <span className="sr-only">Cargando Pulse...</span>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex-1 flex flex-col justify-center p-8">
        <h1 className="text-3xl font-semibold text-center mb-8 tracking-tight text-white">
          Pulse
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
