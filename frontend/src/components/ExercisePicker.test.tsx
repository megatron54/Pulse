import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExercisePicker } from "./ExercisePicker";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getExerciseCategories: vi.fn(),
      searchExercises: vi.fn(),
    },
  };
});

describe("ExercisePicker", () => {
  beforeEach(() => {
    vi.mocked(api.getExerciseCategories).mockReset();
    vi.mocked(api.searchExercises).mockReset();
    vi.mocked(api.searchExercises).mockResolvedValue([]);
  });

  it("carga y muestra las categorías al montar", async () => {
    vi.mocked(api.getExerciseCategories).mockResolvedValue([
      { id: 10, name: "Abs" },
      { id: 9, name: "Legs" },
    ]);

    render(<ExercisePicker />);

    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    expect(
      screen.getByRole("combobox", { name: "Categoría de ejercicios" })
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Abs" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Legs" })).toBeInTheDocument();
  });

  it("al elegir una categoría, busca y muestra sus ejercicios", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getExerciseCategories).mockResolvedValue([{ id: 9, name: "Legs" }]);
    vi.mocked(api.searchExercises).mockResolvedValue([
      { id: 43, nombre: "Barbell Hack Squats", categoria: "Legs", equipamiento: ["Barbell"] },
    ]);

    render(<ExercisePicker />);

    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    await user.selectOptions(screen.getByRole("combobox"), "Legs");

    await waitFor(() =>
      expect(screen.getByText("Barbell Hack Squats")).toBeInTheDocument()
    );
    expect(screen.getByText("Barbell")).toBeInTheDocument();
    expect(api.searchExercises).toHaveBeenCalledWith(9, 2, 50);
  });

  it("muestra un mensaje si una categoría no tiene ejercicios", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getExerciseCategories).mockResolvedValue([{ id: 9, name: "Legs" }]);
    vi.mocked(api.searchExercises).mockResolvedValue([]);

    render(<ExercisePicker />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    await user.selectOptions(screen.getByRole("combobox"), "Legs");

    await waitFor(() =>
      expect(screen.getByText(/no se encontraron ejercicios/i)).toBeInTheDocument()
    );
  });

  it("muestra un error si wger no responde", async () => {
    vi.mocked(api.getExerciseCategories).mockRejectedValue(
      new ApiError(502, "wger devolvió un error")
    );

    render(<ExercisePicker />);

    await waitFor(() =>
      expect(screen.getByText("wger devolvió un error")).toBeInTheDocument()
    );
  });
});
