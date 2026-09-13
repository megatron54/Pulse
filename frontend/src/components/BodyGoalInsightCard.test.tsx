import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BodyGoalInsightCard } from "./BodyGoalInsightCard";
import { api, ApiError, type User } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getUser: vi.fn(),
      getBodyMeasurementHistory: vi.fn(),
    },
  };
});

const baseMedicion = {
  metodo: "manual" as const,
  bodyfat_pct_rango_min: null,
  bodyfat_pct_rango_max: null,
  muscle_kg: null,
  bone_kg: null,
  water_pct: null,
  bmi: null,
};

const usuarioBase: User = {
  id: 1,
  nombre: "Miguel",
  altura_cm: 176,
  fecha_nacimiento: "2002-11-28",
  sexo: "M",
  fase_peso_actual: "cut",
};

describe("BodyGoalInsightCard", () => {
  beforeEach(() => {
    vi.mocked(api.getUser).mockReset();
    vi.mocked(api.getBodyMeasurementHistory).mockReset();
  });

  it("muestra 'en línea' cuando el peso baja durante un cut", async () => {
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 },
      { ...baseMedicion, id: 2, fecha: "2026-08-20", peso_kg: 78 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/en línea/i)).toBeInTheDocument());
  });

  it("muestra un aviso de desviación cuando el peso sube durante un cut", async () => {
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 78 },
      { ...baseMedicion, id: 2, fecha: "2026-08-20", peso_kg: 80 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/no está siguiendo la dirección esperada/i)).toBeInTheDocument());
  });

  it("no inventa una tendencia con una sola medición ('unknown is not zero')", async () => {
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/no hay suficientes mediciones/i)).toBeInTheDocument()
    );
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getUser).mockRejectedValue(new ApiError(500, "caido"));
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
