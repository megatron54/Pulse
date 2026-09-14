import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BodyGoalInsightCard } from "./BodyGoalInsightCard";
import { api, ApiError, type User } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getUser: vi.fn(),
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

const usuarioBase: User = {
  id: 1,
  nombre: "Miguel",
  altura_cm: 176,
  fecha_nacimiento: "2002-11-28",
  sexo: "M",
  fase_peso_actual: "cut",
};

describe("BodyGoalInsightCard", () => {
  beforeEach(() => {
    vi.mocked(api.getUser).mockReset();
    vi.mocked(api.getBodyMeasurementHistory).mockReset();
  });

  it("muestra 'en línea' cuando el peso baja durante un cut", async () => {
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 },
      { ...baseMedicion, id: 2, fecha: "2026-08-20", peso_kg: 78 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() => expect(screen.getByText("Vas en línea con tu objetivo")).toBeInTheDocument());
    // El cambio se escribe con signo y con las fechas de la ventana
    // real, no como un porcentaje suelto sin contexto.
    expect(screen.getByText("−2.5 %")).toBeInTheDocument();
    // Regex y no cadena exacta: `fechaCorta` añade el año cuando la
    // fecha no es del año en curso, y estos datos envejecen.
    expect(screen.getByText(/del 1 ago.* al 20 ago/)).toBeInTheDocument();
    // La fase se dice en español: "cut" es el valor del backend.
    expect(screen.getByText("Déficit")).toBeInTheDocument();
    expect(screen.queryByText(/cut/)).not.toBeInTheDocument();
  });

  it("muestra un aviso de desviación cuando el peso sube durante un cut", async () => {
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 78 },
      { ...baseMedicion, id: 2, fecha: "2026-08-20", peso_kg: 80 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/no va en la dirección esperada/i)).toBeInTheDocument());
  });

  it("no inventa una tendencia con una sola medición ('unknown is not zero')", async () => {
    // Pesada de anteayer: reciente, así que lo que falta de verdad es
    // una segunda pesada y no que el usuario vuelva a la báscula.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 7, 3));
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-08-01", peso_kg: 80 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/solo hay una pesada en los 30 días/i)).toBeInTheDocument()
    );
    vi.useRealTimers();
  });

  it("con una sola pesada y vieja, dice cuánto hace y pide volver a pesarse", async () => {
    // Caso real del usuario: 275 pesadas de Feelfit, la última del 1 de
    // julio. Decir "solo hay una pesada en los 30 días hasta el 1 jul"
    // era cierto y a la vez inútil: el problema es que hace 75 días que
    // no se pesa, y eso es lo accionable (doctrina 7).
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 8, 14));
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...baseMedicion, id: 1, fecha: "2026-07-01", peso_kg: 76.7 },
    ]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/tu última pesada es del 1 jul, hace 75 días/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/vuelve a pesarte/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("sin ninguna pesada lo dice así, sin hablar de una ventana vacía", async () => {
    vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/todavía no hay pesadas registradas/i)).toBeInTheDocument()
    );
  });

  describe("ventana anclada a la última pesada", () => {
    beforeEach(() => {
      // El comportamiento depende de "hoy": sin fijarlo, estos tests
      // cambiarían de resultado con el paso del tiempo.
      vi.useFakeTimers({ shouldAdvanceTime: true });
      vi.setSystemTime(new Date(2026, 8, 14));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("compara las últimas pesadas aunque sean de hace meses, y avisa de que son viejas", async () => {
      // Caso real: 247 días con dato pero la última pesada es del 1 de
      // julio. Con la ventana contada desde hoy la tarjeta quedaba
      // muerta ("hacen falta pesadas en dos días distintos").
      vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
      vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
        { ...baseMedicion, id: 1, fecha: "2025-10-05", peso_kg: 82 },
        { ...baseMedicion, id: 2, fecha: "2026-06-10", peso_kg: 78 },
        { ...baseMedicion, id: 3, fecha: "2026-07-01", peso_kg: 76.7 },
      ]);

      render(<BodyGoalInsightCard userId={1} />);

      await waitFor(() => expect(screen.getByText("−1.7 %")).toBeInTheDocument());
      expect(screen.getByText(/del 10 jun al 1 jul/)).toBeInTheDocument();
      // La pesada de 2025 está fuera de la ventana de 30 días: si
      // entrase, el cambio sería de -6.5 %.
      expect(screen.getByText(/hasta el 1 jul/)).toBeInTheDocument();
      expect(screen.getByText(/hace 75 días/)).toBeInTheDocument();
    });

    it("no avisa de dato viejo cuando la pesada es reciente", async () => {
      vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
      vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
        { ...baseMedicion, id: 1, fecha: "2026-09-01", peso_kg: 78 },
        { ...baseMedicion, id: 2, fecha: "2026-09-13", peso_kg: 77 },
      ]);

      render(<BodyGoalInsightCard userId={1} />);

      await waitFor(() => expect(screen.getByText("−1.3 %")).toBeInTheDocument());
      expect(screen.queryByText(/vuelve a pesarte/i)).not.toBeInTheDocument();
      expect(screen.getByText(/tu peso de los últimos 30 días/i)).toBeInTheDocument();
    });

    it("pide un año de historial para poder encontrar la última pesada", async () => {
      vi.mocked(api.getUser).mockResolvedValue(usuarioBase);
      vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

      render(<BodyGoalInsightCard userId={1} />);

      await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(1, 365));
    });
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getUser).mockRejectedValue(new ApiError(500, "caido"));
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);

    render(<BodyGoalInsightCard userId={1} />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
