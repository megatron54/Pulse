"use client";

import { useState } from "react";
import type { User, UserCreateInput } from "@/lib/api";

export function OnboardingForm({
  onCreate,
}: {
  onCreate: (data: UserCreateInput) => Promise<User>;
}) {
  const [nombre, setNombre] = useState("");
  const [alturaCm, setAlturaCm] = useState(175);
  const [fechaNacimiento, setFechaNacimiento] = useState("1995-01-01");
  const [sexo, setSexo] = useState<"M" | "F">("M");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onCreate({
        nombre,
        altura_cm: alturaCm,
        fecha_nacimiento: fechaNacimiento,
        sexo,
        fase_peso_actual: "maintenance",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md mx-auto p-6 border rounded-lg">
      <h2 className="text-lg font-semibold mb-4">Configura tu perfil</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          Nombre
          <input
            className="border rounded px-2 py-1"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          Altura (cm)
          <input
            type="number"
            className="border rounded px-2 py-1"
            value={alturaCm}
            onChange={(e) => setAlturaCm(Number(e.target.value))}
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          Fecha de nacimiento
          <input
            type="date"
            className="border rounded px-2 py-1"
            value={fechaNacimiento}
            onChange={(e) => setFechaNacimiento(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          Sexo
          <select
            className="border rounded px-2 py-1"
            value={sexo}
            onChange={(e) => setSexo(e.target.value as "M" | "F")}
          >
            <option value="M">Masculino</option>
            <option value="F">Femenino</option>
          </select>
        </label>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="bg-black text-white rounded px-4 py-2 disabled:opacity-50"
        >
          {submitting ? "Creando..." : "Crear perfil"}
        </button>
      </form>
    </div>
  );
}
