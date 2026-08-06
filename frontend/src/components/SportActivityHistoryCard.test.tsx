import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Bike } from "lucide-react";
import { SportActivityHistoryCard } from "./SportActivityHistoryCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminActivities: vi.fn(),
    },
  };
});

describe("SportActivityHistoryCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminActivities).mockReset();
  });

  it("pide las actividades filtradas por la categoría indicada", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([]);
    render(
      <SportActivityHistoryCard
        userId={1}
        categoria="ciclismo"
        titulo="Ciclismo"
        icono={Bike}
        mensajeVacio="Sin actividades de ciclismo todavía."
      />
    );
    await waitFor(() =>
      expect(api.getGarminActivities).toHaveBeenCalledWith(1, 90, undefined, "ciclismo")
    );
  });

  it("muestra el mensaje vacío específico del deporte", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([]);
    render(
      <SportActivityHistoryCard
        userId={1}
        categoria="ciclismo"
        titulo="Ciclismo"
        icono={Bike}
        mensajeVacio="Sin actividades de ciclismo todavía."
      />
    );
    await waitFor(() =>
      expect(screen.getByText(/sin actividades de ciclismo todavía/i)).toBeInTheDocument()
    );
  });

  it("muestra un error si la petición falla", async () => {
    vi.mocked(api.getGarminActivities).mockRejectedValue(new ApiError(500, "caído"));
    render(
      <SportActivityHistoryCard
        userId={1}
        categoria="running"
        titulo="Running"
        icono={Bike}
        mensajeVacio="x"
      />
    );
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("muestra las actividades reales con distancia y duración cuando existen", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([
      {
        activity_id: "1",
        fecha: "2026-08-01",
        tipo: "running",
        duracion_seg: 1800,
        distancia_m: 5000,
        hr_avg: 150,
        hr_max: 172,
        training_effect: 3.2,
      },
    ]);

    render(
      <SportActivityHistoryCard
        userId={1}
        categoria="running"
        titulo="Running"
        icono={Bike}
        mensajeVacio="x"
      />
    );

    await waitFor(() => expect(screen.getByText(/5.0 km/i)).toBeInTheDocument());
    expect(screen.getByText(/30 min/i)).toBeInTheDocument();
  });

  it("muestra el resumen agregado de la ventana (número de sesiones)", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([
      {
        activity_id: "1",
        fecha: "2026-08-01",
        tipo: "strength_training",
        duracion_seg: 2400,
        distancia_m: null,
        hr_avg: 130,
        hr_max: 150,
        training_effect: 2.0,
      },
      {
        activity_id: "2",
        fecha: "2026-08-02",
        tipo: "strength_training",
        duracion_seg: 3000,
        distancia_m: null,
        hr_avg: 128,
        hr_max: 148,
        training_effect: 1.8,
      },
    ]);

    render(
      <SportActivityHistoryCard
        userId={1}
        categoria="gimnasio"
        titulo="Gimnasio"
        icono={Bike}
        mensajeVacio="x"
      />
    );

    await waitFor(() => expect(screen.getByText(/2 sesiones/i)).toBeInTheDocument());
  });
});
