import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageHeader } from "./PageHeader";

describe("PageHeader", () => {
  it("muestra título y subtítulo", () => {
    render(<PageHeader title="Hoy" subtitle="Hola, Test." />);
    expect(screen.getByRole("heading", { name: "Hoy" })).toBeInTheDocument();
    expect(screen.getByText("Hola, Test.")).toBeInTheDocument();
  });

  it("no renderiza el subtítulo si no se pasa", () => {
    render(<PageHeader title="Coach" />);
    expect(screen.queryByText(/hola/i)).not.toBeInTheDocument();
  });

  it("renderiza las acciones a la derecha cuando se pasan", () => {
    render(<PageHeader title="Entrenamiento" actions={<button>Filtrar</button>} />);
    expect(screen.getByRole("button", { name: "Filtrar" })).toBeInTheDocument();
  });
});
