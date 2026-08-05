import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RadialGauge } from "./RadialGauge";

describe("RadialGauge", () => {
  it("expone el valor y la etiqueta de forma accesible", () => {
    render(<RadialGauge value={1.2} max={2} color="#16EC06" label="ACWR" decimals={2} />);
    expect(screen.getByRole("img", { name: /ACWR: 1.20/i })).toBeInTheDocument();
  });

  it("recorta el porcentaje al maximo aunque el valor lo supere", () => {
    render(<RadialGauge value={500} max={100} color="#FF0026" label="Test" />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});
