"use client";

import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { MetricaDetalle } from "@/components/MetricaDetalle";
import { PageHeader } from "@/components/ui/PageHeader";
import { useUser } from "@/lib/UserContext";
import { metricaPorSlug } from "@/lib/metricasSalud";

/**
 * Detalle de una métrica del reloj: `/salud/sueno`, `/salud/vfc`...
 *
 * Es la profundidad que faltaba en "Hoy", donde cada cifra era un
 * callejón sin salida. Vive bajo `/salud` (que hasta ahora solo
 * redirigía a Entrenamiento) porque son datos de salud y no de
 * entrenamiento, y porque la ruta se lee entera: la barra de
 * direcciones también es interfaz (doctrina 8).
 *
 * Cliente y no servidor porque el usuario actual lo publica `AppShell`
 * en un contexto de React: el `id` no viaja en la URL (la app es
 * mono-usuario, ver `useCurrentUser.ts`).
 */
export default function MetricaPage() {
  const user = useUser();
  const parametro = useParams().metrica;
  const slug = Array.isArray(parametro) ? parametro[0] : parametro;
  const metrica = slug ? metricaPorSlug(slug) : undefined;

  if (!metrica) notFound();

  return (
    <main className="content-container py-6 md:py-8">
      <PageHeader title={metrica.titulo} />
      {/* Volver explícito y no solo el botón del navegador: a esta
          pantalla se llega desde dos sitios (la cifra de "Hoy" y el
          histórico de Entrenamiento) y en móvil no hay barra con
          flecha a la vista. */}
      <p className="t-secondary mb-5">
        <Link href="/" className="text-ink-2 underline underline-offset-4 hover:text-ink">
          Volver a Hoy
        </Link>
      </p>
      <MetricaDetalle userId={user.id} metrica={metrica} />
    </main>
  );
}
