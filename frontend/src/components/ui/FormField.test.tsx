import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FormField } from "./FormField";

describe("FormField", () => {
  it("asocia el label con el input vía htmlFor/id", () => {
    render(
      <FormField label="Peso (kg)" htmlFor="peso">
        <input id="peso" />
      </FormField>
    );
    expect(screen.getByLabelText("Peso (kg)")).toBeInTheDocument();
  });

  it("muestra la pista solo si no hay error", () => {
    render(
      <FormField label="Cuello" hint="Opcional">
        <input />
      </FormField>
    );
    expect(screen.getByText("Opcional")).toBeInTheDocument();
  });

  it("muestra el error en vez de la pista", () => {
    render(
      <FormField label="Peso" hint="Opcional" error="Requerido">
        <input />
      </FormField>
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Requerido");
    expect(screen.queryByText("Opcional")).not.toBeInTheDocument();
  });
});
