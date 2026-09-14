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
      syncGarminNow: vi.fn(),
    },
  };
});

describe("DailySessionCard", () => {
  beforeEach(() => {
    vi.mocked(api.getDailySession).mockReset();
    vi.mocked(api.syncGarminNow).mockReset();
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

  it("si falta el recovery de hoy, lo dice y ofrece sincronizar (sin anunciarlo como error)", async () => {
    vi.mocked(api.getDailySession).mockRejectedValue(
      new ApiError(400, "ejecutar sync_and_compute_readiness primero", undefined, "sin_recovery")
    );
    render(<DailySessionCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/datos de recuperación de hoy/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /sincronizar garmin/i })).toBeInTheDocument();
    // No es un fallo del sistema: es un estado vacío esperado.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    // Y no debe filtrarse el mensaje de desarrollador del backend.
    expect(screen.queryByText(/sync_and_compute_readiness/)).not.toBeInTheDocument();
  });

  it("si falta el plan semanal, lo dice y lleva a crearlo (no ofrece sincronizar)", async () => {
    vi.mocked(api.getDailySession).mockRejectedValue(
      new ApiError(400, "crea un TrainingBlock con WeeklySchedule", undefined, "sin_plan")
    );
    render(<DailySessionCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/plan semanal activo/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /plan semanal/i })).toHaveAttribute(
      "href",
      "/entrenamiento"
    );
    expect(screen.queryByRole("button", { name: /sincronizar/i })).not.toBeInTheDocument();
  });

  it("sincronizar Garmin vuelve a pedir la sesion, que es lo que el usuario queria", async () => {
    vi.mocked(api.getDailySession).mockRejectedValueOnce(
      new ApiError(400, "sin recovery", undefined, "sin_recovery")
    );
    vi.mocked(api.syncGarminNow).mockResolvedValue({ fecha: "2026-09-14", puntos_intradia_nuevos: 3 });
    vi.mocked(api.getDailySession).mockResolvedValueOnce({
      session_type: "strength_heavy",
      volume_pct: 85,
      intensity_rpe_cap: 8,
      narrative_text: "Recuperación media.",
      narrative_source: "template",
    });

    render(<DailySessionCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /sincronizar garmin/i })).toBeInTheDocument()
    );
    screen.getByRole("button", { name: /sincronizar garmin/i }).click();

    await waitFor(() => expect(screen.getByText(/fuerza pesada/i)).toBeInTheDocument());
    expect(api.getDailySession).toHaveBeenCalledTimes(2);
  });

  it("un 400 sin motivo no deja al usuario sin mensaje", async () => {
    vi.mocked(api.getDailySession).mockRejectedValue(new ApiError(400, "sin datos"));
    render(<DailySessionCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/falta algún dato para decidir la sesión de hoy/i)).toBeInTheDocument()
    );
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
