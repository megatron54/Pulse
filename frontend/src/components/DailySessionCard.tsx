"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  ApiError,
  todayLocalDate,
  type DailySessionResult,
  type SessionTypeValue,
} from "@/lib/api";
import { Button } from "./ui/Button";
import { Card, CardTitle } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { MetricGrid, StatTile } from "./ui/StatTile";

const LABELS: Record<SessionTypeValue, string> = {
  rest: "Descanso",
  active_recovery: "Recuperación activa",
  strength_heavy: "Fuerza pesada",
  strength_hypertrophy: "Hipertrofia",
  endurance_intervals: "Intervalos de resistencia",
  endurance_long: "Resistencia larga",
  martial_arts_technical: "Artes marciales (técnica)",
  martial_arts_sparring: "Artes marciales (sparring)",
};

/** Qué falta, qué significa y qué hacer al respecto - uno por `motivo`
 * del backend (`services.errors.SessionNotDecidableError`). */
type Falta = { motivo: string | null; mensaje: string };

/**
 * "Qué hago hoy" (Design System v3). Segundo y último bloque de "Hoy".
 *
 * Se rehízo entera por tres defectos que la auditoría localizó en la
 * versión v2 de esta misma tarjeta:
 *
 *  1. **Jerarquía invertida.** El `volume_pct` se pintaba a `text-3xl`
 *     en azul de acento y el tipo de sesión a `text-lg`: el número que
 *     dominaba la tarjeta era el ajuste, no la respuesta. Lo que el
 *     usuario viene a leer es "Fuerza pesada"; el 85% es el detalle.
 *  2. **La barra de progreso mentía.** Una barra llena de color de
 *     acento sugiere "completado", cuando `volume_pct` es el volumen
 *     RECOMENDADO respecto al planificado. Ahora es una cifra con su
 *     unidad, como las demás métricas.
 *  3. **El estado vacío no orientaba.** Decía "Aún no hay recovery de
 *     hoy sincronizado de Garmin, o no tienes un plan semanal activo":
 *     una disyunción que el usuario no puede resolver, y que además
 *     contradecía a la tarjeta de recuperación de justo encima cuando
 *     esta SÍ mostraba datos. El backend distingue ahora los dos casos
 *     con un `motivo`, así que cada uno dice qué falta y ofrece la
 *     acción que lo arregla.
 */
export function DailySessionCard({ userId }: { userId: number }) {
  const [resultado, setResultado] = useState<DailySessionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Distinto de `error`: un 400 (sin recovery de hoy / sin plan
  // activo) es un estado VACÍO esperado, no un fallo del sistema - no
  // debe anunciarse como `role="alert"` a lectores de pantalla
  // (hallazgo de code-review, BAJO).
  const [falta, setFalta] = useState<Falta | null>(null);
  const [intentos, setIntentos] = useState(0);

  const reintentar = () => setIntentos((n) => n + 1);

  useEffect(() => {
    let cancelado = false;
    api
      .getDailySession(userId, { target_date: todayLocalDate() })
      .then((r) => {
        if (cancelado) return;
        setError(null);
        setFalta(null);
        setResultado(r);
      })
      .catch((err) => {
        if (cancelado) return;
        if (err instanceof ApiError && err.status === 400) {
          setFalta({ motivo: err.motivo ?? null, mensaje: mensajeDe(err.motivo) });
        } else {
          setError(err instanceof ApiError ? err.message : "No se pudo calcular la sesión de hoy.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  if (error) {
    return (
      <Card>
        <CardTitle>Sesión de hoy</CardTitle>
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            reintentar();
          }}
        />
      </Card>
    );
  }

  if (falta) {
    return (
      <Card>
        <CardTitle>Sesión de hoy</CardTitle>
        <EmptyState message={falta.mensaje} accion={<AccionDe falta={falta} userId={userId} alResolver={reintentar} />} />
      </Card>
    );
  }

  if (resultado === null) {
    return (
      <Card>
        <CardTitle>Sesión de hoy</CardTitle>
        <LoadingState lines={2} />
      </Card>
    );
  }

  const tipo = LABELS[resultado.session_type as SessionTypeValue] ?? resultado.session_type;

  // `plano` + divisor de 1px para la narrativa, mismo patrón que la
  // tarjeta de recuperación: nunca una tarjeta dentro de otra.
  return (
    <Card plano>
      <div className="flex flex-col gap-5 p-5">
        <div>
          <h2 className="t-section mb-2 text-ink-3">Sesión de hoy</h2>
          <p className="t-page-title text-ink">{tipo}</p>
        </div>
        <MetricGrid>
          <StatTile label="Volumen" value={resultado.volume_pct} unit="%" />
          {resultado.intensity_rpe_cap !== null && (
            <StatTile label="RPE máximo" value={resultado.intensity_rpe_cap} />
          )}
        </MetricGrid>
      </div>
      {resultado.narrative_text && (
        <div className="border-t border-line px-5 py-4">
          <p className="t-body text-pretty text-ink-2">{resultado.narrative_text}</p>
        </div>
      )}
    </Card>
  );
}

/** El `detail` del backend está escrito para los logs ("ejecutar
 * sync_and_compute_readiness primero"); esto es lo mismo dicho al
 * usuario, y explicando POR QUÉ hace falta. */
function mensajeDe(motivo: string | undefined): string {
  if (motivo === "sin_recovery") {
    return "Todavía no hay datos de recuperación de hoy. Pulse ajusta la sesión a cómo has dormido y recuperado, así que necesita la sincronización de Garmin antes de decidir nada.";
  }
  if (motivo === "sin_plan") {
    return "No tienes un plan semanal activo. Pulse ajusta el volumen de lo que ya tengas planificado para hoy; sin plan no hay sesión que ajustar.";
  }
  return "Falta algún dato para decidir la sesión de hoy.";
}

function AccionDe({
  falta,
  userId,
  alResolver,
}: {
  falta: Falta;
  userId: number;
  alResolver: () => void;
}) {
  if (falta.motivo === "sin_recovery") {
    return <BotonSincronizar userId={userId} alTerminar={alResolver} />;
  }
  if (falta.motivo === "sin_plan") {
    // Enlace, no botón: el plan semanal se crea en Entrenamiento, donde
    // está el formulario - duplicarlo aquí escondería en la pantalla de
    // hoy una decisión de varias semanas.
    return (
      <Link
        href="/entrenamiento"
        className="t-body rounded-md font-medium text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      >
        Crear mi plan semanal
      </Link>
    );
  }
  return null;
}

/** Sincronización manual del día en curso (`POST /garmin/sync`): pocas
 * llamadas, no el backfill completo. Al terminar se vuelve a pedir la
 * sesión, que es lo que el usuario quería en realidad. */
function BotonSincronizar({ userId, alTerminar }: { userId: number; alTerminar: () => void }) {
  const [estado, setEstado] = useState<"listo" | "sincronizando" | "fallo">("listo");

  async function sincronizar() {
    setEstado("sincronizando");
    try {
      await api.syncGarminNow(userId);
      alTerminar();
    } catch {
      setEstado("fallo");
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button onClick={sincronizar} disabled={estado === "sincronizando"}>
        {estado === "sincronizando" ? "Sincronizando…" : "Sincronizar Garmin ahora"}
      </Button>
      {estado === "fallo" && (
        <p role="alert" className="t-secondary text-neg">
          Garmin no respondió. Vuelve a intentarlo en unos minutos.
        </p>
      )}
    </div>
  );
}
