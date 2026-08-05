import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GarminActivitiesCard } from "./GarminActivitiesCard";
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

describe("GarminActivitiesCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminActivities).mockReset();
  });

  it("muestra un mensaje honesto de 'sin datos' cuando la lista viene vacía", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([]);
    render(<GarminActivitiesCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/sin actividades sincronizadas todavía/i)).toBeInTheDocument()
    );
  });

  it("muestra las actividades reales cuando la sincronización ya trajo datos", async () => {
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

    render(<GarminActivitiesCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/running/i)).toBeInTheDocument());
    expect(screen.getByText(/5.0 km/i)).toBeInTheDocument();
  });

  it("muestra un error si la petición falla", async () => {
    vi.mocked(api.getGarminActivities).mockRejectedValue(new ApiError(404, "no existe"));
    render(<GarminActivitiesCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
