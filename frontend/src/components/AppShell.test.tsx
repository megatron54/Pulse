import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import { useCurrentUser } from "@/lib/useCurrentUser";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

vi.mock("@/lib/useCurrentUser", () => ({
  useCurrentUser: vi.fn(),
}));

describe("AppShell", () => {
  beforeEach(() => {
    vi.mocked(useCurrentUser).mockReset();
  });

  it("anuncia el estado de carga mientras useCurrentUser resuelve", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: null,
      loading: true,
      error: null,
      createUser: vi.fn(),
    });
    render(
      <AppShell>
        <p>Contenido de la página</p>
      </AppShell>
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("Contenido de la página")).not.toBeInTheDocument();
  });

  it("muestra el onboarding (sin nav) cuando no hay usuario todavía", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: null,
      loading: false,
      error: null,
      createUser: vi.fn(),
    });
    render(
      <AppShell>
        <p>Contenido de la página</p>
      </AppShell>
    );
    expect(screen.getByText("Configura tu perfil")).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByText("Contenido de la página")).not.toBeInTheDocument();
  });

  it("muestra el error de creación de usuario si lo hay", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: null,
      loading: false,
      error: "fallo al crear usuario",
      createUser: vi.fn(),
    });
    render(
      <AppShell>
        <p>Contenido de la página</p>
      </AppShell>
    );
    expect(screen.getByText("fallo al crear usuario")).toBeInTheDocument();
  });

  it("monta la navegación y el contenido de la página una vez hay usuario", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {
        id: 1,
        nombre: "Test",
        altura_cm: 180,
        fecha_nacimiento: "1995-01-01",
        sexo: "M",
        fase_peso_actual: "maintenance",
      },
      loading: false,
      error: null,
      createUser: vi.fn(),
    });
    render(
      <AppShell>
        <p>Contenido de la página</p>
      </AppShell>
    );
    expect(screen.getAllByRole("navigation").length).toBeGreaterThan(0);
    expect(screen.getByText("Contenido de la página")).toBeInTheDocument();
  });
});
