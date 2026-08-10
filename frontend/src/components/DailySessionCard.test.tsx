import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DailySessionCard } from "./DailySessionCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getDailySession: vi.fn(),
    },
  };
});

describe("DailySessionCard", () => {
  beforeEach(() => {
    vi.mocked(api.getDailySession).mockReset();
  });

  it("se carga automaticamente al montar, sin pulsar ningun boton", async () => {
    vi.mocked(api.getDailySession).mockResolvedValue({
      session_type: "strength_heavy",
      volume_pct: 100,
      intensity_rpe_cap: null,
      narrative_text: "Todo verde, sesion completa.",
      narrative_source: "template",
    });
    render(<DailySessionCard userId={1} />);
    await waitFor(() => expect(api.getDailySession).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/fuerza pesada/i)).toBeInTheDocument();
  });

  it("no pide seleccionar manualmente que tocaba hoy", () => {
    vi.mocked(api.getDailySession).mockResolvedValue({
      session_type: "rest",
      volume_pct: 0,
      intensity_rpe_cap: null,
      narrative_text: "Descanso.",
      narrative_source: "template",
    });
    render(<DailySessionCard userId={1} />);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("explica honestamente si falta recovery de hoy o plan activo (400), sin anunciarlo como error", async () => {
    vi.mocked(api.getDailySession).mockRejectedValue(new ApiError(400, "sin datos"));
    render(<DailySessionCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/aún no hay recovery de hoy sincronizado/i)).toBeInTheDocument()
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("el reintento vuelve a pedir la sesion", async () => {
    vi.mocked(api.getDailySession).mockRejectedValueOnce(new ApiError(500, "caido"));
    render(<DailySessionCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    vi.mocked(api.getDailySession).mockResolvedValueOnce({
      session_type: "rest",
      volume_pct: 0,
      intensity_rpe_cap: null,
      narrative_text: "Descanso.",
      narrative_source: "template",
    });
    screen.getByRole("button", { name: /reintentar/i }).click();

    await waitFor(() => expect(api.getDailySession).toHaveBeenCalledTimes(2));
  });
});
