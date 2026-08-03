import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UserProvider, useUser } from "./UserContext";
import type { User } from "./api";

const usuarioFalso: User = {
  id: 1,
  nombre: "Test",
  altura_cm: 180,
  fecha_nacimiento: "1995-01-01",
  sexo: "M",
  fase_peso_actual: "maintenance",
};

function ComponenteQueUsaUser() {
  const user = useUser();
  return <p>Hola, {user.nombre}</p>;
}

describe("UserContext", () => {
  it("useUser() devuelve el usuario cuando hay un UserProvider", () => {
    render(
      <UserProvider user={usuarioFalso}>
        <ComponenteQueUsaUser />
      </UserProvider>
    );
    expect(screen.getByText("Hola, Test")).toBeInTheDocument();
  });

  it("useUser() lanza un error explícito si se usa fuera de un UserProvider", () => {
    // Silencia el log de error de React para este test esperado.
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<ComponenteQueUsaUser />)).toThrow(/AppShell/);
    consoleError.mockRestore();
  });
});
