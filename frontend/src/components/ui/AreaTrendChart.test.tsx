import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AreaTrendChart } from "./AreaTrendChart";

describe("AreaTrendChart", () => {
  it("renderiza sin lanzar con datos válidos", () => {
    render(
      <AreaTrendChart
        data={[
          { fecha: "2026-08-01", valor: 80 },
          { fecha: "2026-08-02", valor: 79.5 },
        ]}
        color="#00F19F"
      />
    );
    expect(screen.getByRole("img", { name: /gráfica de tendencia/i })).toBeInTheDocument();
  });

  it("no revienta con un solo punto de dato", () => {
    render(<AreaTrendChart data={[{ fecha: "2026-08-01", valor: 80 }]} color="#00F19F" />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});
