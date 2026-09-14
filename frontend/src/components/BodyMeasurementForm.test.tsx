import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BodyMeasurementForm } from "./BodyMeasurementForm";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      createBodyMeasurement: vi.fn(),
    },
  };
});

const MEDICION = {
  id: 1,
  fecha: "2026-09-14",
  peso_kg: 78.4,
  metodo: "manual" as const,
  bodyfat_pct_rango_min: null,
  bodyfat_pct_rango_max: null,
  muscle_kg: null,
  bone_kg: null,
  water_pct: null,
  bmi: null,
};

describe("BodyMeasurementForm", () => {
  beforeEach(() => {
    vi.mocked(api.createBodyMeasurement).mockReset();
  });

  it("guarda el peso del día y avisa al padre", async () => {
    vi.mocked(api.createBodyMeasurement).mockResolvedValue(MEDICION);
    const onSaved = vi.fn();
    const user = userEvent.setup();

    render(<BodyMeasurementForm userId={1} onSaved={onSaved} />);
    await user.type(screen.getByLabelText(/peso de hoy/i), "78.4");
    await user.click(screen.getByRole("button", { name: /guardar medición/i }));

    await waitFor(() =>
      expect(api.createBodyMeasurement).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ peso_kg: 78.4 })
      )
    );
    expect(onSaved).toHaveBeenCalledTimes(1);
    // La confirmación se anuncia (role="status"), no solo se pinta.
    expect(await screen.findByRole("status")).toHaveTextContent(/medición guardada/i);
  });

  it("no manda las medidas de cinta que se han dejado en blanco", async () => {
    vi.mocked(api.createBodyMeasurement).mockResolvedValue(MEDICION);
    const user = userEvent.setup();

    render(<BodyMeasurementForm userId={1} />);
    await user.type(screen.getByLabelText(/peso de hoy/i), "80");
    await user.click(screen.getByRole("button", { name: /guardar medición/i }));

    await waitFor(() => expect(api.createBodyMeasurement).toHaveBeenCalled());
    const enviado = vi.mocked(api.createBodyMeasurement).mock.calls[0][1];
    expect(enviado.cuello_cm).toBeUndefined();
    expect(enviado.cintura_cm).toBeUndefined();
    expect(enviado.cadera_cm).toBeUndefined();
  });

  it("presenta la grasa estimada como rango, nunca como un valor exacto", async () => {
    vi.mocked(api.createBodyMeasurement).mockResolvedValue({
      ...MEDICION,
      metodo: "navy",
      bodyfat_pct_rango_min: 14.2,
      bodyfat_pct_rango_max: 17.2,
    });
    const user = userEvent.setup();

    render(<BodyMeasurementForm userId={1} />);
    await user.type(screen.getByLabelText(/peso de hoy/i), "78.4");
    await user.click(screen.getByRole("button", { name: /guardar medición/i }));

    await waitFor(() => expect(screen.getByText("14.2–17.2 %")).toBeInTheDocument());
    expect(screen.getByText("rango, no un valor exacto")).toBeInTheDocument();
    // "Método: navy" era el valor crudo de la columna en pantalla.
    expect(screen.getByText(/método navy/i)).toBeInTheDocument();
  });

  it("muestra el error del servidor sin perder lo escrito", async () => {
    vi.mocked(api.createBodyMeasurement).mockRejectedValue(new ApiError(500, "base de datos caída"));
    const user = userEvent.setup();

    render(<BodyMeasurementForm userId={1} />);
    await user.type(screen.getByLabelText(/peso de hoy/i), "78.4");
    await user.click(screen.getByRole("button", { name: /guardar medición/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("base de datos caída"));
    // Un fallo del servidor no vacía el formulario: volver a teclearlo
    // todo es la peor forma de reintentar.
    expect(screen.getByLabelText(/peso de hoy/i)).toHaveValue(78.4);
  });
});
