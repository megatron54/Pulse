import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoadingState } from "./LoadingState";

describe("LoadingState", () => {
  it("anuncia el estado de carga a lectores de pantalla", () => {
    render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveAccessibleName("Cargando");
  });

  it("renderiza el numero de lineas de shimmer pedido", () => {
    const { container } = render(<LoadingState lines={3} />);
    expect(container.querySelectorAll('[data-testid="shimmer-bar"]')).toHaveLength(3);
  });
});
