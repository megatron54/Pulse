import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NutritionPlanCard } from "./NutritionPlanCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getActiveNutritionPlan: vi.fn(),
      getNutritionPhaseRecommendation: vi.fn(),
      createNutritionPlan: vi.fn(),
    },
  };
});

describe("NutritionPlanCard", () => {
  beforeEach(() => {
    vi.mocked(api.getActiveNutritionPlan).mockReset();
    vi.mocked(api.getNutritionPhaseRecommendation).mockReset();
    vi.mocked(api.createNutritionPlan).mockReset();
  });

  it("sin plan activo, muestra la recomendacion del sistema (nunca la aplica sola)", async () => {
    vi.mocked(api.getActiveNutritionPlan).mockResolvedValue(null);
    vi.mocked(api.getNutritionPhaseRecommendation).mockResolvedValue({
      fase_recomendada: "maintenance",
      accion: "nuevo_plan_sugerido",
      motivo: "Sin plan activo - mantenimiento es el punto de partida seguro.",
      semanas_sugeridas: 4,
    });

    render(<NutritionPlanCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText("Sin plan activo todavía.")).toBeInTheDocument()
    );
    expect(api.createNutritionPlan).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeInTheDocument();
  });

  it("con plan activo vigente, muestra la fase y los dias restantes", async () => {
    vi.mocked(api.getActiveNutritionPlan).mockResolvedValue({
      plan: { id: 1, fase: "cut", fecha_inicio: "2026-08-01", semanas_duracion: 8, motivo: null, activo: true },
      fecha_fin: "2026-09-26",
      dias_restantes: 30,
      expirado: false,
    });
    vi.mocked(api.getNutritionPhaseRecommendation).mockResolvedValue({
      fase_recomendada: "cut",
      accion: "sin_cambios",
      motivo: "Tu plan de cut sigue en curso - 30 días restantes.",
      semanas_sugeridas: null,
    });

    render(<NutritionPlanCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/déficit/i)).toBeInTheDocument());
    expect(screen.getByText(/30/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirmar/i })).not.toBeInTheDocument();
  });

  it("confirmar la recomendacion crea el plan con los datos sugeridos", async () => {
    vi.mocked(api.getActiveNutritionPlan).mockResolvedValue(null);
    vi.mocked(api.getNutritionPhaseRecommendation).mockResolvedValue({
      fase_recomendada: "maintenance",
      accion: "nuevo_plan_sugerido",
      motivo: "Sin plan activo - mantenimiento es el punto de partida seguro.",
      semanas_sugeridas: 4,
    });
    vi.mocked(api.createNutritionPlan).mockResolvedValue({
      id: 1,
      fase: "maintenance",
      fecha_inicio: "2026-08-10",
      semanas_duracion: 4,
      motivo: "Sin plan activo - mantenimiento es el punto de partida seguro.",
      activo: true,
    });
    const user = userEvent.setup();

    render(<NutritionPlanCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /confirmar/i })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /confirmar/i }));

    await waitFor(() =>
      expect(api.createNutritionPlan).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ fase: "maintenance", semanas_duracion: 4 })
      )
    );
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getActiveNutritionPlan).mockRejectedValue(new ApiError(500, "caído"));
    vi.mocked(api.getNutritionPhaseRecommendation).mockResolvedValue({
      fase_recomendada: "maintenance",
      accion: "sin_cambios",
      motivo: "x",
      semanas_sugeridas: null,
    });

    render(<NutritionPlanCard userId={1} />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
