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

  it("con `href` toda la casilla es el enlace a su detalle, cifra incluida", () => {
    // La etiqueta mide 11px: si el enlace fuera solo el texto, en móvil
    // sería un blanco imposible de acertar (doctrina 4).
    render(<StatTile label="Sueño" value={83} href="/salud/sueno" />);
    const enlace = screen.getByRole("link", { name: /sueño/i });
    expect(enlace).toHaveAttribute("href", "/salud/sueno");
    expect(enlace).toHaveTextContent("83");
  });

  it("sin `href` no finge ser pulsable", () => {
    render(<StatTile label="Sueño" value={83} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("Sueño")).not.toHaveClass("underline");
  });

  it("la pista de que se puede pulsar no depende del cursor", () => {
    // Con `group-hover:underline` las seis puertas al detalle de "Hoy"
    // eran invisibles en móvil, que es donde se usa la app (doctrina 5:
    // nada que solo se entienda con el cursor encima).
    render(<StatTile label="Sueño" value={83} href="/salud/sueno" />);
    expect(screen.getByText("Sueño")).toHaveClass("underline");
  });
});
