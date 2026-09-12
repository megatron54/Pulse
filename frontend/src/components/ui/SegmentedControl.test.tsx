import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SegmentedControl } from "./SegmentedControl";

describe("SegmentedControl", () => {
  const OPTIONS = [
    { value: "sesiones", label: "Sesiones" },
    { value: "plan", label: "Plan" },
  ] as const;

  it("marca como seleccionada la opción activa", () => {
    render(
      <SegmentedControl options={OPTIONS} value="sesiones" onChange={() => {}} ariaLabel="Vista" />
    );
    expect(screen.getByRole("tab", { name: "Sesiones" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Plan" })).toHaveAttribute("aria-selected", "false");
  });

  it("llama a onChange con el valor pulsado", () => {
    const onChange = vi.fn();
    render(
      <SegmentedControl options={OPTIONS} value="sesiones" onChange={onChange} ariaLabel="Vista" />
    );
    screen.getByRole("tab", { name: "Plan" }).click();
    expect(onChange).toHaveBeenCalledWith("plan");
  });
});
