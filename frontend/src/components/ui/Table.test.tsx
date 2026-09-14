import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Table, Td, TdNum } from "./Table";

const cabeceras = [
  { clave: "sesion", label: "Sesión" },
  { clave: "distancia", label: "Distancia", numerica: true },
] as const;

function tablaDePrueba() {
  return render(
    <Table cabeceras={cabeceras} etiqueta="Sesiones de prueba">
      <tr>
        <Td envolver>Entrenamiento de fuerza de tren superior</Td>
        <TdNum>{null}</TdNum>
      </tr>
    </Table>
  );
}

describe("Table", () => {
  it("tiene nombre accesible y una sola fila de cabeceras", () => {
    tablaDePrueba();

    expect(screen.getByRole("table", { name: "Sesiones de prueba" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader")).toHaveLength(2);
  });

  it("escribe “—” y no 0 cuando la cifra no existe", () => {
    // Doctrina 6: "lo desconocido no es cero". La auditoría encontró
    // "0.0 km" en cada sesión de fuerza.
    tablaDePrueba();

    expect(screen.getByLabelText("sin dato")).toHaveTextContent("—");
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("separa las cabeceras entre sí, salvo la última", () => {
    // Sin gotera en el `th`, a 390px las cabeceras se leían pegadas:
    // "DURACIÓN DISTANCIA FC MEDIA" parecía una sola.
    tablaDePrueba();

    const [primera, ultima] = screen.getAllByRole("columnheader");
    expect(primera.className).toContain("pr-4");
    expect(ultima.className).toContain("last:pr-0");
  });

  it("alinea las cifras con la primera línea de la celda de texto", () => {
    // Con la fecha debajo del nombre de la sesión, una cifra centrada
    // verticalmente flotaba entre las dos líneas.
    tablaDePrueba();

    expect(screen.getByLabelText("sin dato").parentElement!.className).toContain("align-top");
  });

  it("deja que la celda con `envolver` se parta en varias líneas", () => {
    // Doctrina 4: nada se corta. La celda de texto libre es la que cede
    // ancho partiéndose, en vez de empujar la tabla fuera de la tarjeta.
    tablaDePrueba();

    const celda = screen.getByText("Entrenamiento de fuerza de tren superior");
    expect(celda.className).not.toContain("whitespace-nowrap");
    expect(celda.className).toContain("text-pretty");
  });
});
