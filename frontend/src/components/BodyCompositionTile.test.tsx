import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BodyCompositionTile } from "./BodyCompositionTile";
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

const base = {
  id: 1,
  fecha: "2026-08-10",
  peso_kg: 78.5,
  metodo: "manual" as const,
  bodyfat_pct_rango_min: null,
  bodyfat_pct_rango_max: null,
  muscle_kg: null,
  bone_kg: null,
  water_pct: null,
  bmi: null,
};

describe("BodyCompositionTile", () => {
  beforeEach(() => {
    vi.mocked(api.getBodyMeasurementHistory).mockReset();
  });

  it("no muestra nada si todavia no hay mediciones", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);
    const { container } = render(<BodyCompositionTile userId={1} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("no muestra nada si la ultima medicion es solo peso, sin composicion", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([base]);
    const { container } = render(<BodyCompositionTile userId={1} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("muestra un tile por cada campo de composicion presente en la ultima medicion", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      {
        ...base,
        metodo: "feelfit_bioimpedance" as unknown as "manual",
        bodyfat_pct_rango_min: 18.2,
        bodyfat_pct_rango_max: 18.2,
        muscle_kg: 34.1,
        bone_kg: 3.2,
        water_pct: 55.4,
        bmi: 24.1,
      },
    ]);

    render(<BodyCompositionTile userId={1} />);

    await waitFor(() => expect(screen.getByText(/% grasa/i)).toBeInTheDocument());
    expect(screen.getByText(/músculo/i)).toBeInTheDocument();
    expect(screen.getByText(/hueso/i)).toBeInTheDocument();
    expect(screen.getByText(/agua/i)).toBeInTheDocument();
    expect(screen.getByText(/bmi/i)).toBeInTheDocument();
  });

  it("muestra el % de grasa como rango cuando min y max difieren (metodo navy manual)", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...base, bodyfat_pct_rango_min: 15.0, bodyfat_pct_rango_max: 19.0 },
    ]);

    render(<BodyCompositionTile userId={1} />);

    await waitFor(() => expect(screen.getByText(/15\.0-19\.0%/)).toBeInTheDocument());
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockRejectedValue(new ApiError(500, "caido"));
    render(<BodyCompositionTile userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
