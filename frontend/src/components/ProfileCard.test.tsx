import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileCard } from "./ProfileCard";
import { api, type User } from "@/lib/api";
import { UserProvider } from "@/lib/UserContext";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, updateUser: vi.fn() } };
});

const USUARIO: User = {
  id: 1,
  nombre: "Miguel",
  altura_cm: 176,
  fecha_nacimiento: "2002-11-28",
  sexo: "M",
  fase_peso_actual: "maintenance",
};

function montar(onUserChange = vi.fn()) {
  render(
    <UserProvider user={USUARIO} onUserChange={onUserChange}>
      <ProfileCard />
    </UserProvider>
  );
  return onUserChange;
}

describe("ProfileCard", () => {
  beforeEach(() => {
    vi.mocked(api.updateUser).mockReset();
  });

  it("muestra los datos en castellano, no los valores internos del modelo", () => {
    montar();
    expect(screen.getByText("Miguel")).toBeInTheDocument();
    expect(screen.getByText("Masculino")).toBeInTheDocument();
    // "maintenance" es el valor de la base de datos, no algo que
    // mostrar a una persona.
    expect(screen.getByText("Mantenimiento")).toBeInTheDocument();
    expect(screen.queryByText("maintenance")).not.toBeInTheDocument();
  });

  it("dice para qué sirve cada dato en vez de listarlo a secas", () => {
    montar();
    expect(screen.getByText(/objetivo calórico igual a tu gasto/i)).toBeInTheDocument();
  });

  it("envía solo los campos que cambiaron", async () => {
    vi.mocked(api.updateUser).mockResolvedValue({ ...USUARIO, fase_peso_actual: "cut" });
    const onUserChange = montar();

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText("Fase de peso"), { target: { value: "cut" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(api.updateUser).toHaveBeenCalledWith(1, { fase_peso_actual: "cut" }));
    // El usuario del contexto se actualiza: sin esto la cabecera
    // seguiría mostrando los datos viejos hasta recargar.
    expect(onUserChange).toHaveBeenCalledWith({ ...USUARIO, fase_peso_actual: "cut" });
  });

  it("no deja guardar si no se ha cambiado nada", () => {
    montar();
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
  });

  it("cancelar vuelve a la vista de lectura sin guardar", () => {
    montar();
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Otro" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(api.updateUser).not.toHaveBeenCalled();
    expect(screen.getByText("Miguel")).toBeInTheDocument();
  });
});
