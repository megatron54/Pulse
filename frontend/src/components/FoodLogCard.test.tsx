import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FoodLogCard } from "./FoodLogCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getFoodLog: vi.fn(),
      saveWgerToken: vi.fn(),
      searchIngredients: vi.fn(),
      createFoodLogEntry: vi.fn(),
    },
  };
});

describe("FoodLogCard", () => {
  beforeEach(() => {
    vi.mocked(api.getFoodLog).mockReset();
    vi.mocked(api.saveWgerToken).mockReset();
    vi.mocked(api.searchIngredients).mockReset();
    vi.mocked(api.createFoodLogEntry).mockReset();
  });

  it("muestra el formulario para conectar wger si no hay credenciales (404)", async () => {
    vi.mocked(api.getFoodLog).mockRejectedValue(new ApiError(404, "sin credenciales de wger"));

    render(<FoodLogCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/conecta tu cuenta de wger/i)).toBeInTheDocument()
    );
    expect(screen.getByLabelText(/token de wger/i)).toBeInTheDocument();
  });

  it("tras guardar el token, vuelve a cargar el diario del día", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getFoodLog)
      .mockRejectedValueOnce(new ApiError(404, "sin credenciales"))
      .mockResolvedValueOnce({
        entradas: [],
        kcal_total: 0,
        proteina_g_total: 0,
        carbohidratos_g_total: 0,
        grasa_g_total: 0,
        entradas_omitidas: 0,
      });
    vi.mocked(api.saveWgerToken).mockResolvedValue(undefined);

    render(<FoodLogCard userId={1} />);
    await waitFor(() => expect(screen.getByLabelText(/token de wger/i)).toBeInTheDocument());

    await user.type(screen.getByLabelText(/token de wger/i), "tok-abc");
    await user.click(screen.getByRole("button", { name: /conectar/i }));

    await waitFor(() => expect(api.saveWgerToken).toHaveBeenCalledWith(1, "tok-abc"));
    await waitFor(() => expect(api.getFoodLog).toHaveBeenCalledTimes(2));
  });

  it("muestra el diario del día con sus totales cuando ya hay credenciales", async () => {
    vi.mocked(api.getFoodLog).mockResolvedValue({
      entradas: [
        {
          ingredient_id: 2,
          nombre: "Pollo",
          amount_grams: 150,
          kcal: 247.5,
          proteina_g: 46.5,
          carbohidratos_g: 0,
          grasa_g: 5.4,
        },
      ],
      kcal_total: 247.5,
      proteina_g_total: 46.5,
      carbohidratos_g_total: 0,
      grasa_g_total: 5.4,
      entradas_omitidas: 0,
    });

    render(<FoodLogCard userId={1} />);

    await waitFor(() => expect(screen.getByText("Pollo")).toBeInTheDocument());
    expect(screen.getByText(/248 kcal/i)).toBeInTheDocument();
  });

  it("busca ingredientes y registra uno, refrescando el diario", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getFoodLog).mockResolvedValue({
      entradas: [],
      kcal_total: 0,
      proteina_g_total: 0,
      carbohidratos_g_total: 0,
      grasa_g_total: 0,
      entradas_omitidas: 0,
    });
    vi.mocked(api.searchIngredients).mockResolvedValue([
      {
        id: 2,
        nombre: "Pollo",
        kcal_100g: 165,
        proteina_100g_g: 31,
        carbohidratos_100g_g: 0,
        grasa_100g_g: 3.6,
      },
    ]);
    vi.mocked(api.createFoodLogEntry).mockResolvedValue(undefined);

    render(<FoodLogCard userId={1} />);
    await waitFor(() => expect(screen.getByPlaceholderText(/buscar alimento/i)).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/buscar alimento/i), "pollo");
    await user.click(screen.getByRole("button", { name: /buscar/i }));

    await waitFor(() => expect(screen.getByText("Pollo")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /añadir/i }));

    await waitFor(() =>
      expect(api.createFoodLogEntry).toHaveBeenCalledWith(1, 2, expect.any(Number))
    );
  });

  it("avisa si hay entradas omitidas por ingredientes no resueltos", async () => {
    vi.mocked(api.getFoodLog).mockResolvedValue({
      entradas: [],
      kcal_total: 0,
      proteina_g_total: 0,
      carbohidratos_g_total: 0,
      grasa_g_total: 0,
      entradas_omitidas: 2,
    });

    render(<FoodLogCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/2.*no se pudieron cargar/i)).toBeInTheDocument());
  });
});
