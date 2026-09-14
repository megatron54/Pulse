"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Conexiones } from "@/lib/api";
import { fechaCorta, plural } from "@/lib/fechas";
import { Button } from "./ui/Button";
import { Card, CardTitle } from "./ui/Card";
import { CredentialsForm } from "./ui/CredentialsForm";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

/**
 * Conexiones a servicios externos, en el Perfil (petición explícita del
 * usuario: "conexiones a garmin, feelfit u otros").
 *
 * Solo aparecen las dos integraciones que EXISTEN. No se listan Apple
 * Health, Google Fit ni similares como "próximamente": un ajuste que no
 * hace nada es ruido, y el proyecto ya tenía el problema de exponer
 * planes internos al usuario (la página Coach anunciaba "Fase 6 del
 * plan de reconstrucción").
 *
 * El estado viene de `GET /users/{id}/connections`, no de inferirlo de
 * "¿hay datos?": sin ese endpoint, una cuenta conectada cuyo token
 * caducó y una cuenta nunca conectada se veían exactamente igual.
 */

type Estado = "conectado" | "desconectado";

function IndicadorEstado({ estado }: { estado: Estado }) {
  const conectado = estado === "conectado";
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        aria-hidden="true"
        className={`size-2 rounded-full ${conectado ? "bg-pos" : "bg-line-strong"}`}
      />
      <span className={`t-secondary ${conectado ? "text-pos" : "text-ink-3"}`}>
        {conectado ? "Conectado" : "Sin conectar"}
      </span>
    </span>
  );
}

function Conexion({
  nombre,
  estado,
  detalles,
  acciones,
  formulario,
}: {
  nombre: string;
  estado: Estado;
  /** Líneas de detalle ya formateadas: qué cuenta, desde cuándo, cuántos datos. */
  detalles: string[];
  acciones?: React.ReactNode;
  formulario?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="t-section text-ink">{nombre}</h3>
        <IndicadorEstado estado={estado} />
      </div>
      {detalles.length > 0 && (
        <div className="flex flex-col gap-0.5">
          {detalles.map((linea) => (
            <p key={linea} className="t-secondary text-pretty text-ink-2">
              {linea}
            </p>
          ))}
        </div>
      )}
      {acciones && <div className="flex flex-wrap items-center gap-2">{acciones}</div>}
      {formulario}
    </div>
  );
}

export function ConnectionsCard({ userId }: { userId: number }) {
  const [conexiones, setConexiones] = useState<Conexiones | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);
  const [formAbierto, setFormAbierto] = useState<"garmin" | "feelfit" | null>(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [mensajeSync, setMensajeSync] = useState<string | null>(null);

  const recargar = useCallback(() => setIntentos((n) => n + 1), []);

  useEffect(() => {
    let cancelado = false;
    api
      .getConnections(userId)
      .then((datos) => {
        if (cancelado) return;
        setConexiones(datos);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar el estado de tus conexiones."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  async function sincronizarAhora() {
    setSincronizando(true);
    setMensajeSync(null);
    try {
      const resultado = await api.syncGarminNow(userId);
      setMensajeSync(
        `Sincronizado el ${fechaCorta(resultado.fecha)}: ${plural(
          resultado.puntos_intradia_nuevos,
          "punto nuevo",
          "puntos nuevos"
        )}.`
      );
      recargar();
    } catch (err) {
      setMensajeSync(
        err instanceof ApiError ? err.message : "No se pudo sincronizar con Garmin ahora mismo."
      );
    } finally {
      setSincronizando(false);
    }
  }

  if (error) {
    return (
      <Card>
        <CardTitle>Conexiones</CardTitle>
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            recargar();
          }}
        />
      </Card>
    );
  }

  if (!conexiones) {
    return (
      <Card>
        <CardTitle>Conexiones</CardTitle>
        <LoadingState lines={3} />
      </Card>
    );
  }

  const { garmin, feelfit } = conexiones;

  const detallesGarmin: string[] = [];
  if (garmin.email) detallesGarmin.push(garmin.email);
  if (garmin.historial_desde) {
    detallesGarmin.push(`Histórico desde el ${fechaCorta(garmin.historial_desde)}`);
  }
  if (garmin.dias_de_historial != null) {
    detallesGarmin.push(plural(garmin.dias_de_historial, "día sincronizado", "días sincronizados"));
  }
  if (!garmin.conectado) {
    detallesGarmin.push(
      garmin.email
        ? "La sesión guardada dejó de funcionar. Vuelve a conectar la cuenta para reanudar la sincronización diaria."
        : "Pulse necesita tu cuenta de Garmin para traer sueño, VFC, body battery y actividades."
    );
  }
  if (mensajeSync) detallesGarmin.push(mensajeSync);

  const detallesFeelfit: string[] = [];
  if (feelfit.conectado_desde) {
    detallesFeelfit.push(`Conectada el ${fechaCorta(feelfit.conectado_desde)}`);
  }
  if (feelfit.mediciones_importadas > 0) {
    detallesFeelfit.push(
      plural(feelfit.mediciones_importadas, "medición importada", "mediciones importadas")
    );
  }
  if (!feelfit.conectado) {
    detallesFeelfit.push(
      "Conecta la báscula para traer peso y composición corporal automáticamente, sin pasar por Google Fit ni Apple Health."
    );
  }

  return (
    <Card>
      <CardTitle>Conexiones</CardTitle>
      <div className="divide-y divide-line">
        <Conexion
          nombre="Garmin Connect"
          estado={garmin.conectado ? "conectado" : "desconectado"}
          detalles={detallesGarmin}
          acciones={
            <>
              {garmin.conectado && (
                <Button variant="secondary" onClick={sincronizarAhora} disabled={sincronizando}>
                  {sincronizando ? "Sincronizando..." : "Sincronizar ahora"}
                </Button>
              )}
              <Button
                variant={garmin.conectado ? "secondary" : "primary"}
                onClick={() => setFormAbierto((f) => (f === "garmin" ? null : "garmin"))}
                aria-expanded={formAbierto === "garmin"}
              >
                {garmin.conectado ? "Reconectar" : "Conectar Garmin"}
              </Button>
            </>
          }
          formulario={
            formAbierto === "garmin" && (
              <CredentialsForm
                idPrefijo="perfil-garmin"
                emailInicial={garmin.email ?? ""}
                descripcion="Tu email y contraseña van directos a tu propio servidor de Pulse por HTTPS. La contraseña no se guarda: solo se usa para iniciar sesión esta vez y dejar la sesión de Garmin renovada."
                aviso={
                  garmin.email
                    ? "Usa esta misma cuenta de Garmin. Con otra distinta, Pulse crearía un perfil nuevo y separado en vez de reconectar el tuyo."
                    : undefined
                }
                etiquetaAccion={garmin.conectado ? "Reconectar" : "Conectar"}
                onSubmit={async (credenciales) => {
                  await api.connectGarmin(credenciales);
                  recargar();
                  return "Cuenta de Garmin conectada. La sincronización de hoy ya está en marcha.";
                }}
              />
            )
          }
        />
        <Conexion
          nombre="Báscula Feelfit"
          estado={feelfit.conectado ? "conectado" : "desconectado"}
          detalles={detallesFeelfit}
          acciones={
            <Button
              variant={feelfit.conectado ? "secondary" : "primary"}
              onClick={() => setFormAbierto((f) => (f === "feelfit" ? null : "feelfit"))}
              aria-expanded={formAbierto === "feelfit"}
            >
              {feelfit.conectado ? "Reconectar" : "Conectar Feelfit"}
            </Button>
          }
          formulario={
            formAbierto === "feelfit" && (
              <CredentialsForm
                idPrefijo="perfil-feelfit"
                descripcion="Las credenciales de la app Feelfit viajan a tu propio servidor de Pulse y no se guardan. El token de Feelfit caduca cada pocos días: cuando caduque, la sincronización se detiene y habrá que reconectar aquí."
                etiquetaAccion={feelfit.conectado ? "Reconectar" : "Conectar"}
                onSubmit={async (credenciales) => {
                  const resultado = await api.connectFeelfit(userId, credenciales);
                  recargar();
                  return `Báscula conectada: ${plural(
                    resultado.mediciones_importadas,
                    "medición importada",
                    "mediciones importadas"
                  )}.`;
                }}
              />
            )
          }
        />
      </div>
    </Card>
  );
}
