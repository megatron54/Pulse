import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatTile } from "./StatTile";

describe("StatTile", () => {
  it("muestra la etiqueta, el valor y la unidad", () => {
    render(<StatTile label="VFC" value={54} unit=" ms" />);
    expect(screen.getByText("VFC")).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, el) => el?.textContent === "54ms" || el?.textContent === "54 ms"
      )
    ).toBeInTheDocument();
  });

  it("no pinta ningún icono: en v3 la métrica es el dato, no el adorno", () => {
    const { container } = render(<StatTile label="Sueño" value={83} />);
    expect(container.querySelector("svg")).toBeNull();
  });
});
