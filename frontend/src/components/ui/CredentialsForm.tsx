"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api";
import { Button } from "./Button";
import { FormField, fieldInputClass } from "./FormField";

/**
 * Formulario email+contraseña de una integración externa (Garmin,
 * Feelfit). Sin `Card` propia: se monta DENTRO de la sección de
 * Conexiones del Perfil, y v3 prohíbe la tarjeta dentro de otra
 * tarjeta (doctrina 2).
 *
 * Existe para no tener tres copias del mismo formulario: `GarminConnectForm`
 * y el ya borrado `FeelfitConnectForm` repetían el mismo markup con
 * textos ligeramente distintos, y el Perfil habría sido la tercera.
 *
 * `onSubmit` recibe las credenciales y devuelve el mensaje de éxito a
 * mostrar - quien llama decide qué endpoint usar y cómo resumir el
 * resultado ("se importaron 34 mediciones", "cuenta reconectada").
 * La contraseña se borra del estado en cuanto la llamada termina bien:
 * nunca queda en memoria más de lo necesario, y nunca se persiste.
 */
export function CredentialsForm({
  idPrefijo,
  emailInicial = "",
  descripcion,
  aviso,
  etiquetaAccion = "Conectar",
  onSubmit,
}: {
  /** Prefijo de los `id` de los inputs: puede haber dos de estos en la misma página. */
  idPrefijo: string;
  emailInicial?: string;
  descripcion: string;
  /** Advertencia destacada (p.ej. "usa la misma cuenta"), si aplica. */
  aviso?: string;
  etiquetaAccion?: string;
  onSubmit: (credenciales: { email: string; password: string }) => Promise<string>;
}) {
  const [email, setEmail] = useState(emailInicial);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function manejarEnvio(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    setExito(null);
    try {
      const mensaje = await onSubmit({ email, password });
      setPassword("");
      setExito(mensaje);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conectar. Inténtalo otra vez.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={manejarEnvio} className="flex flex-col gap-4">
      <p className="t-secondary text-pretty text-ink-2">{descripcion}</p>
      {aviso && <p className="t-secondary text-pretty text-warn">{aviso}</p>}
      <FormField label="Email" htmlFor={`${idPrefijo}-email`}>
        <input
          id={`${idPrefijo}-email`}
          type="email"
          autoComplete="username"
          className={fieldInputClass}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </FormField>
      <FormField label="Contraseña" htmlFor={`${idPrefijo}-password`}>
        <input
          id={`${idPrefijo}-password`}
          type="password"
          autoComplete="current-password"
          className={fieldInputClass}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </FormField>
      {error && (
        <p role="alert" className="t-secondary text-pretty text-neg">
          {error}
        </p>
      )}
      {exito && (
        <p role="status" className="t-secondary text-pretty text-pos">
          {exito}
        </p>
      )}
      <Button type="submit" disabled={enviando}>
        {enviando ? "Conectando..." : etiquetaAccion}
      </Button>
    </form>
  );
}
