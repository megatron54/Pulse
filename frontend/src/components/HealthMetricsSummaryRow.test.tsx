import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HealthMetricsSummaryRow } from "./HealthMetricsSummaryRow";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthHistory: vi.fn(),
    },
  };
});

describe("HealthMetricsSummaryRow", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
  });

  it("pide solo el dia de hoy (nunca todo el historico)", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<HealthMetricsSummaryRow userId={1} />);
    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 1));
  });

  it("no muestra nada si todavia no hay datos de hoy", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    const { container } = render(<HealthMetricsSummaryRow userId={1} />);
    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("muestra el valor de hoy de cada metrica con datos, y omite las que no tienen ninguno", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-10",
        hrv_value: 49,
        hrv_status: "NONE",
        body_battery_am: 77,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: null,
        resting_hr: 52,
        vo2max: null,
      },
    ]);

    render(<HealthMetricsSummaryRow userId={1} />);

    await waitFor(() => expect(screen.getByText(/vfc/i)).toBeInTheDocument());
    expect(screen.getByText(/body battery/i)).toBeInTheDocument();
    expect(screen.getByText(/sueño/i)).toBeInTheDocument();
    expect(screen.getByText(/fc reposo/i)).toBeInTheDocument();
    expect(screen.queryByText(/estrés/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/vo2max/i)).not.toBeInTheDocument();
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getGarminHealthHistory).mockRejectedValue(new ApiError(500, "caido"));
    render(<HealthMetricsSummaryRow userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
