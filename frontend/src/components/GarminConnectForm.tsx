"use client";

import { useState } from "react";
import { api, ApiError, type GarminConnectInput, type User } from "@/lib/api";
import { Button } from "./ui/Button";
import { Card, CardTitle } from "./ui/Card";
import { FormField, fieldInputClass } from "./ui/FormField";

const ETIQUETA_CAMPO: Record<string, string> = {
  nombre: "Nombre",
  altura_cm: "Altura (cm)",
  fecha_nacimiento: "Fecha de nacimiento",
  sexo: "Sexo",
};

/**
 * Reemplaza por completo al formulario manual de perfil
 * (`OnboardingForm`, eliminado) - petición explícita del usuario: "sin
 * cuenta local, que al hacer la conexión a Garmin, todos esos datos se
 * saquen de ahí". Solo pide email + contraseña de tu cuenta Garmin
 * Connect; el backend (`connect_new_user_via_garmin`) extrae nombre,
 * altura, fecha de nacimiento y sexo directamente de tu perfil de
 * Garmin.
 *
 * Flujo de "pedir solo lo que falte" (decisión explícita del usuario,
 * nunca el formulario completo si Garmin ya dio un dato): si el
 * backend responde 422 con `campos_faltantes`, se muestra un segundo
 * paso MÍNIMO solo con esos campos - se reintenta la misma llamada de
 * conexión reutilizando el email/contraseña ya introducidos en el
 * estado de este componente (el usuario NO vuelve a teclearlos),
 * añadiendo los valores del segundo paso como `overrides`.
 *
 * La contraseña vive solo en el estado de este componente durante la
 * sesión de conexión - nunca se persiste en localStorage ni se envía a
 * ningún sitio salvo esta petición HTTPS al propio backend.
 */
export function GarminConnectForm({
  onConnected,
}: {
  onConnected: (usuario: User) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [camposFaltantes, setCamposFaltantes] = useState<string[] | null>(null);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function conectar(overridesActuales: Record<string, string> = {}) {
    setSubmitting(true);
    setError(null);
    try {
      // altura_cm viaja como string en el estado del formulario (value
      // de un <input type="number">) - el backend espera un float.
      // Number("") -> NaN si el campo quedara vacío pese al `required`
      // del input (ej. borrado tras autocompletar) - nunca se envía
      // NaN (el backend lo rechazaría como si faltara, generando un
      // 422 en bucle sin explicación clara).
      const overridesTipados: Record<string, string | number> = { ...overridesActuales };
      if ("altura_cm" in overridesTipados) {
        const altura = Number(overridesTipados.altura_cm);
        if (Number.isNaN(altura)) {
          setError("La altura debe ser un número.");
          setSubmitting(false);
          return;
        }
        overridesTipados.altura_cm = altura;
      }
      const payload = { email, password, ...overridesTipados } as GarminConnectInput;
      const usuario = await api.connectGarmin(payload);
      onConnected(usuario);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        const detalle = err.detail as { campos_faltantes?: string[] } | undefined;
        setCamposFaltantes(detalle?.campos_faltantes ?? []);
      } else {
        // 401 (credenciales inválidas) o 429 (rate-limit de Garmin)
        // pueden ocurrir también en el segundo submit (completar
        // campos) - hallazgo de code-review: sin este `else` volvía a
        // mostrarse el formulario de "completar campos" con un error
        // de sesión, sin forma de volver al paso 1. Se vuelve siempre
        // al paso 1 para que el usuario pueda reintentar desde cero.
        setCamposFaltantes(null);
        setError(err instanceof ApiError ? err.message : "No se pudo conectar con Garmin.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitInicial(e: React.FormEvent) {
    e.preventDefault();
    await conectar();
  }

  async function handleSubmitCompletar(e: React.FormEvent) {
    e.preventDefault();
    await conectar(overrides);
  }

  if (camposFaltantes) {
    return (
      <div className="mx-auto w-full max-w-sm">
        <Card>
          <CardTitle>Falta un dato</CardTitle>
          <p className="-mt-2 mb-4 text-sm text-text-secondary">
            Garmin no nos dio {camposFaltantes.length === 1 ? "este dato" : "estos datos"} - solo te
            pedimos lo que falta.
          </p>
          <form onSubmit={handleSubmitCompletar} className="flex flex-col gap-4">
            {camposFaltantes.map((campo) => (
              <FormField key={campo} label={ETIQUETA_CAMPO[campo] ?? campo} htmlFor={campo}>
                {campo === "sexo" ? (
                  <select
                    id={campo}
                    className={fieldInputClass}
                    value={overrides[campo] ?? ""}
                    onChange={(e) => setOverrides((o) => ({ ...o, [campo]: e.target.value }))}
                  >
                    <option value="" disabled>
                      Elige...
                    </option>
                    <option value="M">Masculino</option>
                    <option value="F">Femenino</option>
                  </select>
                ) : (
                  <input
                    id={campo}
                    type={campo === "fecha_nacimiento" ? "date" : campo === "altura_cm" ? "number" : "text"}
                    className={fieldInputClass}
                    value={overrides[campo] ?? ""}
                    onChange={(e) => setOverrides((o) => ({ ...o, [campo]: e.target.value }))}
                    required
                  />
                )}
              </FormField>
            ))}
            {error && (
              <p role="alert" className="text-sm text-recovery-low">
                {error}
              </p>
            )}
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Completando..." : "Completar"}
            </Button>
          </form>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-sm">
      <Card>
        <CardTitle>Conecta tu cuenta de Garmin</CardTitle>
        <p className="-mt-2 mb-4 text-sm text-text-secondary">
          Tu email y contraseña van directos a tu propio servidor de Pulse por HTTPS - nunca se
          guardan, solo se usan para iniciar sesión en Garmin Connect esta vez.
        </p>
        <form onSubmit={handleSubmitInicial} className="flex flex-col gap-4">
          <FormField label="Email" htmlFor="garmin-email">
            <input
              id="garmin-email"
              type="email"
              className={fieldInputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </FormField>
          <FormField label="Contraseña" htmlFor="garmin-password">
            <input
              id="garmin-password"
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
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Conectando..." : "Conectar"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
