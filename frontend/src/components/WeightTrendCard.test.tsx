import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WeightTrendCard } from "./WeightTrendCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getBodyMeasurementHistory: vi.fn(),
    },
  };
});

describe("WeightTrendCard", () => {
  beforeEach(() => {
    vi.mocked(api.getBodyMeasurementHistory).mockReset();
  });

  it("muestra la tendencia de peso deduplicada a una fila por día", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", peso_kg: 80, metodo: "manual", bodyfat_pct_rango_min: null, bodyfat_pct_rango_max: null },
      // Segunda medición del mismo día -> debe ganar (append-only, "la última fila del día gana")
      { id: 2, fecha: "2026-08-01", peso_kg: 79.5, metodo: "manual", bodyfat_pct_rango_min: null, bodyfat_pct_rango_max: null },
      { id: 3, fecha: "2026-08-02", peso_kg: 79.2, metodo: "manual", bodyfat_pct_rango_min: null, bodyfat_pct_rango_max: null },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByRole("img")).toBeInTheDocument());
    expect(screen.getByText(/79.2 kg/)).toBeInTheDocument();
    expect(screen.getByText(/2 d[ií]as/i)).toBeInTheDocument();
  });

  it("muestra un mensaje cuando no hay mediciones todavía", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/todavía no hay mediciones/i)).toBeInTheDocument()
    );
  });

  it("muestra un mensaje de error si la petición falla", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockRejectedValue(new Error("boom"));

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/no se pudo cargar/i)).toBeInTheDocument()
    );
  });

  it("propaga el mensaje del servidor cuando el fallo es un ApiError", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockRejectedValue(
      new ApiError(500, "fallo interno del servidor")
    );

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText("fallo interno del servidor")).toBeInTheDocument()
    );
  });

  it("no actualiza el estado tras desmontar (evita el warning de setState en componente desmontado)", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    let resolverPromesa: (valor: unknown) => void = () => {};
    vi.mocked(api.getBodyMeasurementHistory).mockReturnValue(
      new Promise((resolve) => {
        resolverPromesa = resolve;
      })
    );

    const { unmount } = render(<WeightTrendCard userId={1} />);
    unmount();
    resolverPromesa([
      { id: 1, fecha: "2026-08-01", peso_kg: 80, metodo: "manual", bodyfat_pct_rango_min: null, bodyfat_pct_rango_max: null },
    ]);
    await new Promise((r) => setTimeout(r, 0));

    const advertenciasDeSetStateEnDesmontado = consoleError.mock.calls.filter((args) =>
      String(args[0]).includes("unmounted")
    );
    expect(advertenciasDeSetStateEnDesmontado).toHaveLength(0);
    consoleError.mockRestore();
  });

  it("vuelve a pedir el historial cuando cambia userId", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    const { rerender } = render(<WeightTrendCard userId={1} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(1, 90));

    rerender(<WeightTrendCard userId={2} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(2, 90));

    expect(api.getBodyMeasurementHistory).toHaveBeenCalledTimes(2);
  });
});
