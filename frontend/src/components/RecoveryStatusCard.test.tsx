import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecoveryStatusCard } from "./RecoveryStatusCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthHistory: vi.fn(),
      getReadinessHistory: vi.fn(),
      // CoachNarrativeBlock llama a esto internamente - se mockea para
      // que los tests no disparen una petición de red real de fondo.
      getGarminHealthNarrative: vi.fn().mockResolvedValue({ text: null, source: null }),
    },
  };
});

describe("RecoveryStatusCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
    vi.mocked(api.getReadinessHistory).mockReset();
    vi.mocked(api.getGarminHealthNarrative).mockReset();
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({ text: null, source: null });
  });

  it("pide solo el readiness de hoy y los ultimos 7 dias de historial (nunca todo el historico)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(api.getReadinessHistory).toHaveBeenCalledWith(1, 1));
    expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 7);
  });

  it("muestra 'Aun sin datos de hoy' (nunca un cero inventado) si el scheduler no ha sincronizado todavia", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/aún sin datos de hoy/i)).toBeInTheDocument());
  });

  it("muestra el semaforo de zona cuando ya hay un readiness calculado hoy", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-10", resultado: "green", hrv_delta_pct: 2, training_readiness: "high", acwr: 1 },
    ]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/recovery alta/i)).toBeInTheDocument());
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getReadinessHistory).mockRejectedValue(new ApiError(500, "caido"));
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("muestra el valor de hoy de cada metrica con datos, y omite las que no tienen ninguno", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-10",
        hrv_value: 49,
        hrv_status: "NONE",
        body_battery_am: 77,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
      },
    ]);

    render(<RecoveryStatusCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/vfc/i)).toBeInTheDocument());
    expect(screen.getByText(/body battery/i)).toBeInTheDocument();
    expect(screen.getByText(/sueño/i)).toBeInTheDocument();
    expect(screen.queryByText(/estrés/i)).not.toBeInTheDocument();
  });

  it("no renderiza ningun formulario manual (check-in eliminado del todo)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/aún sin datos de hoy/i)).toBeInTheDocument());
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });
});
