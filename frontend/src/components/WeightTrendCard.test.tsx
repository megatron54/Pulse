import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WeightTrendCard } from "./WeightTrendCard";
import { api, ApiError, type BodyMeasurement } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getBodyMeasurementHistory: vi.fn(),
    },
  };
});

const baseMedicion = {
  metodo: "manual" as const,
  bodyfat_pct_rango_min: null,
  bodyfat_pct_rango_max: null,
  muscle_kg: null,
  bone_kg: null,
  water_pct: null,
  bmi: null,
};

/** `userEvent` con temporizadores falsos: sin `advanceTimers` sus
 *  esperas internas no avanzan nunca y el clic se queda colgado. */
const clic = (elemento: Element) =>
  userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(elemento);

describe("WeightTrendCard", () => {
  beforeEach(() => {
    vi.mocked(api.getBodyMeasurementHistory).mockReset();
    // La tarjeta recorta las ventanas contra el día de hoy, así que sin
    // fijar el reloj estos casos cambiarían de resultado con el paso de
    // los meses (una pesada de agosto sale de los 90 días en noviembre).
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 8, 14));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("muestra la tendencia de peso deduplicada a una fila por día", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 },
      // Segunda medición del mismo día -> debe ganar (append-only, "la última fila del día gana")
      { ...baseMedicion, id: 2, fecha: "2026-08-01", peso_kg: 79.5 },
      { ...baseMedicion, id: 3, fecha: "2026-08-02", peso_kg: 79.2 },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByRole("img")).toBeInTheDocument());
    expect(screen.getByText((_, el) => el?.textContent === "79.2 kg")).toBeInTheDocument();
    expect(screen.getByText(/2 d[ií]as/i)).toBeInTheDocument();
  });

  it("con una sola pesada no dibuja gráfica ni inventa un cambio", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByText("1 día")).toBeInTheDocument());
    expect(screen.getByText(/hace falta una segunda pesada/i)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("escribe el signo del cambio, también cuando el peso sube", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 79.2 },
      { ...baseMedicion, id: 2, fecha: "2026-08-05", peso_kg: 80.1 },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByText("+0.9 kg")).toBeInTheDocument());
    expect(screen.getByText("de 79.2 a 80.1 kg")).toBeInTheDocument();
  });

  it("ordena por fecha aunque el historial llegue desordenado", async () => {
    // El endpoint promete orden ascendente, pero el delta y la gráfica
    // dependen de él: si cambiara, el cambio de peso saldría invertido.
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 2, fecha: "2026-08-05", peso_kg: 78.0 },
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80.0 },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByText("−2.0 kg")).toBeInTheDocument());
  });

  it("sin ninguna medición dice que no hay ninguna, y no ofrece ampliar la ventana", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/todavía no hay mediciones/i)).toBeInTheDocument());
    // Sin historial, ampliar la ventana no descubre nada: el hueco es
    // real y lo que toca decir es cómo apuntar la primera pesada.
    expect(screen.queryByRole("button", { name: "Ver todo el historial" })).not.toBeInTheDocument();
  });

  it("abre en la ventana más corta que tenga datos, no siempre en 90 días", async () => {
    // Hallazgo real: con 275 mediciones importadas de Feelfit (2022-2026)
    // pero ninguna de los últimos dos meses, la tarjeta abría en 90 días
    // y decía "Días con dato: 1 día" - el historial entero escondido
    // detrás de un selector que nadie sabía que había que tocar.
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2024-09-18", peso_kg: 82 },
      { ...baseMedicion, id: 2, fecha: "2026-07-01", peso_kg: 76.7 },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByRole("tab", { name: "Todo" })).toHaveAttribute("aria-selected", "true")
    );
    expect(screen.getByText("Cambio total")).toBeInTheDocument();
    expect(screen.getByText("−5.3 kg")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Peso" })).toBeInTheDocument();
  });

  it("si los datos recientes bastan, abre en 90 días y no en todo el historial", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2022-10-01", peso_kg: 90 },
      { ...baseMedicion, id: 2, fecha: "2026-08-20", peso_kg: 77 },
      { ...baseMedicion, id: 3, fecha: "2026-09-13", peso_kg: 76.4 },
    ]);

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByRole("tab", { name: "90 días" })).toHaveAttribute("aria-selected", "true")
    );
    // Y la ventana recorta de verdad: la pesada de 2022 no entra.
    expect(screen.getByText("2 días")).toBeInTheDocument();
    expect(screen.getByText("−0.6 kg")).toBeInTheDocument();
  });

  it("pide el historial una sola vez: cambiar de ventana recorta en el cliente", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-20", peso_kg: 77 },
      { ...baseMedicion, id: 2, fecha: "2026-09-13", peso_kg: 76.4 },
    ]);

    render(<WeightTrendCard userId={1} />);
    await waitFor(() => expect(screen.getByText("Cambio en 90 días")).toBeInTheDocument());
    expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(1, 3650);

    await clic(screen.getByRole("tab", { name: "1 año" }));

    await waitFor(() => expect(screen.getByText("Cambio en 12 meses")).toBeInTheDocument());
    expect(screen.getByText("Últimos 12 meses.")).toBeInTheDocument();
    expect(api.getBodyMeasurementHistory).toHaveBeenCalledTimes(1);
  });

  it("en una ventana elegida y vacía dice de cuándo es la última pesada y ofrece ampliar", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2024-09-18", peso_kg: 82 },
      { ...baseMedicion, id: 2, fecha: "2024-10-02", peso_kg: 81.4 },
    ]);

    render(<WeightTrendCard userId={1} />);
    await waitFor(() => expect(screen.getByText("Cambio total")).toBeInTheDocument());

    await clic(screen.getByRole("tab", { name: "90 días" }));

    await waitFor(() =>
      expect(screen.getByText(/ninguna pesada en esta ventana: la última es del 2 oct 2024/i)).toBeInTheDocument()
    );

    await clic(screen.getByRole("button", { name: "Ver todo el historial" }));

    await waitFor(() => expect(screen.getByRole("img", { name: "Peso" })).toBeInTheDocument());
  });

  it("muestra un mensaje de error si la petición falla", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockRejectedValue(new Error("boom"));

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/no se pudo cargar/i)).toBeInTheDocument()
    );
  });

  it("propaga el mensaje del servidor cuando el fallo es un ApiError", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockRejectedValue(
      new ApiError(500, "fallo interno del servidor")
    );

    render(<WeightTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText("fallo interno del servidor")).toBeInTheDocument()
    );
  });

  it("no actualiza el estado tras desmontar (evita el warning de setState en componente desmontado)", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    let resolverPromesa: (valor: BodyMeasurement[]) => void = () => {};
    vi.mocked(api.getBodyMeasurementHistory).mockReturnValue(
      new Promise((resolve) => {
        resolverPromesa = resolve;
      })
    );

    const { unmount } = render(<WeightTrendCard userId={1} />);
    unmount();
    resolverPromesa([{ ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 }]);
    await new Promise((r) => setTimeout(r, 0));

    const advertenciasDeSetStateEnDesmontado = consoleError.mock.calls.filter((args) =>
      String(args[0]).includes("unmounted")
    );
    expect(advertenciasDeSetStateEnDesmontado).toHaveLength(0);
    consoleError.mockRestore();
  });

  it("vuelve a pedir el historial cuando cambia userId", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    const { rerender } = render(<WeightTrendCard userId={1} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(1, 3650));

    rerender(<WeightTrendCard userId={2} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(2, 3650));

    expect(api.getBodyMeasurementHistory).toHaveBeenCalledTimes(2);
  });

  it("vuelve a pedir el historial cuando cambia refreshKey (tras guardar una medición nueva)", async () => {
    // Regresión de un hallazgo real de pruebas manuales con Playwright:
    // tras guardar una medición en BodyMeasurementForm, esta tarjeta
    // seguía mostrando "todavía no hay mediciones" hasta recargar la
    // página entera - no había forma de decirle "hay datos nuevos".
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    const { rerender } = render(<WeightTrendCard userId={1} refreshKey={0} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledTimes(1));

    rerender(<WeightTrendCard userId={1} refreshKey={1} />);
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledTimes(2));
  });
});
