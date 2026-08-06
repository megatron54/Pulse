import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Nav } from "./Nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/entrenamiento",
}));

describe("Nav", () => {
  it("renderiza un enlace a cada sección principal en el sidebar de escritorio", () => {
    render(<Nav />);
    const sidebar = screen.getByRole("navigation", { name: "Navegación principal" });
    for (const nombre of ["Hoy", "Salud", "Entrenamiento", "Nutrición", "Cuerpo", "Garmin"]) {
      expect(within(sidebar).getByText(nombre)).toBeInTheDocument();
    }
  });

  it("marca como activo el enlace de la ruta actual en el sidebar", () => {
    render(<Nav />);
    const sidebar = screen.getByRole("navigation", { name: "Navegación principal" });
    const enlaceActivo = within(sidebar).getByRole("link", { name: /entrenamiento/i });
    expect(enlaceActivo).toHaveAttribute("aria-current", "page");
  });

  it("la ruta raíz 'Hoy' no queda activa cuando la ruta actual es otra sección", () => {
    render(<Nav />);
    const sidebar = screen.getByRole("navigation", { name: "Navegación principal" });
    const enlaceHoy = within(sidebar).getByRole("link", { name: /^hoy$/i });
    expect(enlaceHoy).not.toHaveAttribute("aria-current");
  });

  it("la barra de pestañas móvil también marca la ruta activa", () => {
    render(<Nav />);
    const barraMovil = screen.getByRole("navigation", { name: "Navegación principal (móvil)" });
    const enlaceActivo = within(barraMovil).getByRole("link", { name: /entreno/i });
    expect(enlaceActivo).toHaveAttribute("aria-current", "page");
  });
});
