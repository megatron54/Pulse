import { describe, expect, it, afterEach, vi } from "vitest";
import {
  diasDesdeHoy,
  fechaCorta,
  fechaMenosDias,
  fechaRelativa,
  masRecientePorFecha,
  plural,
} from "./fechas";

describe("masRecientePorFecha", () => {
  it("devuelve null sin elementos", () => {
    expect(masRecientePorFecha([])).toBeNull();
  });

  // Regresión del bug real que motivó el helper: el hero de "Hoy" leía
  // `.at(-1)` de una respuesta DESCENDENTE y mostraba el día más
  // antiguo de la ventana como si fuera hoy.
  it("elige el mas reciente con la respuesta en orden descendente", () => {
    const descendente = [{ fecha: "2026-09-13" }, { fecha: "2026-09-12" }, { fecha: "2026-09-11" }];
    expect(masRecientePorFecha(descendente)).toEqual({ fecha: "2026-09-13" });
  });

  it("elige el mas reciente con la respuesta en orden ascendente", () => {
    const ascendente = [{ fecha: "2026-09-11" }, { fecha: "2026-09-12" }, { fecha: "2026-09-13" }];
    expect(masRecientePorFecha(ascendente)).toEqual({ fecha: "2026-09-13" });
  });
});

describe("fechaRelativa", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("dice Hoy y Ayer, y fecha corta mas atras", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13));

    expect(fechaRelativa("2026-09-13")).toBe("Hoy");
    expect(fechaRelativa("2026-09-12")).toBe("Ayer");
    expect(fechaRelativa("2026-09-05")).toBe("5 sep");
  });

  it("no retrocede un dia por interpretar el ISO como UTC", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 0, 1));
    expect(fechaCorta("2026-01-01")).toBe("1 ene");
  });
});

describe("fechaMenosDias", () => {
  it("retrocede dias cruzando meses y anios", () => {
    expect(fechaMenosDias("2026-07-01", 29)).toBe("2026-06-02");
    expect(fechaMenosDias("2026-01-05", 10)).toBe("2025-12-26");
    expect(fechaMenosDias("2026-03-01", 1)).toBe("2026-02-28");
  });

  it("cero dias devuelve la misma fecha", () => {
    expect(fechaMenosDias("2026-09-14", 0)).toBe("2026-09-14");
  });
});

describe("diasDesdeHoy", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("cuenta los dias transcurridos desde una fecha pasada", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 14));

    expect(diasDesdeHoy("2026-09-14")).toBe(0);
    expect(diasDesdeHoy("2026-07-01")).toBe(75);
  });
});

describe("plural", () => {
  it("concuerda el singular", () => {
    expect(plural(1, "día con dato", "días con dato")).toBe("1 día con dato");
    expect(plural(3, "día con dato", "días con dato")).toBe("3 días con dato");
  });
});
