import { describe, expect, it } from "vitest";
import { formatNumero } from "./numeros";

const ESPACIO_FINO = " ";

describe("formatNumero", () => {
  it("no agrupa por debajo de 10 000", () => {
    expect(formatNumero(0)).toBe("0");
    expect(formatNumero(842)).toBe("842");
    // Cuatro dígitos sin separar a propósito: "2 450 kcal" se lee peor.
    expect(formatNumero(2450)).toBe("2450");
    expect(formatNumero(9999)).toBe("9999");
  });

  it("agrupa los miles con espacio fino irrompible desde 10 000", () => {
    expect(formatNumero(10_000)).toBe(`10${ESPACIO_FINO}000`);
    // El caso que motivó el módulo: 13893 pasos.
    expect(formatNumero(13_893)).toBe(`13${ESPACIO_FINO}893`);
    expect(formatNumero(1_234_567)).toBe(`1${ESPACIO_FINO}234${ESPACIO_FINO}567`);
  });

  it("nunca usa el punto como separador de miles", () => {
    // La app escribe los decimales con punto ("78.4 kg"), así que
    // "13.893" sería ambiguo.
    expect(formatNumero(13_893)).not.toContain(".");
  });

  it("respeta los decimales pedidos y los separa del grupo de miles", () => {
    expect(formatNumero(78.44, 1)).toBe("78.4");
    expect(formatNumero(12_345.67, 2)).toBe(`12${ESPACIO_FINO}345.67`);
  });

  it("conserva el signo de los negativos", () => {
    expect(formatNumero(-12_500)).toBe(`-12${ESPACIO_FINO}500`);
    expect(formatNumero(-450)).toBe("-450");
  });
});
