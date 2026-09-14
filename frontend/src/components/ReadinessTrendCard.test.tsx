import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReadinessTrendCard } from "./ReadinessTrendCard";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getReadinessHistory: vi.fn(),
    },
  };
});

describe("ReadinessTrendCard", () => {
  beforeEach(() => {
    vi.mocked(api.getReadinessHistory).mockReset();
    // `fechaCorta` omite el año cuando la fecha es del año en curso, así
    // que sin fijar el reloj estos asserts cambiarían solos el 1 de
    // enero. `shouldAdvanceTime` deja que `waitFor` siga funcionando.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 7, 10));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("coloca cada día en su columna de día de la semana, con cabeceras", async () => {
    // 1 ago 2026 es sábado, 2 ago domingo, 3 ago lunes: la rejilla
    // arranca el lunes 27 de julio y acaba el domingo 9 de agosto,
    // o sea 14 casillas (2 semanas completas).
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", resultado: "green", hrv_delta_pct: 2, training_readiness: "high", acwr: 1.0 },
      { id: 2, fecha: "2026-08-02", resultado: "yellow", hrv_delta_pct: -5, training_readiness: "moderate", acwr: 1.1 },
      { id: 3, fecha: "2026-08-03", resultado: "red", hrv_delta_pct: -15, training_readiness: "low", acwr: 1.6 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() => expect(screen.getAllByRole("gridcell")).toHaveLength(14));
    // Solo tres casillas pertenecen al periodo; las once que completan
    // las semanas se marcan como fuera de él y no como días perdidos.
    expect(screen.getAllByTestId("readiness-dia")).toHaveLength(3);
    expect(screen.getAllByTestId("readiness-fuera")).toHaveLength(11);
    expect(screen.getByRole("columnheader", { name: "lunes" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "domingo" })).toBeInTheDocument();
  });

  it("dice el nivel de cada día con palabras y fecha humana, no un color a secas", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", resultado: "red", hrv_delta_pct: -15, training_readiness: "low", acwr: 1.6 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() =>
      expect(
        screen.getByRole("gridcell", { name: "1 ago: recuperación baja" })
      ).toBeInTheDocument()
    );
  });

  it("deja en blanco los días sin dato del periodo, sin contarlos como recuperación baja", async () => {
    // 3 y 5 de agosto con dato, el 4 sin sincronizar: ese hueco SÍ es
    // información ("ese día falta"), a diferencia de las casillas que
    // solo rellenan la semana.
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-03", resultado: "green", hrv_delta_pct: 2, training_readiness: "high", acwr: 1.0 },
      { id: 2, fecha: "2026-08-05", resultado: "green", hrv_delta_pct: 1, training_readiness: "high", acwr: 1.0 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() => expect(screen.getAllByTestId("readiness-dia")).toHaveLength(3));
    expect(screen.getAllByRole("gridcell", { name: /sin datos/ })).toHaveLength(1);
    expect(screen.getAllByTestId("readiness-fuera")).toHaveLength(4);
    // Y el hueco no se cuenta como recuperación media ni baja: las dos
    // filas de la leyenda siguen a cero.
    expect(screen.getAllByText("0 días")).toHaveLength(2);
  });

  it("resume el mes en cifras escritas, con el plural resuelto", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-03", resultado: "green", hrv_delta_pct: 2, training_readiness: "high", acwr: 1.0 },
      { id: 2, fecha: "2026-08-04", resultado: "green", hrv_delta_pct: 3, training_readiness: "high", acwr: 1.0 },
      { id: 3, fecha: "2026-08-05", resultado: "red", hrv_delta_pct: -15, training_readiness: "low", acwr: 1.6 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() => expect(screen.getByText("2 días")).toBeInTheDocument());
    expect(screen.getByText("1 día")).toBeInTheDocument();
    expect(screen.getByText("0 días")).toBeInTheDocument();
  });

  it("agrupa múltiples filas del mismo día quedándose con la última", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([
      { id: 1, fecha: "2026-08-01", resultado: "red", hrv_delta_pct: -20, training_readiness: "low", acwr: 1.6 },
      { id: 2, fecha: "2026-08-01", resultado: "green", hrv_delta_pct: 1, training_readiness: "high", acwr: 1.0 },
    ]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() =>
      expect(
        screen.getByRole("gridcell", { name: "1 ago: recuperación óptima" })
      ).toBeInTheDocument()
    );
  });

  it("muestra un mensaje cuando no hay ningún día calculado todavía", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);

    render(<ReadinessTrendCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/todavía no hay ningún día con recuperación/i)).toBeInTheDocument()
    );
  });

  it("vuelve a pedir el historial cuando cambia refreshKey (tras un check-in nuevo)", async () => {
    vi.mocked(api.getReadinessHistory).mockResolvedValue([]);

    const { rerender } = render(<ReadinessTrendCard userId={1} refreshKey={0} />);
    await waitFor(() => expect(api.getReadinessHistory).toHaveBeenCalledTimes(1));

    rerender(<ReadinessTrendCard userId={1} refreshKey={1} />);
    await waitFor(() => expect(api.getReadinessHistory).toHaveBeenCalledTimes(2));
  });
});
