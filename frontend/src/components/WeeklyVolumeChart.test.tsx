import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { escalaEje, WeeklyVolumeChart } from "./WeeklyVolumeChart";
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
    await waitFor(() => expect(screen.getByText("Volumen por semana")).toBeInTheDocument());
    // La última semana se escribe, no solo se dibuja: una curva sin
    // ninguna cifra obliga a pasar el cursor por encima (doctrina 5).
    // Se mira la cabecera y no la pantalla entera: "8.0 km" es también
    // una marca legítima del eje Y, así que buscarlo en todo el DOM
    // encontraba dos y el test fallaba de forma intermitente (recharts
    // solo dibuja las marcas cuando llega a medir el contenedor).
    const cabecera = screen.getByText("Volumen por semana").parentElement!;
    // La semana EN CURSO, y cuánto se sale de la anterior: "última
    // semana con datos" un lunes es la semana pasada, y una cifra sola
    // no dice si se está entrenando más o menos que de costumbre.
    expect(cabecera.textContent).toContain("Esta semana: 8.0 km, 3.0 km más que la anterior");
  });

  it("si esta semana no hay sesiones lo dice, en vez de dar la cifra de la semana pasada", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([
      { semana_inicio: "2026-07-20", distancia_total_m: 5000, duracion_total_seg: 1800, num_sesiones: 1 },
      { semana_inicio: "2026-07-27", distancia_total_m: 8000, duracion_total_seg: 3000, num_sesiones: 2 },
      { semana_inicio: "2026-08-03", distancia_total_m: null, duracion_total_seg: null, num_sesiones: 0 },
    ]);
    render(<WeeklyVolumeChart userId={1} categoria="running" metrica="distancia" />);

    await waitFor(() => expect(screen.getByText("Volumen por semana")).toBeInTheDocument());
    expect(
      screen.getByText("Esta semana todavía sin sesiones registradas.")
    ).toBeInTheDocument();
  });

  it("sin categoría pide el volumen de todos los deportes juntos", async () => {
    // La vista "Todas" de Sesiones: lo que se quiere saber ahí es
    // cuánto se ha entrenado en total, no cuánto de cada deporte.
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([]);
    render(<WeeklyVolumeChart userId={1} metrica="duracion" />);

    await waitFor(() =>
      expect(api.getGarminWeeklyVolume).toHaveBeenCalledWith(1, undefined, 12)
    );
  });

  it("muestra la tendencia de duracion total por semana (gimnasio)", async () => {
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([
      { semana_inicio: "2026-07-27", distancia_total_m: null, duracion_total_seg: 1800, num_sesiones: 1 },
      { semana_inicio: "2026-08-03", distancia_total_m: null, duracion_total_seg: 3600, num_sesiones: 2 },
    ]);
    render(<WeeklyVolumeChart userId={1} categoria="gimnasio" metrica="duracion" />);
    await waitFor(() => expect(screen.getByText("Volumen por semana")).toBeInTheDocument());
    expect(screen.getByText(/1 h/)).toBeInTheDocument();
  });

  it("no dibuja una tendencia con una sola semana de dato", async () => {
    // Un punto no es una tendencia: el área con dos vértices inventaba
    // una pendiente inexistente (hallazgo de la auditoría v3).
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([
      { semana_inicio: "2026-08-03", distancia_total_m: null, duracion_total_seg: 3600, num_sesiones: 2 },
    ]);
    const { container } = render(
      <WeeklyVolumeChart userId={1} categoria="gimnasio" metrica="duracion" />
    );
    await waitFor(() => expect(api.getGarminWeeklyVolume).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  describe("escalaEje", () => {
    it("rotula las semanas largas en horas, no en cientos de minutos", () => {
      // "Todas" suma los tres deportes: 13 h de semana salían como
      // "800 min" en el eje mientras la cabecera decía "13 h 20 min".
      expect(escalaEje([48000, 12000], "duracion")).toEqual({
        divisor: 3600,
        unidad: " h",
        decimales: 1,
      });
    });

    it("mantiene los minutos mientras las semanas son cortas", () => {
      // Dos sesiones de gimnasio a la semana son 80 min: en horas
      // serían "1.3 h", que se lee peor.
      expect(escalaEje([2400, 4800], "duracion")).toEqual({
        divisor: 60,
        unidad: " min",
        decimales: 0,
      });
    });

    it("la distancia siempre va en kilómetros", () => {
      expect(escalaEje([80000], "distancia")).toEqual({
        divisor: 1000,
        unidad: " km",
        decimales: 1,
      });
    });
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
