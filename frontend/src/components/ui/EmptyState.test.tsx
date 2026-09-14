import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("muestra el mensaje", () => {
    render(<EmptyState message="Todavía no hay datos." />);
    expect(screen.getByText("Todavía no hay datos.")).toBeInTheDocument();
  });

  it("no pinta ningún icono: en v3 un estado vacío es información, no un cartel", () => {
    const { container } = render(<EmptyState message="Vacío" />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("puede ofrecer la acción que resuelve el vacío", () => {
    render(
      <EmptyState message="Sin mediciones." accion={<button>Añadir medición</button>} />
    );
    expect(screen.getByRole("button", { name: "Añadir medición" })).toBeInTheDocument();
  });
});
