import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Ghost } from "lucide-react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("muestra el mensaje y el icono decorativo", () => {
    render(<EmptyState icon={Ghost} message="Todavía no hay datos." />);
    expect(screen.getByText("Todavía no hay datos.")).toBeInTheDocument();
  });

  it("el icono no interfiere con lectores de pantalla", () => {
    const { container } = render(<EmptyState icon={Ghost} message="Vacío" />);
    const icono = container.querySelector("svg");
    expect(icono).toHaveAttribute("aria-hidden", "true");
  });
});
