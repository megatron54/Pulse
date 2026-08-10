import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecoveryRing } from "./RecoveryRing";
import { PALETA } from "@/lib/theme";

describe("RecoveryRing", () => {
  it("muestra el porcentaje formateado en el centro del anillo", () => {
    render(<RecoveryRing percent={78} zone="green" />);
    expect(screen.getByText("78%")).toBeInTheDocument();
  });

  // Los tests de color leen `PALETA` en vez de hardcodear hex (hallazgo
  // de code-review del rediseño estilo Apple: la versión anterior
  // fijaba los hex viejos de la guía de marca de WHOOP como string
  // literal, y quedó desincronizada en cuanto `theme.ts` se repintó).
  it("usa el color de zona 'green' de la paleta activa", () => {
    const { container } = render(<RecoveryRing percent={78} zone="green" />);
    const arcoProgreso = container.querySelector('circle[data-testid="ring-progress"]');
    expect(arcoProgreso).toHaveAttribute("stroke", PALETA.recoveryHigh);
  });

  it("usa el color de zona 'yellow' de la paleta activa", () => {
    const { container } = render(<RecoveryRing percent={50} zone="yellow" />);
    const arcoProgreso = container.querySelector('circle[data-testid="ring-progress"]');
    expect(arcoProgreso).toHaveAttribute("stroke", PALETA.recoveryMedium);
  });

  it("usa el color de zona 'red' de la paleta activa", () => {
    const { container } = render(<RecoveryRing percent={20} zone="red" />);
    const arcoProgreso = container.querySelector('circle[data-testid="ring-progress"]');
    expect(arcoProgreso).toHaveAttribute("stroke", PALETA.recoveryLow);
  });

  it("deriva la zona automáticamente del porcentaje si no se especifica (umbrales 67/34)", () => {
    const { container: verde } = render(<RecoveryRing percent={80} />);
    expect(
      verde.querySelector('circle[data-testid="ring-progress"]')
    ).toHaveAttribute("stroke", PALETA.recoveryHigh);

    const { container: amarillo } = render(<RecoveryRing percent={50} />);
    expect(
      amarillo.querySelector('circle[data-testid="ring-progress"]')
    ).toHaveAttribute("stroke", PALETA.recoveryMedium);

    const { container: rojo } = render(<RecoveryRing percent={20} />);
    expect(
      rojo.querySelector('circle[data-testid="ring-progress"]')
    ).toHaveAttribute("stroke", PALETA.recoveryLow);
  });

  it("acepta una etiqueta debajo del porcentaje", () => {
    render(<RecoveryRing percent={78} zone="green" label="Recovery" />);
    expect(screen.getByText("Recovery")).toBeInTheDocument();
  });

  it("expone el valor por accesibilidad vía aria-label del SVG (WCAG 1.4.1, no solo color)", () => {
    render(<RecoveryRing percent={78} zone="green" label="Recovery" />);
    expect(
      screen.getByRole("img", { name: /recovery.*78.*verde/i })
    ).toBeInTheDocument();
  });

  it("redondea el porcentaje mostrado a un entero", () => {
    render(<RecoveryRing percent={77.6} zone="green" />);
    expect(screen.getByText("78%")).toBeInTheDocument();
  });

  it("clampa valores fuera de rango 0-100", () => {
    render(<RecoveryRing percent={150} zone="green" />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("en modo categórico (categoryLabel) muestra la palabra de la zona en vez de un número inventado", () => {
    // Regresión de hallazgo CRÍTICO de code-review: el motor de reglas
    // de Pulse es categórico (verde/amarillo/rojo), NUNCA emite un
    // score continuo 0-100 como el de WHOOP. Mostrar un número
    // fabricado dentro de un anillo idéntico al de WHOOP induciría a
    // pensar que es una medición real. En este modo, el centro del
    // anillo muestra la palabra de la zona, nunca un "%".
    render(<RecoveryRing zone="green" categoryLabel="óptimo" label="Recovery" />);
    expect(screen.getByText("ÓPTIMO")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("en modo categórico, el aria-label anuncia la palabra de la zona, no un porcentaje", () => {
    render(<RecoveryRing zone="red" categoryLabel="alerta" label="Recovery" />);
    const svg = screen.getByRole("img");
    expect(svg.getAttribute("aria-label")).not.toMatch(/%/);
    expect(svg.getAttribute("aria-label")).toMatch(/alerta/i);
  });

  it("en modo categórico, el arco se rellena hasta un punto representativo fijo de la zona (sin mostrar el número)", () => {
    const { container } = render(<RecoveryRing zone="yellow" categoryLabel="precaución" />);
    const arco = container.querySelector('circle[data-testid="ring-progress"]');
    expect(arco).toHaveAttribute("stroke", PALETA.recoveryMedium);
    expect(arco).toHaveAttribute("stroke-dasharray");
  });
});
