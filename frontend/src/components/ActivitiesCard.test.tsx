import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ActivitiesCard } from "./ActivitiesCard";
import { api, ApiError, type GarminActivity } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminActivities: vi.fn(),
      getGarminExerciseSets: vi.fn(),
      getGarminWeeklyVolume: vi.fn(),
      getGarminSportNarrative: vi.fn(),
      getGarminHealthNarrative: vi.fn(),
    },
  };
});

const CARRERA: GarminActivity = {
  activity_id: "1",
  fecha: "2026-08-01",
  tipo: "running",
  duracion_seg: 1800,
  distancia_m: 5000,
  hr_avg: 150,
  hr_max: 172,
  training_effect: 3.2,
};

const FUERZA: GarminActivity = {
  activity_id: "2",
  fecha: "2026-08-02",
  tipo: "strength_training",
  duracion_seg: 2400,
  distancia_m: null,
  hr_avg: 130,
  hr_max: 150,
  training_effect: 2.0,
};

describe("ActivitiesCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminActivities).mockReset();
    vi.mocked(api.getGarminExerciseSets).mockReset();
    vi.mocked(api.getGarminWeeklyVolume).mockResolvedValue([]);
    vi.mocked(api.getGarminSportNarrative).mockResolvedValue({ text: null, source: null });
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({ text: null, source: null });
  });

  it("muestra un mensaje honesto cuando no hay sesiones sincronizadas", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([]);
    render(<ActivitiesCard userId={1} titulo="Todas las sesiones" mensajeVacio="Sin sesiones todavía." />);
    await waitFor(() => expect(screen.getByText("Sin sesiones todavía.")).toBeInTheDocument());
  });

  it("pide las actividades filtradas por la categoría indicada", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([]);
    render(
      <ActivitiesCard userId={1} categoria="ciclismo" titulo="Ciclismo" mensajeVacio="Sin salidas." />
    );
    await waitFor(() =>
      expect(api.getGarminActivities).toHaveBeenCalledWith(1, 90, undefined, "ciclismo")
    );
  });

  it("presenta las sesiones en una tabla con cabeceras escritas una sola vez", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([CARRERA]);
    render(<ActivitiesCard userId={1} titulo="Carrera" mensajeVacio="x" />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(screen.getAllByRole("columnheader", { name: "Duración" })).toHaveLength(1);
    expect(screen.getByText("5.0 km")).toBeInTheDocument();
    expect(screen.getByText("30 min")).toBeInTheDocument();
  });

  it("traduce el tipo crudo de Garmin y la fecha ISO", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([FUERZA]);
    render(<ActivitiesCard userId={1} titulo="Gimnasio" mensajeVacio="x" />);

    await waitFor(() => expect(screen.getByText("Fuerza")).toBeInTheDocument());
    expect(screen.queryByText(/strength_training|strength training/i)).not.toBeInTheDocument();
    expect(screen.getByText("2 ago")).toBeInTheDocument();
    expect(screen.queryByText("2026-08-02")).not.toBeInTheDocument();
  });

  it("pone la fecha bajo el nombre de la sesión, sin una columna propia", async () => {
    // Cinco columnas no caben a 390px: al nombre le quedaban 40px y
    // "Natación en piscina" salía en tres líneas (doctrina 4).
    vi.mocked(api.getGarminActivities).mockResolvedValue([CARRERA]);
    render(<ActivitiesCard userId={1} titulo="Carrera" mensajeVacio="x" />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(screen.queryByRole("columnheader", { name: "Fecha" })).not.toBeInTheDocument();
    // Pero la fecha sigue ahí, en la misma celda que el nombre.
    const [primeraCelda] = screen.getAllByRole("cell");
    expect(primeraCelda.textContent).toBe("Carrera1 ago");
    // Y la cabecera del pulso es de una palabra, no "FC media".
    expect(screen.getByRole("columnheader", { name: "Pulso" })).toBeInTheDocument();
  });

  it("no inventa un 0.0 km en sesiones sin distancia: omite la columna entera", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([FUERZA]);
    render(<ActivitiesCard userId={1} categoria="gimnasio" titulo="Gimnasio" mensajeVacio="x" />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(screen.queryByText(/0\.0 km/)).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Distancia" })).not.toBeInTheDocument();
  });

  it("mantiene la columna de distancia si alguna sesión de la lista la tiene", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([CARRERA, FUERZA]);
    render(<ActivitiesCard userId={1} titulo="Todas" mensajeVacio="x" />);

    await waitFor(() =>
      expect(screen.getByRole("columnheader", { name: "Distancia" })).toBeInTheDocument()
    );
    // La sesión de fuerza muestra la ausencia como tal, no como cero.
    expect(screen.getByLabelText("sin dato")).toBeInTheDocument();
  });

  it("expande y colapsa el detalle de series de gimnasio con un botón accesible", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([FUERZA]);
    vi.mocked(api.getGarminExerciseSets).mockResolvedValue([
      {
        numero_serie: 0,
        tipo_serie: "ACTIVE",
        repeticiones: 10,
        peso_kg: 60.0,
        categoria_ejercicio: "BENCH_PRESS",
        duracion_seg: 45,
      },
    ]);

    render(<ActivitiesCard userId={1} categoria="gimnasio" titulo="Gimnasio" mensajeVacio="x" />);

    const boton = await screen.findByRole("button", { name: "Fuerza" });
    expect(boton).toHaveAttribute("aria-expanded", "false");

    await userEvent.click(boton);
    await waitFor(() => expect(screen.getByText("Press de banca")).toBeInTheDocument());
    expect(boton).toHaveAttribute("aria-expanded", "true");

    await userEvent.click(boton);
    await waitFor(() => expect(screen.queryByText("Press de banca")).not.toBeInTheDocument());
  });

  it("no ofrece expandir series en sesiones que no son de gimnasio", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([CARRERA]);
    render(<ActivitiesCard userId={1} categoria="running" titulo="Carrera" mensajeVacio="x" />);

    await waitFor(() => expect(screen.getByText("Carrera", { selector: "td" })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Carrera" })).not.toBeInTheDocument();
  });

  it("resuelve el plural del recuento de sesiones", async () => {
    vi.mocked(api.getGarminActivities).mockResolvedValue([CARRERA]);
    render(<ActivitiesCard userId={1} titulo="Carrera" mensajeVacio="x" />);
    await waitFor(() => expect(screen.getByText(/1 sesión en 90 días/)).toBeInTheDocument());
  });

  it("muestra un error reintentable si la petición falla", async () => {
    vi.mocked(api.getGarminActivities).mockRejectedValue(new ApiError(500, "caído"));
    render(<ActivitiesCard userId={1} titulo="Carrera" mensajeVacio="x" />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
  });
});
