"use client";

import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { CLAVE_USUARIO } from "@/lib/useCurrentUser";
import { AppearanceCard } from "@/components/AppearanceCard";
import { ConnectionsCard } from "@/components/ConnectionsCard";
import { ProfileCard } from "@/components/ProfileCard";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { FadeIn } from "@/components/ui/FadeIn";
import { PageHeader } from "@/components/ui/PageHeader";

/**
 * Página "Perfil" (Design System v3). Pedida explícitamente por el
 * usuario: "Falta una pagina de Perfil, donde puedas gestionar los
 * ajustes propios, de la app, modo claro oscuro, conexiones a garmin,
 * feelfit u otros".
 *
 * Ocupa el hueco de navegación que dejó "Coach", que gastaba un 20% de
 * la barra principal para decir "Todavía no está construido" citando
 * la fase interna del plan de desarrollo.
 *
 * Tres bloques, en orden de lo que el usuario viene a hacer aquí:
 * sus datos (los que alimentan los cálculos), la apariencia de la app,
 * y las conexiones a los servicios que le dan los datos.
 */
export default function PerfilPage() {
  const usuario = useUser();

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader title="Perfil" subtitle="Tus datos, la app y tus conexiones." />
      <div className="flex flex-col gap-5">
        <FadeIn delay={0}>
          <ProfileCard />
        </FadeIn>
        <FadeIn delay={0.05}>
          <AppearanceCard />
        </FadeIn>
        <FadeIn delay={0.1}>
          <ConnectionsCard userId={usuario.id} />
        </FadeIn>
        <FadeIn delay={0.15}>
          <SesionCard />
        </FadeIn>
      </div>
    </main>
  );
}

/**
 * Cerrar sesión en este dispositivo. Dice exactamente qué hace y qué NO
 * hace (no borra nada del servidor): el mecanismo real es un `user_id`
 * en `localStorage` (mono-usuario, ver `useCurrentUser`), y prometer
 * "borrar mi cuenta" sería mentir sobre lo que ocurre.
 *
 * Con confirmación en dos pasos porque implica volver a pasar por el
 * login de Garmin, y ahí es donde un email distinto crea un perfil
 * duplicado - el problema que ya ocurrió una vez en este proyecto.
 */
function SesionCard() {
  const [confirmando, setConfirmando] = useState(false);

  function cerrarSesion() {
    localStorage.removeItem(CLAVE_USUARIO);
    // Recarga completa, no `router.push`: la sesión vive en el estado de
    // `AppShell` (que solo lee localStorage al montar), así que navegar
    // dentro de la SPA dejaría al usuario "dentro" con la sesión ya
    // borrada. Recargar es lo que de verdad vuelve a la pantalla de
    // conexión.
    window.location.reload();
  }

  return (
    <Card>
      <CardTitle>Sesión</CardTitle>
      <div className="flex flex-col gap-3">
        <p className="t-secondary text-pretty text-ink-2">
          Pulse te recuerda en este dispositivo. Al cerrar sesión tendrás que volver a entrar con tu
          cuenta de Garmin; tus datos siguen en tu servidor, no se borra nada.
        </p>
        {confirmando ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={cerrarSesion}>Sí, cerrar sesión</Button>
            <Button variant="ghost" onClick={() => setConfirmando(false)}>
              Cancelar
            </Button>
          </div>
        ) : (
          <div>
            <Button variant="secondary" onClick={() => setConfirmando(true)}>
              Cerrar sesión
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
