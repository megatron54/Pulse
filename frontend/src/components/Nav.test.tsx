import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Nav } from "./Nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/entrenamiento",
}));

describe("Nav", () => {
  it("renderiza un enlace a cada una de las 5 secciones (Coach fuera, Perfil dentro)", () => {
    render(<Nav />);
    const sidebar = screen.getByRole("navigation", { name: "Navegación principal" });
    for (const nombre of ["Hoy", "Cuerpo", "Entrenamiento", "Nutrición", "Perfil"]) {
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
    // "Entreno", no "Entrenamiento": a 390px la etiqueta larga no cabe
    // en un quinto de pantalla, y truncar está prohibido. El nombre
    // accesible es el texto visible (WCAG 2.5.3, "Label in Name"), así
    // que aquí se consulta por la etiqueta corta a propósito.
    const enlaceActivo = within(barraMovil).getByRole("link", { name: /entreno/i });
    expect(enlaceActivo).toHaveAttribute("aria-current", "page");
  });

  it("Coach ya no ocupa un sitio en la navegación principal", () => {
    render(<Nav />);
    expect(screen.queryByRole("link", { name: /coach/i })).not.toBeInTheDocument();
  });
});
