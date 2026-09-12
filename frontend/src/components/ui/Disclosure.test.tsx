import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Disclosure } from "./Disclosure";

describe("Disclosure", () => {
  it("empieza cerrado por defecto", () => {
    render(
      <Disclosure summary="Medida manual opcional">
        <p>Contenido</p>
      </Disclosure>
    );
    expect(screen.queryByText("Contenido")).not.toBeInTheDocument();
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });

  it("se abre al pulsar el resumen", () => {
    render(
      <Disclosure summary="Medida manual opcional">
        <p>Contenido</p>
      </Disclosure>
    );
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Contenido")).toBeInTheDocument();
  });

  it("respeta defaultOpen", () => {
    render(
      <Disclosure summary="Medida manual opcional" defaultOpen>
        <p>Contenido</p>
      </Disclosure>
    );
    expect(screen.getByText("Contenido")).toBeInTheDocument();
  });
});
