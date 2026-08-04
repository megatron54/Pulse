import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HabitJournalCard } from "./HabitJournalCard";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      setHabits: vi.fn(),
      getHabitCorrelation: vi.fn(),
    },
  };
});

describe("HabitJournalCard", () => {
  beforeEach(() => {
    vi.mocked(api.setHabits).mockReset();
    vi.mocked(api.getHabitCorrelation).mockReset();
  });

  it("muestra un checkbox por cada hábito del catálogo", () => {
    render(<HabitJournalCard userId={1} />);
    expect(screen.getByLabelText(/alcohol/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/siesta/i)).toBeInTheDocument();
  });

  it("al marcar hábitos y guardar, llama a setHabits con la lista seleccionada", async () => {
    const user = userEvent.setup();
    vi.mocked(api.setHabits).mockResolvedValue(undefined);

    render(<HabitJournalCard userId={1} />);
    await user.click(screen.getByLabelText(/alcohol/i));
    await user.click(screen.getByLabelText(/siesta/i));
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() =>
      expect(api.setHabits).toHaveBeenCalledWith(1, expect.arrayContaining(["alcohol", "siesta"]))
    );
  });

  it("no muestra correlación fabricada cuando datos_suficientes es false", async () => {
    vi.mocked(api.getHabitCorrelation).mockResolvedValue({
      habito: "alcohol",
      dias_con_habito_con_dato: 2,
      dias_sin_habito_con_dato: 1,
      pct_red_con_habito: null,
      pct_red_sin_habito: null,
      datos_suficientes: false,
    });

    render(<HabitJournalCard userId={1} />);
    const select = await screen.findByLabelText(/ver correlación/i);
    const user = userEvent.setup();
    await user.selectOptions(select, "alcohol");

    await waitFor(() =>
      expect(screen.getByText(/todavía no hay suficientes datos/i)).toBeInTheDocument()
    );
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("muestra los porcentajes cuando datos_suficientes es true", async () => {
    vi.mocked(api.getHabitCorrelation).mockResolvedValue({
      habito: "alcohol",
      dias_con_habito_con_dato: 6,
      dias_sin_habito_con_dato: 6,
      pct_red_con_habito: 0.67,
      pct_red_sin_habito: 0.17,
      datos_suficientes: true,
    });

    render(<HabitJournalCard userId={1} />);
    const select = await screen.findByLabelText(/ver correlación/i);
    const user = userEvent.setup();
    await user.selectOptions(select, "alcohol");

    await waitFor(() => expect(screen.getByText(/67%/)).toBeInTheDocument());
    expect(screen.getByText(/17%/)).toBeInTheDocument();
  });
});
