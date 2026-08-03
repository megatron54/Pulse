import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReadinessTrendCard } from "./ReadinessTrendCard";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getReadinessHistory: vi.fn(),
    },
  };
});

describe("ReadinessTrendCard", () => {
  beforeEach(() => {
    vi.mocked(api.getReadinessHistory).mockReset();
  });

  it("renderiza un bloque de color por cada día del historial", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", resultado: "green", hrv_delta_pct: 2, training_readiness: "high", acwr: 1.0 },
      { id: 2, fecha: "2026-08-02", resultado: "yellow", hrv_delta_pct: -5, training_readiness: "moderate", acwr: 1.1 },
      { id: 3, fecha: "2026-08-03", resultado: "red", hrv_delta_pct: -15, training_readiness: "low", acwr: 1.6 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() => expect(screen.getAllByTestId("readiness-dia")).toHaveLength(3));
    const dias = screen.getAllByTestId("readiness-dia");
    expect(dias[0]).toHaveAttribute("title", expect.stringContaining("2026-08-01"));
    expect(dias[2]).toHaveClass("bg-recovery-low");
  });

  it("expone el significado por texto (aria-label), no solo por color (WCAG 1.4.1)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", resultado: "red", hrv_delta_pct: -15, training_readiness: "low", acwr: 1.6 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByRole("listitem", { name: /2026-08-01: alerta/i })).toBeInTheDocument()
    );
  });

  it("agrupa múltiples filas del mismo día quedándose con la última", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", resultado: "red", hrv_delta_pct: -20, training_readiness: "low", acwr: 1.6 },
      { id: 2, fecha: "2026-08-01", resultado: "green", hrv_delta_pct: 1, training_readiness: "high", acwr: 1.0 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() => expect(screen.getAllByTestId("readiness-dia")).toHaveLength(1));
    expect(screen.getByTestId("readiness-dia")).toHaveClass("bg-recovery-high");
  });

  it("muestra un mensaje cuando no hay check-ins todavía", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/todavía no hay check-ins/i)).toBeInTheDocument()
    );
  });

  it("vuelve a pedir el historial cuando cambia refreshKey (tras un check-in nuevo)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);

    const { rerender } = render(<ReadinessTrendCard userId={1} refreshKey={0} />);
    await waitFor(() => expect(api.getReadinessHistory).toHaveBeenCalledTimes(1));

    rerender(<ReadinessTrendCard userId={1} refreshKey={1} />);
    await waitFor(() => expect(api.getReadinessHistory).toHaveBeenCalledTimes(2));
  });
});
