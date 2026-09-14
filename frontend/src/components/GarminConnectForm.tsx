"use client";

import { useState } from "react";
import { api, ApiError, type GarminConnectInput, type User } from "@/lib/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
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
 *
 * v3 (01-arquitectura/05-design-system-v3.md): es la PRIMERA pantalla
 * de la app, y venía con tres defectos de la auditoría. El texto de la
 * promesa de privacidad estaba pegado al título con un `-mt-2` a mano
 * en vez de la escala tipográfica, los errores se pintaban con el
 * token de "recuperación baja" (un color de dato usado como color de
 * interfaz, doctrina 1), y los inputs no declaraban `autoComplete`,
 * así que el gestor de contraseñas del navegador no ofrecía rellenar
 * la cuenta de Garmin. Además, el paso de "falta un dato" no decía
 * cuál era el primer paso ni que la conexión seguía en marcha: ahora
 * se numeran los dos pasos.
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

  const mensajeError = error && (
    <p role="alert" className="t-body text-pretty text-neg">
      {error}
    </p>
  );

  if (camposFaltantes) {
    const faltaUno = camposFaltantes.length === 1;
    return (
      <div className="mx-auto w-full max-w-sm">
        <Card>
          <p className="t-micro text-ink-3">Paso 2 de 2</p>
          <h2 className="t-section mt-1 text-ink">
            {faltaUno ? "Falta un dato" : "Faltan unos datos"}
          </h2>
          <p className="t-secondary mt-1 text-pretty text-ink-2">
            Hemos entrado en tu cuenta de Garmin, pero tu perfil de ahí no incluye{" "}
            {faltaUno ? "este dato" : "estos datos"}. Solo te pedimos lo que falta.
          </p>
          <form onSubmit={handleSubmitCompletar} className="mt-5 flex flex-col gap-4">
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
                      Elige una opción…
                    </option>
                    <option value="M">Masculino</option>
                    <option value="F">Femenino</option>
                  </select>
                ) : (
                  <input
                    id={campo}
                    type={
                      campo === "fecha_nacimiento"
                        ? "date"
                        : campo === "altura_cm"
                          ? "number"
                          : "text"
                    }
                    inputMode={campo === "altura_cm" ? "numeric" : undefined}
                    className={fieldInputClass}
                    value={overrides[campo] ?? ""}
                    onChange={(e) => setOverrides((o) => ({ ...o, [campo]: e.target.value }))}
                    required
                  />
                )}
              </FormField>
            ))}
            {mensajeError}
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Completando…" : "Completar"}
            </Button>
          </form>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-sm">
      <Card>
        <p className="t-micro text-ink-3">Paso 1 de 2</p>
        <h2 className="t-section mt-1 text-ink">Conecta tu cuenta de Garmin</h2>
        <p className="t-secondary mt-1 text-pretty text-ink-2">
          Pulse saca de ahí tu perfil y tu historial: no hay que rellenar nada a mano.
        </p>
        <form onSubmit={handleSubmitInicial} className="mt-5 flex flex-col gap-4">
          <FormField label="Email" htmlFor="garmin-email">
            <input
              id="garmin-email"
              type="email"
              autoComplete="username"
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
              autoComplete="current-password"
              className={fieldInputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </FormField>
          {mensajeError}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Conectando…" : "Conectar"}
          </Button>
        </form>
        {/* La promesa de privacidad va al final y en pequeño: es
            importante, pero leerla no es el primer paso. */}
        <p className="t-secondary mt-4 text-pretty text-ink-3">
          Tu email y tu contraseña viajan por HTTPS a tu propio servidor de Pulse y se usan solo
          para iniciar sesión en Garmin Connect esta vez. La contraseña no se guarda en ningún
          sitio.
        </p>
      </Card>
    </div>
  );
}
