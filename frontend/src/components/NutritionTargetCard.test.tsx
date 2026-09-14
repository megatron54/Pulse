import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NutritionTargetCard } from "./NutritionTargetCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getNutritionTarget: vi.fn(),
    },
  };
});

const OBJETIVO = {
  kcal_objetivo: 2450,
  proteina_g: 180,
  carbohidratos_g: 250,
  grasa_g: 70,
  fase_aplicada: "cut",
  deficit_pausado_por_guardrail: false,
};

describe("NutritionTargetCard", () => {
  beforeEach(() => {
    vi.mocked(api.getNutritionTarget).mockReset();
  });

  it("calcula el objetivo al entrar, sin que haya que pulsar un botón", async () => {
    // El defecto que señaló el usuario: un botón "Calcular macros de
    // hoy" que solo servía para pedir lo que la pantalla debería
    // mostrar sola.
    vi.mocked(api.getNutritionTarget).mockResolvedValue(OBJETIVO);

    render(<NutritionTargetCard userId={1} />);

    await waitFor(() => expect(screen.getByText("2450")).toBeInTheDocument());
    expect(api.getNutritionTarget).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: /calcular/i })).not.toBeInTheDocument();
  });

  it("escribe los gramos de cada macro y la fase en español", async () => {
    vi.mocked(api.getNutritionTarget).mockResolvedValue(OBJETIVO);

    render(<NutritionTargetCard userId={1} />);

    await waitFor(() => expect(screen.getByText("180 g")).toBeInTheDocument());
    expect(screen.getByText("250 g")).toBeInTheDocument();
    expect(screen.getByText("70 g")).toBeInTheDocument();
    // "Fase aplicada: cut" era el dato crudo del backend en pantalla.
    expect(screen.getByText("Déficit")).toBeInTheDocument();
    expect(screen.queryByText(/\bcut\b/)).not.toBeInTheDocument();
  });

  it("sin ninguna pesada, dice qué falta y lleva a registrarlo", async () => {
    vi.mocked(api.getNutritionTarget).mockRejectedValue(
      new ApiError(400, "No hay ninguna medición de peso registrada")
    );

    render(<NutritionTargetCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/hace falta tu peso/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("link", { name: /registrar mi peso/i })).toHaveAttribute(
      "href",
      "/cuerpo"
    );
    // Un 400 esperable no es un fallo que reintentar.
    expect(screen.queryByRole("button", { name: /reintentar/i })).not.toBeInTheDocument();
  });

  it("explica en palabras que el déficit está en pausa por el guardrail", async () => {
    vi.mocked(api.getNutritionTarget).mockResolvedValue({
      ...OBJETIVO,
      fase_aplicada: "maintenance",
      deficit_pausado_por_guardrail: true,
    });

    render(<NutritionTargetCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/tu déficit está en pausa/i)).toBeInTheDocument()
    );
    expect(screen.getByText("Mantenimiento")).toBeInTheDocument();
  });

  it("muestra un error reintentable si el cálculo falla por otra razón", async () => {
    vi.mocked(api.getNutritionTarget).mockRejectedValue(new ApiError(500, "caído"));

    render(<NutritionTargetCard userId={1} />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText("caído")).toBeInTheDocument();
  });
});
