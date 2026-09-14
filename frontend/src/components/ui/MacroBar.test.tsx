import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MacroBar } from "./MacroBar";

describe("MacroBar", () => {
  it("muestra los gramos y el porcentaje de kcal de cada macro", () => {
    render(
      <MacroBar
        macros={[
          { label: "Proteína", gramos: 180, kcal: 720 },
          { label: "Carbohidratos", gramos: 250, kcal: 1000 },
          { label: "Grasa", gramos: 70, kcal: 630 },
        ]}
      />
    );

    expect(screen.getByText("180 g")).toBeInTheDocument();
    expect(screen.getByText("250 g")).toBeInTheDocument();
    expect(screen.getByText("70 g")).toBeInTheDocument();
    // La proporción, que es la única razón de ser de la barra, también
    // se escribe: 720 de 2350 kcal = 31 %.
    expect(screen.getByText("31 %")).toBeInTheDocument();
    expect(screen.getByText("43 %")).toBeInTheDocument();
    expect(screen.getByText("27 %")).toBeInTheDocument();
  });

  it("omite un segmento sin kcal en la barra sin romper el render", () => {
    render(
      <MacroBar
        macros={[
          { label: "Proteína", gramos: 180, kcal: 720 },
          { label: "Carbohidratos", gramos: 0, kcal: 0 },
        ]}
      />
    );

    expect(screen.getByText("0 g")).toBeInTheDocument();
    expect(screen.getByText("0 %")).toBeInTheDocument();
  });

  it("no dibuja nada si el objetivo no tiene kcal (no hay proporción que mostrar)", () => {
    const { container } = render(
      <MacroBar macros={[{ label: "Proteína", gramos: 0, kcal: 0 }]} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
