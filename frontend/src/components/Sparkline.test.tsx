import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Sparkline } from "./Sparkline";

describe("Sparkline", () => {
  it("renders un SVG con una polyline con tantos puntos como valores", () => {
    const { container } = render(<Sparkline values={[70, 71, 69, 68]} />);
    const polyline = container.querySelector("polyline");
    expect(polyline).toBeInTheDocument();
    // 4 valores -> 4 pares "x,y" en el atributo points.
    const puntos = polyline?.getAttribute("points")?.trim().split(" ");
    expect(puntos).toHaveLength(4);
  });

  it("muestra un mensaje de 'sin datos' si la serie está vacía, sin romper", () => {
    render(<Sparkline values={[]} />);
    expect(screen.getByText(/sin datos suficientes/i)).toBeInTheDocument();
  });

  it("muestra el mismo mensaje con un único punto (no se puede trazar una línea)", () => {
    render(<Sparkline values={[70]} />);
    expect(screen.getByText(/sin datos suficientes/i)).toBeInTheDocument();
  });

  it("no rompe si todos los valores son iguales (rango cero)", () => {
    const { container } = render(<Sparkline values={[70, 70, 70]} />);
    expect(container.querySelector("polyline")).toBeInTheDocument();
  });

  it("aplica el color proporcionado a la línea", () => {
    const { container } = render(
      <Sparkline values={[1, 2, 3]} strokeColor="#ff0000" />
    );
    expect(container.querySelector("polyline")).toHaveAttribute("stroke", "#ff0000");
  });

  it("usa el label proporcionado como aria-label del SVG", () => {
    render(<Sparkline values={[1, 2, 3]} label="Tendencia de peso, último 80kg" />);
    expect(
      screen.getByRole("img", { name: "Tendencia de peso, último 80kg" })
    ).toBeInTheDocument();
  });

  it("normaliza la geometría de la polyline al rango vertical esperado", () => {
    // Serie conocida: min=10, max=20 -> el punto mínimo debe quedar
    // cerca del borde inferior (y alto) y el máximo cerca del superior
    // (y bajo), respetando el padding vertical documentado.
    const { container } = render(<Sparkline values={[10, 20, 10]} />);
    const puntos = container
      .querySelector("polyline")!
      .getAttribute("points")!
      .trim()
      .split(" ")
      .map((p) => p.split(",").map(Number));

    const [, y1] = puntos[0];
    const [, y2] = puntos[1];
    const [, y3] = puntos[2];
    expect(y2).toBeLessThan(y1); // el valor máximo (20) queda más arriba (y menor)
    expect(y3).toBeCloseTo(y1, 1); // los dos valores mínimos (10) quedan a la misma altura
  });
});
