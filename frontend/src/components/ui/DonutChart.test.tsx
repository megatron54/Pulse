import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DonutChart } from "./DonutChart";

describe("DonutChart", () => {
  it("renderiza sin lanzar con varios segmentos", async () => {
    const { container } = render(
      <DonutChart
        segments={[
          { nombre: "Proteína", valor: 150, color: "#00F19F" },
          { nombre: "Carbohidratos", valor: 200, color: "#67AEE6" },
          { nombre: "Grasa", valor: 70, color: "#7BA1BB" },
        ]}
      />
    );
    await waitFor(() => expect(container.querySelector("svg")).toBeInTheDocument());
  });

  it("renderiza el contenido central superpuesto", () => {
    const { getByText } = render(
      <DonutChart
        segments={[{ nombre: "A", valor: 1, color: "#fff" }]}
        centro={<span>2400 kcal</span>}
      />
    );
    expect(getByText("2400 kcal")).toBeInTheDocument();
  });
});
