import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BodyCompositionTile } from "./BodyCompositionTile";
import { api, ApiError, type User } from "@/lib/api";
import { UserProvider } from "@/lib/UserContext";

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

const USUARIO: User = {
  id: 1,
  nombre: "Miguel",
  altura_cm: 176,
  fecha_nacimiento: "2002-11-28",
  sexo: "M",
  fase_peso_actual: "maintenance",
};

function montar(props: { userId: number; refreshKey?: number }, sexo: "M" | "F" = "M") {
  return render(
    <UserProvider user={{ ...USUARIO, sexo }} onUserChange={vi.fn()}>
      <BodyCompositionTile {...props} />
    </UserProvider>
  );
}

const base = {
  id: 1,
  fecha: "2026-08-10",
  peso_kg: 78.5,
  metodo: "manual" as const,
  bodyfat_pct_rango_min: null,
  bodyfat_pct_rango_max: null,
  muscle_kg: null,
  bone_kg: null,
  water_pct: null,
  bmi: null,
};

describe("BodyCompositionTile", () => {
  beforeEach(() => {
    vi.mocked(api.getBodyMeasurementHistory).mockReset();
  });

  it("no muestra nada si todavia no hay mediciones", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);
    const { container } = montar({ userId: 1 });
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("no muestra nada si la ultima medicion es solo peso, sin composicion", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([base]);
    const { container } = montar({ userId: 1 });
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("muestra un tile por cada campo de composicion presente en la ultima medicion", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      {
        ...base,
        metodo: "feelfit_bioimpedance" as unknown as "manual",
        bodyfat_pct_rango_min: 18.2,
        bodyfat_pct_rango_max: 18.2,
        muscle_kg: 34.1,
        bone_kg: 3.2,
        water_pct: 55.4,
        bmi: 24.1,
      },
    ]);

    montar({ userId: 1 });

    await waitFor(() => expect(screen.getByText(/% grasa/i)).toBeInTheDocument());
    expect(screen.getByText(/músculo/i)).toBeInTheDocument();
    expect(screen.getByText(/hueso/i)).toBeInTheDocument();
    expect(screen.getByText(/agua/i)).toBeInTheDocument();
    // "IMC" en pantalla: "bmi" es el nombre de la columna.
    expect(screen.getByText("IMC")).toBeInTheDocument();
    expect(screen.queryByText(/bmi/i)).not.toBeInTheDocument();
  });

  it("fecha la medicion y elige la mas reciente aunque el historial llegue desordenado", async () => {
    // `dedupeUltimaPorDia` no promete orden, asi que un `.at(-1)` sin
    // ordenar podia mostrar la composicion de una pesada antigua.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 8, 14));
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...base, id: 2, fecha: "2026-07-01", bmi: 24.8 },
      { ...base, id: 1, fecha: "2026-06-01", bmi: 22.2 },
    ]);

    montar({ userId: 1 });

    await waitFor(() => expect(screen.getByText("24.8")).toBeInTheDocument());
    expect(screen.getByText(/última medida: 1 jul/i)).toBeInTheDocument();
    expect(screen.queryByText("22.2")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("pide un año de historial: la ultima pesada puede ser de hace meses", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([]);
    montar({ userId: 1 });
    await waitFor(() => expect(api.getBodyMeasurementHistory).toHaveBeenCalledWith(1, 365));
  });

  it("muestra el % de grasa como rango cuando min y max difieren (metodo navy manual)", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...base, bodyfat_pct_rango_min: 15.0, bodyfat_pct_rango_max: 19.0 },
    ]);

    montar({ userId: 1 });

    // El "%" va en su propio <span> (unidad atenuada), asi que se
    // compara el texto completo del parrafo. Guion largo, no "-": es un
    // rango, no una resta.
    await waitFor(() =>
      expect(
        screen.getByText((_, el) => el?.textContent === "15.0–19.0%" && el.tagName === "P")
      ).toBeInTheDocument()
    );
  });

  it("colorea el IMC y el % de grasa segun su rango de referencia (doctrina 1: color = informacion)", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...base, bodyfat_pct_rango_min: 22.0, bodyfat_pct_rango_max: 22.0, bmi: 32.0 },
    ]);

    montar({ userId: 1 }, "M");

    // El color vive en el <p> que envuelve la cifra (StatTile), no en el
    // <span> que anima el número - de ahí el `.closest("p")`.
    // IMC 32 en un hombre: obesidad (rango OMS) -> rojo.
    await waitFor(() =>
      expect(screen.getByText("32.0").closest("p")).toHaveClass("text-neg")
    );
    // 22% de grasa en un hombre supera el rango normal (ACE, 20-25) -> amarillo.
    expect(screen.getByText("22.0").closest("p")).toHaveClass("text-warn");
  });

  it("el agua solo se marca 'bajo' (azul) si cae por debajo del rango: un agua alta no es un riesgo conocido", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...base, water_pct: 40.0 },
    ]);

    montar({ userId: 1 }, "M");

    await waitFor(() =>
      expect(screen.getByText("40.0").closest("p")).toHaveClass("text-data")
    );
  });

  it("no colorea musculo ni hueso: son kg absolutos sin rango de referencia valido", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockResolvedValue([
      { ...base, muscle_kg: 34.1, bone_kg: 3.2 },
    ]);

    montar({ userId: 1 });

    await waitFor(() => expect(screen.getByText("34.1")).toBeInTheDocument());
    expect(screen.getByText("34.1").closest("p")).toHaveClass("text-ink");
    expect(screen.getByText("3.2").closest("p")).toHaveClass("text-ink");
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getBodyMeasurementHistory).mockRejectedValue(new ApiError(500, "caido"));
    montar({ userId: 1 });
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
