import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GarminHealthHistoryCard } from "./GarminHealthHistoryCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthHistory: vi.fn(),
    },
  };
});

describe("GarminHealthHistoryCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
  });

  it("muestra un mensaje honesto de 'sin datos' cuando el historial viene vacío", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/garmin no ha sincronizado ningún día en esta ventana/i)).toBeInTheDocument()
    );
  });

  it("muestra un error si la petición falla", async () => {
    vi.mocked(api.getGarminHealthHistory).mockRejectedValue(new ApiError(404, "no existe"));
    render(<GarminHealthHistoryCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("muestra solo las métricas que sí tienen algún dato real (nunca inventa una gráfica vacía)", async () => {
    // Día con HRV/sleep pero sin stress/resting_hr/vo2max - "unknown is
    // not zero": no debe aparecer una sección de estrés vacía.
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: 49,
        hrv_status: "NONE",
        body_battery_am: 77,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() => expect(screen.getByText("Variabilidad cardíaca")).toBeInTheDocument());
    expect(screen.getByText("Body Battery al despertar")).toBeInTheDocument();
    expect(screen.getByText("Calidad del sueño")).toBeInTheDocument();
    // Las siglas del proveedor no llegan a la interfaz: ni "VFC (HRV)"
    // ni "VO2max" dicen al usuario qué está mirando.
    expect(screen.queryByText(/hrv/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/estrés medio/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/pulso en reposo/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/VO₂/)).not.toBeInTheDocument();
  });

  it("el selector de rango vuelve a pedir el historial con los días correctos", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: 49,
        hrv_status: "NONE",
        body_battery_am: 77,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: 10,
        resting_hr: 54,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<GarminHealthHistoryCard userId={1} />);
    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 90));

    const boton30d = screen.getByRole("tab", { name: "30 días" });
    boton30d.click();

    await waitFor(() => expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 30));
  });

  it("marca con aria-selected el rango activo del selector", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByRole("tab", { name: "90 días" })).toHaveAttribute("aria-selected", "true")
    );
    expect(screen.getByRole("tab", { name: "7 días" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "30 días" })).toHaveAttribute("aria-selected", "false");
  });

  it("muestra el valor MÁS RECIENTE de cada métrica, no el más antiguo (el backend devuelve desc)", async () => {
    // El endpoint devuelve más reciente primero - el componente debe
    // invertir el orden antes de graficar/leer "el último valor". Si
    // se eliminara el reverse(), este test detectaría la regresión:
    // el "último" mostrado sería el valor MÁS ANTIGUO (40), no el más
    // reciente (60).
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: 60,
        hrv_status: null,
        body_battery_am: null,
        training_readiness: null,
        sleep_score: null,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
      {
        fecha: "2026-08-01",
        hrv_value: 40,
        hrv_status: null,
        body_battery_am: null,
        training_readiness: null,
        sleep_score: null,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() => expect(screen.getByText("Variabilidad cardíaca")).toBeInTheDocument());
    // Se mira la CABECERA de la seccion y no toda la pantalla: desde
    // que el eje Y rotula marcas redondas propias, "40 ms" puede
    // aparecer legitimamente como marca del eje. Se sube al `<h3>` con
    // `closest` y no con `parentElement`: el titulo es ahora un enlace
    // a su pagina de detalle, asi que su padre directo es el propio
    // enlace y no la fila que contiene la cifra.
    const cabecera = screen.getByText("Variabilidad cardíaca").closest("h3")!.parentElement!;
    expect(cabecera.textContent).toContain("60 ms");
    expect(cabecera.textContent).not.toContain("40 ms");
  });

  it("grafica un valor legítimo de 0 - no lo trata como ausente", async () => {
    // "unknown is not zero" en su dirección inversa: un 0 real (ej.
    // estrés medio de 0, un día perfectamente relajado) no debe
    // confundirse con "sin dato" y ocultar la sección.
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: null,
        hrv_status: null,
        body_battery_am: null,
        training_readiness: null,
        sleep_score: null,
        stress_avg: 0,
        resting_hr: null,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/estrés medio/i)).toBeInTheDocument());
  });

  it("muestra las fases de sueño de la última noche con datos", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: null,
        hrv_status: null,
        body_battery_am: null,
        training_readiness: null,
        sleep_score: null,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: 5400,
        light_sleep_seg: 14400,
        rem_sleep_seg: 5040,
        awake_sleep_seg: 600,
      },
    ]);

    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/fases de sueño/i)).toBeInTheDocument());
    expect(screen.getByText(/profundo/i)).toBeInTheDocument();
    expect(screen.getByText(/rem/i)).toBeInTheDocument();
    expect(screen.getByText(/ligero/i)).toBeInTheDocument();
  });

  it("no muestra la sección de fases de sueño si ningún día trae esos datos", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-06",
        hrv_value: 49,
        hrv_status: null,
        body_battery_am: null,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
        pasos: null,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<GarminHealthHistoryCard userId={1} />);

    await waitFor(() => expect(screen.getByText("Calidad del sueño")).toBeInTheDocument());
    expect(screen.queryByText(/fases de sueño/i)).not.toBeInTheDocument();
  });
});
