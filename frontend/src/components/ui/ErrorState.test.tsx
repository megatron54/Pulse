import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("muestra el mensaje como alert", () => {
    render(<ErrorState message="Algo falló." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Algo falló.");
  });

  it("sin onRetry no muestra boton de reintentar", () => {
    render(<ErrorState message="Algo falló." />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("con onRetry muestra el boton y lo dispara al hacer click", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorState message="Algo falló." onRetry={onRetry} />);

    await user.click(screen.getByRole("button", { name: /reintentar/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
