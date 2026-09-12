import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChipFilter } from "./ChipFilter";

describe("ChipFilter", () => {
  const OPTIONS = [
    { value: "todas", label: "Todas" },
    { value: "running", label: "Running" },
  ] as const;

  it("marca como seleccionado el chip activo", () => {
    render(<ChipFilter options={OPTIONS} value="todas" onChange={() => {}} ariaLabel="Deporte" />);
    expect(screen.getByRole("tab", { name: "Todas" })).toHaveAttribute("aria-selected", "true");
  });

  it("llama a onChange con el valor pulsado", () => {
    const onChange = vi.fn();
    render(<ChipFilter options={OPTIONS} value="todas" onChange={onChange} ariaLabel="Deporte" />);
    screen.getByRole("tab", { name: "Running" }).click();
    expect(onChange).toHaveBeenCalledWith("running");
  });
});
