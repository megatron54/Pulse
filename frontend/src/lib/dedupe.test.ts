import { describe, expect, it } from "vitest";
import { dedupeUltimaPorDia } from "./dedupe";

describe("dedupeUltimaPorDia", () => {
  it("se queda con la fila de mayor id para una fecha repetida", () => {
    const resultado = dedupeUltimaPorDia([
      { id: 1, fecha: "2026-08-01", valor: "vieja" },
      { id: 2, fecha: "2026-08-01", valor: "nueva" },
    ]);
    expect(resultado).toEqual([{ id: 2, fecha: "2026-08-01", valor: "nueva" }]);
  });

  it("es correcto aunque el array NO venga ordenado por id ascendente", () => {
    // A propósito en desorden: la función no debe depender del orden
    // de llegada, solo del valor de `id`.
    const resultado = dedupeUltimaPorDia([
      { id: 5, fecha: "2026-08-01", valor: "correcta" },
      { id: 2, fecha: "2026-08-01", valor: "vieja" },
    ]);
    expect(resultado).toEqual([{ id: 5, fecha: "2026-08-01", valor: "correcta" }]);
  });

  it("conserva una fila por cada fecha distinta", () => {
    const resultado = dedupeUltimaPorDia([
      { id: 1, fecha: "2026-08-01", valor: "a" },
      { id: 2, fecha: "2026-08-02", valor: "b" },
    ]);
    expect(resultado).toHaveLength(2);
  });

  it("devuelve un array vacío para un array vacío", () => {
    expect(dedupeUltimaPorDia([])).toEqual([]);
  });
});
