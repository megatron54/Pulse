import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("renderiza el texto y responde a click", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Guardar</Button>);

    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("tiene un anillo de foco visible (accesibilidad de teclado)", () => {
    render(<Button>Guardar</Button>);
    const boton = screen.getByRole("button", { name: "Guardar" });
    expect(boton.className).toMatch(/focus-visible:ring-2/);
  });

  it("respeta disabled y no dispara onClick", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button onClick={onClick} disabled>
        Guardar
      </Button>
    );
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("la variante ghost tiene area minima de 44px (WCAG 2.5.5)", () => {
    render(<Button variant="ghost">Añadir</Button>);
    const boton = screen.getByRole("button", { name: "Añadir" });
    expect(boton.className).toMatch(/min-h-11/);
    expect(boton.className).toMatch(/min-w-11/);
  });
});
