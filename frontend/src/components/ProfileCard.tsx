"use client";

import { useState } from "react";
import { api, ApiError, type User } from "@/lib/api";
import { fechaCorta, plural } from "@/lib/fechas";
import { useSetUser, useUser } from "@/lib/UserContext";
import { Button } from "./ui/Button";
import { Card, CardTitle } from "./ui/Card";
import { DataList, DataRow } from "./ui/DataList";
import { FormField, fieldInputClass } from "./ui/FormField";

const ETIQUETA_SEXO: Record<User["sexo"], string> = {
  M: "Masculino",
  F: "Femenino",
};

/**
 * Fases de peso tal y como las usa el motor de nutrición
 * (`services.nutrition_service`). Se muestran con su nombre en
 * castellano y con lo que hacen: "cut" no significa nada por sí solo
 * para quien no venga del argot, y este campo decide el objetivo
 * calórico diario.
 */
const FASES: readonly { value: User["fase_peso_actual"]; label: string; efecto: string }[] = [
  { value: "cut", label: "Déficit", efecto: "Objetivo calórico por debajo de tu gasto" },
  { value: "maintenance", label: "Mantenimiento", efecto: "Objetivo calórico igual a tu gasto" },
  { value: "recomp", label: "Recomposición", efecto: "Déficit leve con proteína alta" },
  { value: "surplus", label: "Superávit", efecto: "Objetivo calórico por encima de tu gasto" },
];

function edadEnAnios(fechaNacimientoIso: string): number {
  const [anio, mes, dia] = fechaNacimientoIso.split("-").map(Number);
  const hoy = new Date();
  let edad = hoy.getFullYear() - anio;
  const yaCumplio = hoy.getMonth() + 1 > mes || (hoy.getMonth() + 1 === mes && hoy.getDate() >= dia);
  if (!yaCumplio) edad -= 1;
  return edad;
}

/**
 * "Tus datos" del Perfil: los datos personales que alimentan los
 * cálculos de la app, visibles y editables.
 *
 * Eran inmutables hasta ahora (solo se creaban en el alta vía Garmin),
 * y eso no era solo incómodo: `fase_peso_actual` decide el objetivo
 * calórico diario, así que no poder cambiarla dejaba el motor de
 * nutrición clavado en la fase del día que te registraste.
 *
 * Cada dato dice para qué se usa. Un perfil no es un formulario de
 * registro: es la explicación de por qué la app calcula lo que calcula.
 */
export function ProfileCard() {
  const usuario = useUser();
  const setUsuario = useSetUser();
  const [editando, setEditando] = useState(false);

  if (!editando) {
    const fase = FASES.find((f) => f.value === usuario.fase_peso_actual);
    return (
      <Card>
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <h2 className="t-section text-ink">Tus datos</h2>
          <Button variant="secondary" onClick={() => setEditando(true)}>
            Editar
          </Button>
        </div>
        <DataList>
          <DataRow label="Nombre">{usuario.nombre}</DataRow>
          <DataRow label="Altura" nota="Base del cálculo de tu gasto energético">
            <span className="tabular">{usuario.altura_cm}</span> cm
          </DataRow>
          <DataRow
            label="Nacimiento"
            nota={plural(edadEnAnios(usuario.fecha_nacimiento), "año", "años")}
          >
            {fechaCorta(usuario.fecha_nacimiento)}
          </DataRow>
          <DataRow label="Sexo">{ETIQUETA_SEXO[usuario.sexo]}</DataRow>
          <DataRow label="Fase de peso" nota={fase?.efecto}>
            {fase?.label ?? usuario.fase_peso_actual}
          </DataRow>
        </DataList>
      </Card>
    );
  }

  return (
    <Card>
      <CardTitle>Editar tus datos</CardTitle>
      <FormularioPerfil
        usuario={usuario}
        onGuardado={(actualizado) => {
          setUsuario(actualizado);
          setEditando(false);
        }}
        onCancelar={() => setEditando(false)}
      />
    </Card>
  );
}

function FormularioPerfil({
  usuario,
  onGuardado,
  onCancelar,
}: {
  usuario: User;
  onGuardado: (usuario: User) => void;
  onCancelar: () => void;
}) {
  const [nombre, setNombre] = useState(usuario.nombre);
  const [altura, setAltura] = useState(String(usuario.altura_cm));
  const [nacimiento, setNacimiento] = useState(usuario.fecha_nacimiento);
  const [sexo, setSexo] = useState<User["sexo"]>(usuario.sexo);
  const [fase, setFase] = useState<User["fase_peso_actual"]>(usuario.fase_peso_actual);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    const alturaNumero = Number(altura);
    if (!Number.isFinite(alturaNumero) || alturaNumero <= 0) {
      setError("La altura tiene que ser un número mayor que cero.");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      // Solo viaja lo que cambió: un PATCH con el perfil entero haría
      // indistinguible "no lo toqué" de "lo reescribí igual".
      const actualizado = await api.updateUser(usuario.id, {
        ...(nombre !== usuario.nombre && { nombre }),
        ...(alturaNumero !== usuario.altura_cm && { altura_cm: alturaNumero }),
        ...(nacimiento !== usuario.fecha_nacimiento && { fecha_nacimiento: nacimiento }),
        ...(sexo !== usuario.sexo && { sexo }),
        ...(fase !== usuario.fase_peso_actual && { fase_peso_actual: fase }),
      });
      onGuardado(actualizado);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron guardar los cambios.");
    } finally {
      setGuardando(false);
    }
  }

  const sinCambios =
    nombre === usuario.nombre &&
    Number(altura) === usuario.altura_cm &&
    nacimiento === usuario.fecha_nacimiento &&
    sexo === usuario.sexo &&
    fase === usuario.fase_peso_actual;

  return (
    <form onSubmit={guardar} className="flex flex-col gap-4">
      <FormField label="Nombre" htmlFor="perfil-nombre">
        <input
          id="perfil-nombre"
          type="text"
          className={fieldInputClass}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          required
        />
      </FormField>
      <FormField label="Altura (cm)" htmlFor="perfil-altura">
        <input
          id="perfil-altura"
          type="number"
          step="0.5"
          min="1"
          max="300"
          className={fieldInputClass}
          value={altura}
          onChange={(e) => setAltura(e.target.value)}
          required
        />
      </FormField>
      <FormField label="Fecha de nacimiento" htmlFor="perfil-nacimiento">
        <input
          id="perfil-nacimiento"
          type="date"
          className={fieldInputClass}
          value={nacimiento}
          onChange={(e) => setNacimiento(e.target.value)}
          required
        />
      </FormField>
      <FormField label="Sexo" htmlFor="perfil-sexo">
        <select
          id="perfil-sexo"
          className={fieldInputClass}
          value={sexo}
          onChange={(e) => setSexo(e.target.value as User["sexo"])}
        >
          <option value="M">Masculino</option>
          <option value="F">Femenino</option>
        </select>
      </FormField>
      <FormField
        label="Fase de peso"
        htmlFor="perfil-fase"
        hint={FASES.find((f) => f.value === fase)?.efecto}
      >
        <select
          id="perfil-fase"
          className={fieldInputClass}
          value={fase}
          onChange={(e) => setFase(e.target.value as User["fase_peso_actual"])}
        >
          {FASES.map((opcion) => (
            <option key={opcion.value} value={opcion.value}>
              {opcion.label}
            </option>
          ))}
        </select>
      </FormField>
      {error && (
        <p role="alert" className="t-secondary text-pretty text-neg">
          {error}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={guardando || sinCambios}>
          {guardando ? "Guardando..." : "Guardar cambios"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancelar} disabled={guardando}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
