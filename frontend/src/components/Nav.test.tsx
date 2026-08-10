import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Nav } from "./Nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/entrenamiento",
}));

describe("Nav", () => {
  it("renderiza un enlace a cada una de las 7 secciones (reconstruccion v2)", () => {
    render(<Nav />);
    const sidebar = screen.getByRole("navigation", { name: "Navegación principal" });
    for (const nombre of [
      "Hoy",
      "Entrenamiento",
      "Recuperación",
      "Análisis",
      "Coach",
      "Nutrición",
      "Cuerpo",
    ]) {
      expect(within(sidebar).getByText(nombre)).toBeInTheDocument();
    }
  });

  it("ya no muestra Running/Ciclismo/Gimnasio/Garmin como secciones de primer nivel", () => {
    render(<Nav />);
    const sidebar = screen.getByRole("navigation", { name: "Navegación principal" });
    for (const nombre of ["Running", "Ciclismo", "Gimnasio", "Garmin"]) {
      expect(within(sidebar).queryByText(nombre)).not.toBeInTheDocument();
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
    const enlaceActivo = within(barraMovil).getByRole("link", { name: /entrenamiento/i });
    expect(enlaceActivo).toHaveAttribute("aria-current", "page");
  });
});
