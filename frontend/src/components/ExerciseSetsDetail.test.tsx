import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExerciseSetsDetail } from "./ExerciseSetsDetail";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminExerciseSets: vi.fn(),
    },
  };
});

describe("ExerciseSetsDetail", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminExerciseSets).mockReset();
  });

  it("muestra un estado de carga mientras llega la respuesta", () => {
    vi.mocked(api.getGarminExerciseSets).mockReturnValue(new Promise(() => {}));
    render(<ExerciseSetsDetail userId={1} activityId="1" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("muestra un error si la petición falla", async () => {
    vi.mocked(api.getGarminExerciseSets).mockRejectedValue(new ApiError(500, "caído"));
    render(<ExerciseSetsDetail userId={1} activityId="1" />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("muestra un estado vacío si la actividad no tiene series", async () => {
    vi.mocked(api.getGarminExerciseSets).mockResolvedValue([]);
    render(<ExerciseSetsDetail userId={1} activityId="1" />);
    await waitFor(() =>
      expect(screen.getByText(/no tiene series detalladas/i)).toBeInTheDocument()
    );
  });

  it("muestra las series con reps y peso, y etiqueta las de descanso", async () => {
    vi.mocked(api.getGarminExerciseSets).mockResolvedValue([
      {
        numero_serie: 0,
        tipo_serie: "ACTIVE",
        repeticiones: 10,
        peso_kg: 60.0,
        categoria_ejercicio: "BENCH_PRESS",
        duracion_seg: 45,
      },
      {
        numero_serie: 1,
        tipo_serie: "REST",
        repeticiones: null,
        peso_kg: null,
        categoria_ejercicio: null,
        duracion_seg: 90,
      },
    ]);

    render(<ExerciseSetsDetail userId={1} activityId="1" />);

    // El nombre va traducido: "BENCH_PRESS" o "bench press" es el dato
    // crudo del proveedor, no interfaz.
    await waitFor(() => expect(screen.getByText("Press de banca")).toBeInTheDocument());
    expect(screen.queryByText(/bench_press/i)).not.toBeInTheDocument();
    expect(screen.getByText("10 × 60 kg")).toBeInTheDocument();
    // La serie de descanso solo dice su duración: ni reps ni peso a 0.
    expect(screen.getByText("Descanso")).toBeInTheDocument();
    expect(screen.getByText("90 s")).toBeInTheDocument();
    expect(screen.queryByText(/0 reps/)).not.toBeInTheDocument();
  });

  it("distingue un peso real de 0 kg (ejercicio con peso corporal) de un peso ausente", async () => {
    vi.mocked(api.getGarminExerciseSets).mockResolvedValue([
      {
        numero_serie: 0,
        tipo_serie: "ACTIVE",
        repeticiones: 15,
        peso_kg: 0,
        categoria_ejercicio: "PUSH_UP",
        duracion_seg: 30,
      },
    ]);

    render(<ExerciseSetsDetail userId={1} activityId="1" />);

    await waitFor(() => expect(screen.getByText("15 × 0 kg")).toBeInTheDocument());
    expect(screen.getByText("Flexiones")).toBeInTheDocument();
  });

  it("muestra un guion, no un cero, cuando la serie no trae ningún dato", async () => {
    vi.mocked(api.getGarminExerciseSets).mockResolvedValue([
      {
        numero_serie: 0,
        tipo_serie: "ACTIVE",
        repeticiones: null,
        peso_kg: null,
        categoria_ejercicio: "SQUAT",
        duracion_seg: null,
      },
    ]);

    render(<ExerciseSetsDetail userId={1} activityId="1" />);

    await waitFor(() => expect(screen.getByText("Sentadilla")).toBeInTheDocument());
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
