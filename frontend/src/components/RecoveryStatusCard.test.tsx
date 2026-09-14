import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecoveryStatusCard } from "./RecoveryStatusCard";
import { api, ApiError } from "@/lib/api";
import { unDiaDeReadiness, unasSenales } from "@/test/readiness";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthHistory: vi.fn(),
      getReadinessHistory: vi.fn(),
      // CoachNarrativeBlock llama a esto internamente - se mockea para
      // que los tests no disparen una petición de red real de fondo.
      getGarminHealthNarrative: vi.fn().mockResolvedValue({ text: null, source: null }),
    },
  };
});

describe("RecoveryStatusCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
    vi.mocked(api.getReadinessHistory).mockReset();
    vi.mocked(api.getGarminHealthNarrative).mockReset();
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({ text: null, source: null });
  });

  it("pide solo el readiness de hoy y los ultimos 7 dias de historial (nunca todo el historico)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(api.getReadinessHistory).toHaveBeenCalledWith(1, 1));
    expect(api.getGarminHealthHistory).toHaveBeenCalledWith(1, 7);
  });

  it("dice que aun no hay datos (nunca un cero inventado) si el scheduler no ha sincronizado todavia", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/sin datos de hoy todavía/i)).toBeInTheDocument());
  });

  it("muestra el semaforo de zona cuando ya hay un readiness calculado hoy", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([unDiaDeReadiness()]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/recuperación óptima/i)).toBeInTheDocument());
  });

  it("dice qué significa el veredicto y cuál es la señal que lo está bajando", async () => {
    // La pregunta literal del usuario: "¿qué significa? ¿estoy
    // correctamente descansado o no? ¿por qué está en rojo?". Y el caso
    // real que la provocó: VFC de hoy un 16 % POR ENCIMA de su media
    // con veredicto rojo, porque la que cruzaba el umbral era la
    // tendencia de 7 días - la única señal que no se dibujaba en
    // ninguna pantalla.
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      unDiaDeReadiness({
        resultado: "red",
        hrv_delta_pct: 0.16,
        hrv_trend_7d: -0.19,
        senales: unasSenales({
          hrv_delta: { estado: "ok", valor: 0.16 },
          hrv_trend: { estado: "red", valor: -0.19 },
        }),
      }),
    ]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);

    render(<RecoveryStatusCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/no estás recuperado/i)).toBeInTheDocument());
    expect(
      screen.getByText(/lo que baja el veredicto hoy es una sola señal: la tendencia de vfc/i)
    ).toBeInTheDocument();
    // La cifra culpable, al lado de la referencia que la delata.
    expect(screen.getByText("−19 %")).toBeInTheDocument();
    expect(screen.getByText("≥ −10 %")).toBeInTheDocument();
    // Y la VFC de hoy sigue dibujándose como lo que es (buena), sin que
    // eso contradiga al veredicto: son dos señales distintas.
    expect(screen.getByText("+16 %")).toBeInTheDocument();
    // Sin consejos sobre las señales que hoy están bien.
    expect(screen.queryByText(/body battery al despertar depende/i)).not.toBeInTheDocument();
  });

  it("si Garmin ya sincronizó hoy pero falta el cálculo, no dice que no haya datos de hoy", async () => {
    // La tarjeta se contradecía: "Sin datos de hoy todavía" encima de
    // "Últimos datos sincronizados: hoy", con las cifras de hoy debajo.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 8, 14));
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-09-14",
        hrv_value: null,
        hrv_status: null,
        body_battery_am: 2,
        training_readiness: null,
        sleep_score: null,
        stress_avg: 29,
        resting_hr: 54,
        vo2max: null,
        pasos: 183,
        deep_sleep_seg: null,
        light_sleep_seg: null,
        rem_sleep_seg: null,
        awake_sleep_seg: null,
      },
    ]);

    render(<RecoveryStatusCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText("Recuperación sin calcular")).toBeInTheDocument()
    );
    expect(screen.queryByText(/sin datos de hoy todavía/i)).not.toBeInTheDocument();
    expect(screen.getByText(/necesita además el sueño y la variabilidad cardíaca/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("si el último día sincronizado NO es hoy, sí dice que faltan los datos de hoy", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 8, 14));
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-09-11",
        hrv_value: 49,
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

    render(<RecoveryStatusCard userId={1} />);

    await waitFor(() => expect(screen.getByText(/sin datos de hoy todavía/i)).toBeInTheDocument());
    expect(screen.getByText(/últimos datos sincronizados: 11 sep/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getReadinessHistory).mockRejectedValue(new ApiError(500, "caido"));
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("muestra el valor de hoy de cada metrica con datos, y omite las que no tienen ninguno", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([unDiaDeReadiness()]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      {
        fecha: "2026-08-10",
        hrv_value: 49,
        hrv_status: "NONE",
        body_battery_am: 77,
        training_readiness: null,
        sleep_score: 82,
        stress_avg: null,
        resting_hr: null,
        vo2max: null,
        pasos: 8432,
      deep_sleep_seg: null,
      light_sleep_seg: null,
      rem_sleep_seg: null,
      awake_sleep_seg: null,
    },
    ]);

    render(<RecoveryStatusCard userId={1} />);

    // Texto EXACTO y no `/vfc/i`: desde que la tarjeta explica el
    // veredicto, la tabla de señales también habla de "VFC frente a tu
    // media" y de "Body Battery al despertar", así que una expresión
    // regular laxa encuentra tres coincidencias y falla sin que haya
    // nada roto.
    await waitFor(() => expect(screen.getByText("VFC")).toBeInTheDocument());
    expect(screen.getByText("Body Battery")).toBeInTheDocument();
    expect(screen.getByText("Sueño")).toBeInTheDocument();
    expect(screen.getByText("Pasos")).toBeInTheDocument();
    expect(screen.queryByText("Estrés")).not.toBeInTheDocument();
  });

  it("no renderiza ningun formulario manual (check-in eliminado del todo)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);
    render(<RecoveryStatusCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/sin datos de hoy todavía/i)).toBeInTheDocument());
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });
  it("elige el dia MAS RECIENTE aunque el endpoint devuelva orden descendente", async () => {
    // Regresion del bug real que encontro la auditoria:
    // GET /garmin/health-history devuelve "mas reciente primero", pero
    // la tarjeta leia `historial.at(-1)` - el dia mas ANTIGUO de la
    // ventana - y mostraba datos de hace una semana como los de hoy.
    const dia = (fecha: string, hrv: number) => ({
      fecha,
      hrv_value: hrv,
      hrv_status: "NONE",
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
    });
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      dia("2026-08-10", 49),
      dia("2026-08-04", 65),
    ]);

    render(<RecoveryStatusCard userId={1} />);

    await waitFor(() => expect(screen.getByText("49")).toBeInTheDocument());
    expect(screen.queryByText("65")).not.toBeInTheDocument();
  });
});
