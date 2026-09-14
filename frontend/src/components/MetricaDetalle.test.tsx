import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MetricaDetalle } from "./MetricaDetalle";
import { api, ApiError } from "@/lib/api";
import { metricaPorSlug } from "@/lib/metricasSalud";
import { unDiaDeSalud, unaNoche } from "@/test/salud";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthHistory: vi.fn(),
      getGarminIntradayHistory: vi.fn(),
    },
  };
});

const SUENO = metricaPorSlug("sueno")!;
const BODY_BATTERY = metricaPorSlug("body-battery")!;
const PASOS = metricaPorSlug("pasos")!;
const PULSO = metricaPorSlug("pulso-reposo")!;

describe("MetricaDetalle", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthHistory).mockReset();
    vi.mocked(api.getGarminIntradayHistory).mockReset();
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);
  });

  it("abre con la última cifra, de cuándo es, y cuánto se sale de tu media", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", sleep_score: 88 }),
      unDiaDeSalud({ fecha: "2026-09-13", sleep_score: 60 }),
      unDiaDeSalud({ fecha: "2026-09-12", sleep_score: 60 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={SUENO} />);

    // La cifra grande es la MÁS RECIENTE, no la primera de la respuesta
    // (el endpoint devuelve descendente, pero el tipo no lo garantiza).
    // Con `selector` porque el 88 sale dos veces a propósito: la cifra
    // grande de arriba y su fila en la tabla de abajo.
    await waitFor(() =>
      expect(screen.getByText("88", { selector: ".t-hero" })).toBeInTheDocument()
    );
    expect(screen.getByText("hoy")).toBeInTheDocument();
    // Media 69.33 -> 18.67 por encima, redondeado a los decimales de la
    // métrica. Y dice si eso es bueno: dormir MÁS lo es.
    const comparacion = screen.getByText(/por encima de tu media de 30 días/);
    expect(comparacion).toHaveTextContent("19 por encima de tu media de 30 días.");
    expect(comparacion).toHaveClass("text-pos");
  });

  it("no tiñe de verde el ruido de un día: una desviación mínima se lee como 'en tu media'", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", sleep_score: 81 }),
      unDiaDeSalud({ fecha: "2026-09-13", sleep_score: 80 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={SUENO} />);

    await waitFor(() =>
      expect(screen.getByText("En tu media de los últimos 30 días.")).toBeInTheDocument()
    );
  });

  it("en una métrica en la que más es peor, subir no se pinta como bueno", async () => {
    const estres = metricaPorSlug("estres")!;
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", stress_avg: 60 }),
      unDiaDeSalud({ fecha: "2026-09-13", stress_avg: 20 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={estres} />);

    await waitFor(() =>
      expect(screen.getByText(/por encima de tu media/)).toHaveClass("text-neg")
    );
  });

  it("lista las noches en una tabla, la última arriba, con lo que se durmió", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unaNoche({ fecha: "2026-09-13", sleep_score: 71 }),
      unaNoche({ fecha: "2026-09-14", sleep_score: 88 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={SUENO} />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    // La columna se llama "Noche" y no "Día": el sueño se mide por
    // noches, y traducirlo cada vez es trabajo del usuario (doctrina 8).
    expect(screen.getByRole("columnheader", { name: "Noche" })).toBeInTheDocument();
    const filas = screen.getAllByRole("row");
    expect(filas[1]).toHaveTextContent("Hoy");
    expect(filas[1]).toHaveTextContent("88");
    // 5400 + 4800 + 16200 = 26400 s dormidos, sin contar los 900
    // despierto: "he dormido 7 h 20" no incluye los despertares.
    expect(filas[1]).toHaveTextContent("7 h 20 min");
    expect(filas[2]).toHaveTextContent("Ayer");
  });

  it("al pulsar una noche despliega sus fases justo debajo, y al volver a pulsarla las cierra", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unaNoche({ fecha: "2026-09-14" }),
      unaNoche({ fecha: "2026-09-13" }),
    ]);

    render(<MetricaDetalle userId={4} metrica={SUENO} />);
    const noche = await screen.findByRole("button", { name: /ver el detalle de la noche del 14 sep/i });

    expect(noche).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(noche);

    expect(noche).toHaveAttribute("aria-expanded", "true");
    // Las cuatro fases con su cifra escrita al lado, no solo la barra.
    expect(screen.getByText("Profundo")).toBeInTheDocument();
    expect(screen.getByText("1 h 30 min")).toBeInTheDocument();
    expect(screen.getByText("Despierto")).toBeInTheDocument();

    await userEvent.click(noche);
    expect(screen.queryByText("Profundo")).not.toBeInTheDocument();
  });

  it("una noche con puntuación pero sin fases lo dice, en vez de dibujar cuatro fases a cero", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", sleep_score: 64 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={SUENO} />);
    const noche = await screen.findByRole("button", { name: /ver el detalle de la noche/i });
    await userEvent.click(noche);

    expect(screen.getByText(/registró la puntuación pero no las fases/i)).toBeInTheDocument();
    expect(screen.queryByText("Profundo")).not.toBeInTheDocument();
  });

  it("al pulsar un día de Body Battery pide su serie minuto a minuto de ESE día", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", body_battery_am: 72 }),
      unDiaDeSalud({ fecha: "2026-09-13", body_battery_am: 55 }),
    ]);
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([
      { timestamp_utc: "2026-09-13T06:00:00Z", valor: 55 },
      { timestamp_utc: "2026-09-13T12:00:00Z", valor: 40 },
    ]);

    render(<MetricaDetalle userId={4} metrica={BODY_BATTERY} />);
    const dia = await screen.findByRole("button", { name: /ver el detalle del día del 13 sep/i });
    await userEvent.click(dia);

    await waitFor(() =>
      expect(api.getGarminIntradayHistory).toHaveBeenCalledWith(4, "body_battery", "2026-09-13")
    );
    expect(await screen.findByText("2 mediciones ese día.")).toBeInTheDocument();
    expect(screen.getByText("Body Battery minuto a minuto del 13 sep")).toBeInTheDocument();
  });

  it("la gráfica del día dice que el pulso es el de TODO el día, no el de reposo", async () => {
    // La cifra de la fila es 52 ppm y la línea del detalle sube a 180:
    // el reloj guarda el pulso del día completo y el reposo es solo su
    // tramo más bajo. Sin rótulo, la gráfica desmiente a la cifra que
    // se acaba de pulsar.
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", resting_hr: 52 }),
    ]);
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([
      { timestamp_utc: "2026-09-14T04:00:00Z", valor: 52 },
      { timestamp_utc: "2026-09-14T18:00:00Z", valor: 180 },
    ]);

    render(<MetricaDetalle userId={4} metrica={PULSO} />);
    await userEvent.click(await screen.findByRole("button", { name: /ver el detalle del día/i }));

    expect(
      await screen.findByText("Pulso de todo el día, minuto a minuto del 14 sep")
    ).toBeInTheDocument();
  });

  it("si el reloj no guardó la serie de ese día lo explica, sin dejar un hueco mudo", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", body_battery_am: 72 }),
    ]);
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);

    render(<MetricaDetalle userId={4} metrica={BODY_BATTERY} />);
    await userEvent.click(await screen.findByRole("button", { name: /ver el detalle del día/i }));

    expect(await screen.findByText(/no guardó la serie minuto a minuto de ese día/i)).toBeInTheDocument();
  });

  it("los días sin dato no son días a cero: no salen en la tabla ni cuentan para la media", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", pasos: 8000 }),
      unDiaDeSalud({ fecha: "2026-09-13" }),
      unDiaDeSalud({ fecha: "2026-09-12", pasos: 12000 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={PASOS} />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    // 2 días con dato + la cabecera: el 13 no existe, no es un 0.
    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(screen.getByText("2 días")).toBeInTheDocument();
    // Media de 8000 y 12000 = 10 000, con el separador de miles puesto.
    expect(screen.getByText("10 000")).toBeInTheDocument();
  });

  it("una métrica sin detalle por día no finge tener filas pulsables", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([
      unDiaDeSalud({ fecha: "2026-09-14", pasos: 8000 }),
    ]);

    render(<MetricaDetalle userId={4} metrica={PASOS} />);

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /ver el detalle/i })).not.toBeInTheDocument();
    expect(screen.getByText(/todo lo que el reloj ha registrado/i)).toBeInTheDocument();
  });

  it("una ventana sin datos dice qué hacer, y aun así explica qué es la métrica", async () => {
    vi.mocked(api.getGarminHealthHistory).mockResolvedValue([]);

    render(<MetricaDetalle userId={4} metrica={metricaPorSlug("vo2max")!} />);

    await waitFor(() =>
      expect(screen.getByText(/prueba con un rango más amplio/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/estimación de tu capacidad aeróbica/i)).toBeInTheDocument();
  });

  it("muestra un error con reintento si la petición falla", async () => {
    vi.mocked(api.getGarminHealthHistory).mockRejectedValue(new ApiError(503, "Garmin no responde"));

    render(<MetricaDetalle userId={4} metrica={SUENO} />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText("Garmin no responde")).toBeInTheDocument();
  });
});
