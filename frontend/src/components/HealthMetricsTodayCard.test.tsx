import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HealthMetricsTodayCard } from "./HealthMetricsTodayCard";
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

describe("HealthMetricsTodayCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
  });

  it("pide solo el dia de hoy (nunca todo el historico)", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<HealthMetricsTodayCard userId={1} />);
    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 1));
  });

  it("no muestra nada si todavia no hay datos de hoy", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    const { container } = render(<HealthMetricsTodayCard userId={1} />);
    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("dice de qué día son las cifras, no las presenta como 'hoy' a ciegas", async () => {
    // `fechaRelativa` compara contra el reloj real: sin fijarlo, este
    // assert dejaría de valer mañana. `shouldAdvanceTime` mantiene
    // `waitFor` funcionando.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 8, 14));
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-09-14",
        hrv_value: 49,
        hrv_status: "NONE",
        body_battery_am: 77,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: null,
        resting_hr: 52,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<HealthMetricsTodayCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/última medida: hoy/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: /métricas de recuperación/i })).toBeInTheDocument();
    vi.useRealTimers();
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
        pasos: null,
      deep_sleep_seg: null,
      light_sleep_seg: null,
      rem_sleep_seg: null,
      awake_sleep_seg: null,
    },
    ]);

    render(<HealthMetricsTodayCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/vfc/i)).toBeInTheDocument());
    expect(screen.getByText(/body battery/i)).toBeInTheDocument();
    expect(screen.getByText(/sueño/i)).toBeInTheDocument();
    expect(screen.getByText(/pulso reposo/i)).toBeInTheDocument();
    expect(screen.queryByText(/estrés/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/vo2max/i)).not.toBeInTheDocument();
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getGarminHealthHistory).mockRejectedValue(new ApiError(500, "caido"));
    render(<HealthMetricsTodayCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
