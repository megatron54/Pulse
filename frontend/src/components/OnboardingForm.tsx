"use client";

import { useState } from "react";
import type { User, UserCreateInput } from "@/lib/api";
import { Card, CardTitle } from "./ui/Card";

const inputClass =
  "border border-surface-border bg-surface-muted rounded-lg px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-accent";

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
    <div className="max-w-md mx-auto">
      <Card>
        <CardTitle>Configura tu perfil</CardTitle>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm text-text-secondary">
            Nombre
            <input
              className={inputClass}
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-text-secondary">
            Altura (cm)
            <input
              type="number"
              className={inputClass}
              value={alturaCm}
              onChange={(e) => setAlturaCm(Number(e.target.value))}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-text-secondary">
            Fecha de nacimiento
            <input
              type="date"
              className={inputClass}
              value={fechaNacimiento}
              onChange={(e) => setFechaNacimiento(e.target.value)}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-text-secondary">
            Sexo
            <select
              className={inputClass}
              value={sexo}
              onChange={(e) => setSexo(e.target.value as "M" | "F")}
            >
              <option value="M">Masculino</option>
              <option value="F">Femenino</option>
            </select>
          </label>
          {error && <p className="text-recovery-low text-sm">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="bg-accent text-white font-semibold rounded-lg px-4 py-2.5 disabled:bg-surface-muted disabled:text-text-secondary disabled:cursor-not-allowed disabled:hover:scale-100 transition-transform hover:scale-[1.02] active:scale-[0.98]"
          >
            {submitting ? "Creando..." : "Crear perfil"}
          </button>
        </form>
      </Card>
    </div>
  );
}
