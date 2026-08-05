import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PeriodicSummaryCard } from "./PeriodicSummaryCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getPeriodicSummary: vi.fn(),
    },
  };
});

const _RESUMEN_VACIO = {
  dias_con_checkin_readiness: 0,
  distribucion_readiness: { green: 0, yellow: 0, red: 0 },
  training_load: {
    acute_avg_7d: null,
    chronic_avg_28d: null,
    acwr: null,
    dias_con_dato_agudo: 0,
    dias_con_dato_cronico: 0,
    datos_suficientes: false,
  },
  peso_inicio_kg: null,
  peso_fin_kg: null,
  peso_delta_kg: null,
  actividades_totales: 0,
  duracion_actividades_total_seg: 0,
};

describe("PeriodicSummaryCard", () => {
  beforeEach(() => {
    vi.mocked(api.getPeriodicSummary).mockReset();
  });

  it("muestra la distribucion de readiness de la semana", async () => {
    vi.mocked(api.getPeriodicSummary).mockResolvedValue({
      ..._RESUMEN_VACIO,
      dias_con_checkin_readiness: 5,
      distribucion_readiness: { green: 3, yellow: 1, red: 1 },
    });

    render(<PeriodicSummaryCard userId={1} />);

    await waitFor(() => expect(screen.getByText("3")).toBeInTheDocument());
    expect(screen.getByText(/5 días con check-in/i)).toBeInTheDocument();
  });

  it("no muestra el delta de peso cuando no hay suficientes mediciones", async () => {
    vi.mocked(api.getPeriodicSummary).mockResolvedValue(_RESUMEN_VACIO);
    render(<PeriodicSummaryCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/sin suficientes mediciones de peso/i)).toBeInTheDocument()
    );
  });

  it("muestra el delta de peso cuando hay al menos dos mediciones", async () => {
    vi.mocked(api.getPeriodicSummary).mockResolvedValue({
      ..._RESUMEN_VACIO,
      peso_inicio_kg: 80.0,
      peso_fin_kg: 79.2,
      peso_delta_kg: -0.8,
    });

    render(<PeriodicSummaryCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/-0.8 kg/i)).toBeInTheDocument());
  });

  it("muestra un error si la petición falla", async () => {
    vi.mocked(api.getPeriodicSummary).mockRejectedValue(new ApiError(404, "no existe"));
    render(<PeriodicSummaryCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("vuelve a pedir el resumen cuando cambia refreshKey (tras un check-in nuevo)", async () => {
    // Regresión de un hallazgo real de verificación manual con
    // Playwright: tras registrar un check-in de recuperación, esta
    // tarjeta se quedaba mostrando "0 días con check-in" hasta
    // recargar la página entera - sin refreshKey no había forma de
    // decirle "hay datos nuevos" (mismo patrón que
    // ReadinessTrendCard/WeightTrendCard).
    vi.mocked(api.getPeriodicSummary).mockResolvedValue(_RESUMEN_VACIO);

    const { rerender } = render(<PeriodicSummaryCard userId={1} refreshKey={0} />);
    await waitFor(() => expect(api.getPeriodicSummary).toHaveBeenCalledTimes(1));

    rerender(<PeriodicSummaryCard userId={1} refreshKey={1} />);
    await waitFor(() => expect(api.getPeriodicSummary).toHaveBeenCalledTimes(2));
  });
});
