import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MacroBar } from "./MacroBar";

describe("MacroBar", () => {
  it("muestra los gramos de cada macro en la leyenda", () => {
    render(
      <MacroBar
        segments={[
          { label: "Proteína", grams: 180, kcal: 720, color: "#0A84FF" },
          { label: "Carbohidratos", grams: 250, kcal: 1000, color: "#30D158" },
          { label: "Grasa", grams: 70, kcal: 630, color: "#FFD60A" },
        ]}
      />
    );
    expect(screen.getByText("180g")).toBeInTheDocument();
    expect(screen.getByText("250g")).toBeInTheDocument();
    expect(screen.getByText("70g")).toBeInTheDocument();
  });

  it("omite un segmento sin kcal en la barra sin romper el render", () => {
    render(
      <MacroBar
        segments={[
          { label: "Proteína", grams: 180, kcal: 720, color: "#0A84FF" },
          { label: "Carbohidratos", grams: 0, kcal: 0, color: "#30D158" },
        ]}
      />
    );
    expect(screen.getByText("0g")).toBeInTheDocument();
  });
});
