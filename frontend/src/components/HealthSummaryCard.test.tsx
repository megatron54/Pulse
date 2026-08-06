import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HealthSummaryCard } from "./HealthSummaryCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthHistory: vi.fn(),
      // CoachNarrativeBlock (Épica H) llama a esto internamente - se
      // mockea aquí también para que los tests no disparen una
      // petición de red real de fondo en jsdom.
      getGarminHealthNarrative: vi.fn().mockResolvedValue({ text: null, source: null }),
    },
  };
});

describe("HealthSummaryCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
    vi.mocked(api.getGarminHealthNarrative).mockReset();
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({ text: null, source: null });
  });

  it("pide solo los últimos 7 días (resumen, no el histórico completo)", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<HealthSummaryCard userId={1} />);
    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 7));
  });

  it("muestra un mensaje honesto de 'sin datos' cuando el historial viene vacío", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<HealthSummaryCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/todavía no hay datos de recovery sincronizados/i)).toBeInTheDocument()
    );
  });

  it("muestra un error si la petición falla", async () => {
    vi.mocked(api.getGarminHealthHistory).mockRejectedValue(new ApiError(404, "no existe"));
    render(<HealthSummaryCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("muestra el valor de hoy de cada métrica con datos, y omite las que no tienen ninguno", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
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

    render(<HealthSummaryCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/vfc/i)).toBeInTheDocument());
    expect(screen.getByText(/body battery/i)).toBeInTheDocument();
    expect(screen.getByText(/sueño/i)).toBeInTheDocument();
    expect(screen.queryByText(/estrés/i)).not.toBeInTheDocument();
  });

  it("enlaza al histórico completo en /salud", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: 49,
        hrv_status: null,
        body_battery_am: null,
        training_readiness: null,
        sleep_score: null,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
      },
    ]);

    render(<HealthSummaryCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByRole("link", { name: /ver histórico completo/i })).toHaveAttribute(
        "href",
        "/salud"
      )
    );
  });

  it("el botón de reintento vuelve a pedir el historial tras un error", async () => {
    vi.mocked(api.getGarminHealthHistory).mockRejectedValueOnce(new ApiError(500, "caído"));
    render(<HealthSummaryCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    vi.mocked(api.getGarminHealthHistory).mockResolvedValueOnce([]);
    screen.getByRole("button", { name: /reintentar/i }).click();

    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.getByText(/todavía no hay datos de recovery sincronizados/i)).toBeInTheDocument()
    );
  });
});
