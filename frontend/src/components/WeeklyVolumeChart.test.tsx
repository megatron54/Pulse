import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WeeklyVolumeChart } from "./WeeklyVolumeChart";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminWeeklyVolume: vi.fn(),
    },
  };
});

describe("WeeklyVolumeChart", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminWeeklyVolume).mockReset();
  });

  it("pide el volumen semanal con la metrica de distancia para running", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([]);
    render(<WeeklyVolumeChart userId={1} categoria="running" metrica="distancia" />);
    await waitFor(() =>
      expect(api.getGarminWeeklyVolume).toHaveBeenCalledWith(1, "running", 12)
    );
  });

  it("no renderiza nada si todas las semanas estan vacias (0 sesiones)", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([
      { semana_inicio: "2026-07-20", distancia_total_m: null, duracion_total_seg: null, num_sesiones: 0 },
      { semana_inicio: "2026-07-27", distancia_total_m: null, duracion_total_seg: null, num_sesiones: 0 },
    ]);
    const { container } = render(
      <WeeklyVolumeChart userId={1} categoria="running" metrica="distancia" />
    );
    await waitFor(() => expect(api.getGarminWeeklyVolume).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("muestra la tendencia de distancia total por semana (running/ciclismo)", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([
      { semana_inicio: "2026-07-27", distancia_total_m: 5000, duracion_total_seg: 1800, num_sesiones: 1 },
      { semana_inicio: "2026-08-03", distancia_total_m: 8000, duracion_total_seg: 3000, num_sesiones: 2 },
    ]);
    render(<WeeklyVolumeChart userId={1} categoria="running" metrica="distancia" />);
    await waitFor(() => expect(screen.getByText(/volumen semanal/i)).toBeInTheDocument());
    expect(screen.getByText(/8.0 km/i)).toBeInTheDocument();
  });

  it("muestra la tendencia de duracion total por semana (gimnasio)", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([
      { semana_inicio: "2026-08-03", distancia_total_m: null, duracion_total_seg: 3600, num_sesiones: 2 },
    ]);
    render(<WeeklyVolumeChart userId={1} categoria="gimnasio" metrica="duracion" />);
    await waitFor(() => expect(screen.getByText(/volumen semanal/i)).toBeInTheDocument());
    expect(screen.getByText(/60 min/i)).toBeInTheDocument();
  });

  it("no muestra ningun error visible si la peticion falla (bloque no critico)", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockRejectedValue(new ApiError(500, "caido"));
    const { container } = render(
      <WeeklyVolumeChart userId={1} categoria="running" metrica="distancia" />
    );
    await waitFor(() => expect(api.getGarminWeeklyVolume).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});
