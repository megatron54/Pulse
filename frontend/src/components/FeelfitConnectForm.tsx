"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Disclosure } from "./ui/Disclosure";
import { FormField, fieldInputClass } from "./ui/FormField";

/**
 * Conecta la báscula Feelfit de un usuario YA EXISTENTE (a diferencia de
 * `GarminConnectForm`, que da de alta la cuenta desde cero) - petición
 * explícita del usuario: quiere traer las mediciones de la báscula sin
 * pasar por Samsung Health/Apple Health/Fitbit/Health Connect/Google
 * Fit, que es lo único que la app de Feelfit ofrece de forma oficial.
 * El backend (`feelfit_client`) habla directamente con la API en la
 * nube de Feelfit con el mismo contrato que usa la app - nada de eso es
 * necesario.
 *
 * Colapsado por defecto (`Disclosure`): no hay forma de saber desde el
 * frontend si la cuenta ya está conectada (el backend no expone ese
 * estado todavía), así que se muestra siempre pero fuera del camino
 * principal para quien ya conectó la suya.
 */
export function FeelfitConnectForm({ userId }: { userId: number }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [medicionesImportadas, setMedicionesImportadas] = useState<number | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const resultado = await api.connectFeelfit(userId, { email, password });
      setMedicionesImportadas(resultado.mediciones_importadas);
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conectar con Feelfit.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <Disclosure summary="Conectar báscula Feelfit">
        <p className="text-sm text-text-secondary">
          Tu email y contraseña de la app Feelfit van directos a tu propio servidor de Pulse por
          HTTPS - nunca se guardan, solo se usan para traer tu historial de mediciones de peso y
          composición corporal.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FormField label="Email" htmlFor="feelfit-email">
            <input
              id="feelfit-email"
              type="email"
              className={fieldInputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </FormField>
          <FormField label="Contraseña" htmlFor="feelfit-password">
            <input
              id="feelfit-password"
              type="password"
              className={fieldInputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </FormField>
          {error && (
            <p role="alert" className="text-sm text-recovery-low">
              {error}
            </p>
          )}
          {medicionesImportadas !== null && (
            <p className="text-sm text-recovery-high">
              Conectado: se importaron {medicionesImportadas}{" "}
              {medicionesImportadas === 1 ? "medición" : "mediciones"}.
            </p>
          )}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Conectando..." : "Conectar"}
          </Button>
        </form>
      </Disclosure>
    </Card>
  );
}
