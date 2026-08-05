import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnimatedNumber } from "./AnimatedNumber";

describe("AnimatedNumber", () => {
  it("muestra el valor inicial de inmediato", () => {
    render(<AnimatedNumber value={2000} />);
    expect(screen.getByText("2000")).toBeInTheDocument();
  });

  it("respeta el numero de decimales", () => {
    render(<AnimatedNumber value={1.5} decimals={1} />);
    expect(screen.getByText("1.5")).toBeInTheDocument();
  });

  it("anima hacia el nuevo valor cuando la prop cambia", async () => {
    const { rerender } = render(<AnimatedNumber value={100} />);
    expect(screen.getByText("100")).toBeInTheDocument();

    rerender(<AnimatedNumber value={200} />);

    await waitFor(() => expect(screen.getByText("200")).toBeInTheDocument());
  });
});
