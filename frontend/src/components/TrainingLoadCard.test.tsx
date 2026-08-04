import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TrainingLoadCard } from "./TrainingLoadCard";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getTrainingLoad: vi.fn(),
    },
  };
});

describe("TrainingLoadCard", () => {
  beforeEach(() => {
    vi.mocked(api.getTrainingLoad).mockReset();
  });

  it("muestra el ACWR calculado cuando hay datos suficientes", async () => {
    vi.mocked(api.getTrainingLoad).mockResolvedValue({
      acute_avg_7d: 90,
      chronic_avg_28d: 75,
      acwr: 1.2,
      dias_con_dato_agudo: 7,
      dias_con_dato_cronico: 28,
      datos_suficientes: true,
    });

    render(<TrainingLoadCard userId={1} />);

    await waitFor(() => expect(screen.getByText("1.20")).toBeInTheDocument());
    expect(screen.queryByText(/historial insuficiente/i)).not.toBeInTheDocument();
  });

  it("muestra un aviso de historial insuficiente cuando datos_suficientes es false, sin ocultar el numero", async () => {
    vi.mocked(api.getTrainingLoad).mockResolvedValue({
      acute_avg_7d: 80,
      chronic_avg_28d: 80,
      acwr: 1.0,
      dias_con_dato_agudo: 3,
      dias_con_dato_cronico: 5,
      datos_suficientes: false,
    });

    render(<TrainingLoadCard userId={1} />);

    await waitFor(() => expect(screen.getByText("1.00")).toBeInTheDocument());
    expect(screen.getByText(/historial insuficiente/i)).toBeInTheDocument();
  });

  it("muestra un mensaje explicito cuando no hay ningun historial todavia (acwr null)", async () => {
    vi.mocked(api.getTrainingLoad).mockResolvedValue({
      acute_avg_7d: null,
      chronic_avg_28d: null,
      acwr: null,
      dias_con_dato_agudo: 0,
      dias_con_dato_cronico: 0,
      datos_suficientes: false,
    });

    render(<TrainingLoadCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/todavía no hay suficiente historial/i)).toBeInTheDocument()
    );
  });

  it("marca visualmente el ACWR de riesgo (>1.5) de forma distinta al normal", async () => {
    vi.mocked(api.getTrainingLoad).mockResolvedValue({
      acute_avg_7d: 150,
      chronic_avg_28d: 90,
      acwr: 1.67,
      dias_con_dato_agudo: 7,
      dias_con_dato_cronico: 28,
      datos_suficientes: true,
    });

    render(<TrainingLoadCard userId={1} />);

    await waitFor(() => expect(screen.getByText("1.67")).toBeInTheDocument());
    expect(screen.getByText("1.67")).toHaveClass("text-recovery-low");
  });

  it("expone el riesgo por texto, no solo por color (WCAG 1.4.1)", async () => {
    vi.mocked(api.getTrainingLoad).mockResolvedValue({
      acute_avg_7d: 150,
      chronic_avg_28d: 90,
      acwr: 1.67,
      dias_con_dato_agudo: 7,
      dias_con_dato_cronico: 28,
      datos_suficientes: true,
    });

    render(<TrainingLoadCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/riesgo alto/i)).toBeInTheDocument());
  });
});
