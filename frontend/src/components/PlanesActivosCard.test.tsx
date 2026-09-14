import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlanesActivosCard } from "./PlanesActivosCard";
import { api, type TrainingBlock } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      listTrainingBlocks: vi.fn(),
      deleteTrainingBlock: vi.fn(),
    },
  };
});

// `todayLocalDate` del módulo real devuelve la fecha del sistema, y los
// tests fijan rangos alrededor de esta fecha para que "En curso" /
// "Terminado" no dependan del día en que se ejecuten.
const HOY = new Date();
const iso = (desplazamientoDias: number) => {
  const d = new Date(HOY);
  d.setDate(d.getDate() + desplazamientoDias);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
};

function plan(parcial: Partial<TrainingBlock> & { id: number }): TrainingBlock {
  return {
    fecha_inicio: iso(0),
    fecha_fin: iso(28),
    objetivo_prioritario: "fuerza",
    semana_actual: 1,
    es_deload: false,
    ...parcial,
  };
}

describe("PlanesActivosCard", () => {
  beforeEach(() => {
    vi.mocked(api.listTrainingBlocks).mockReset();
    vi.mocked(api.deleteTrainingBlock).mockReset();
  });

  it("sin ningun plan, dice qué hacer y no solo que no hay nada", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/plan semanal de abajo/i)).toBeInTheDocument());
  });

  it("muestra el objetivo en español, nunca la cadena interna", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([
      plan({ id: 1, objetivo_prioritario: "artes_marciales" }),
    ]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByText("Artes marciales")).toBeInTheDocument());
    expect(screen.queryByText(/artes_marciales/)).not.toBeInTheDocument();
  });

  it("distingue un plan en curso de uno ya terminado", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([
      plan({ id: 1 }),
      plan({ id: 2, fecha_inicio: iso(-60), fecha_fin: iso(-30) }),
    ]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByText("En curso")).toBeInTheDocument());
    expect(screen.getByText("Terminado")).toBeInTheDocument();
  });

  it("marca qué filas se pisan, no solo que hay un solapamiento", async () => {
    // El caso que dejaba a "Hoy" sin sesión: con el aviso solo arriba,
    // el usuario tendría que comparar fechas a ojo para saber cuáles.
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([
      plan({ id: 1, objetivo_prioritario: "fuerza" }),
      plan({ id: 2, objetivo_prioritario: "recomposicion" }),
      plan({ id: 3, fecha_inicio: iso(-60), fecha_fin: iso(-30) }),
    ]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/se pisan en las mismas fechas/i)).toBeInTheDocument());
    expect(screen.getAllByText("Se pisa con otro plan")).toHaveLength(2);
  });

  it("sin solapamiento no avisa de nada", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([plan({ id: 1 })]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByText("En curso")).toBeInTheDocument());
    expect(screen.queryByText(/se pisan/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/se pisa con otro plan/i)).not.toBeInTheDocument();
  });

  it("borrar pide confirmacion nombrando el plan, y no borra hasta aceptarla", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([
      plan({ id: 7, objetivo_prioritario: "recomposicion" }),
    ]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Borrar" })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Borrar" }));

    // La confirmación nombra el plan: lo que hay que verificar antes de
    // aceptar es CUÁL se va a borrar, no si uno está seguro.
    expect(screen.getByText(/¿Borrar «Recomposición corporal»/)).toBeInTheDocument();
    expect(api.deleteTrainingBlock).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /sí, borrar/i }));
    expect(api.deleteTrainingBlock).toHaveBeenCalledWith(1, 7);
  });

  it("cancelar la confirmacion no borra nada", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([plan({ id: 7 })]);
    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Borrar" })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Borrar" }));
    await userEvent.click(screen.getByRole("button", { name: /cancelar/i }));

    expect(api.deleteTrainingBlock).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Borrar" })).toBeInTheDocument();
  });

  it("tras borrar, vuelve a pedir la lista para que el solapamiento desaparezca", async () => {
    vi.mocked(api.listTrainingBlocks)
      .mockResolvedValueOnce([plan({ id: 1 }), plan({ id: 2 })])
      .mockResolvedValueOnce([plan({ id: 1 })]);
    vi.mocked(api.deleteTrainingBlock).mockResolvedValue(undefined);

    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getAllByText("Se pisa con otro plan")).toHaveLength(2));

    await userEvent.click(screen.getAllByRole("button", { name: "Borrar" })[1]);
    await userEvent.click(screen.getByRole("button", { name: /sí, borrar/i }));

    await waitFor(() => expect(screen.queryByText(/se pisa con otro plan/i)).not.toBeInTheDocument());
  });

  it("si el borrado falla, lo dice y el plan sigue en la lista", async () => {
    vi.mocked(api.listTrainingBlocks).mockResolvedValue([plan({ id: 7 })]);
    vi.mocked(api.deleteTrainingBlock).mockRejectedValue(new Error("red caída"));

    render(<PlanesActivosCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Borrar" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Borrar" }));
    await userEvent.click(screen.getByRole("button", { name: /sí, borrar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo borrar/i);
    expect(screen.getByText("Ganar fuerza")).toBeInTheDocument();
  });
});
