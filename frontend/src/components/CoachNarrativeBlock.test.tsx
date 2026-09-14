import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CoachNarrativeBlock } from "./CoachNarrativeBlock";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthNarrative: vi.fn(),
      getGarminSportNarrative: vi.fn(),
    },
  };
});

describe("CoachNarrativeBlock", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthNarrative).mockReset();
    vi.mocked(api.getGarminSportNarrative).mockReset();
  });

  it("no renderiza nada si todavía no hay una decisión de la que hablar (text/source null)", async () => {
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({ text: null, source: null });
    const { container } = render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() => expect(api.getGarminHealthNarrative).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("muestra el texto del coach cuando existe", async () => {
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({
      text: "Dormiste una hora menos que tu media y se nota en la variabilidad.",
      source: "llm",
    });
    render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/se nota en la variabilidad/i)).toBeInTheDocument()
    );
  });

  it("no repite los datos de la pantalla: la narrativa de respaldo no se dibuja", async () => {
    // El texto real de una captura de verificación, debajo de esas
    // mismas seis cifras: paréntesis a la vista, jerga y una unidad que
    // no es la del resto de la app ("lpm" contra "ppm").
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({
      text:
        "Tu estado de salud hoy: recuperación baja (rojo). (VFC hoy (ms): 69.0, " +
        "VFC media de 28 días (ms): 59.6, pulso en reposo (lpm): 52)",
      source: "template",
    });
    const { container } = render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() => expect(api.getGarminHealthNarrative).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("no muestra ningún error visible si la petición falla (bloque no crítico)", async () => {
    vi.mocked(api.getGarminHealthNarrative).mockRejectedValue(new ApiError(500, "caído"));
    const { container } = render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() => expect(api.getGarminHealthNarrative).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("con categoria consulta la narrativa de deporte en vez de la de salud", async () => {
    vi.mocked(api.getGarminSportNarrative).mockResolvedValue({
      text: "Esta semana llevas más sesiones de running que las 4 anteriores.",
      source: "llm",
    });
    render(<CoachNarrativeBlock userId={1} categoria="running" />);
    await waitFor(() =>
      expect(screen.getByText(/más sesiones de running/i)).toBeInTheDocument()
    );
    expect(api.getGarminHealthNarrative).not.toHaveBeenCalled();
    expect(api.getGarminSportNarrative).toHaveBeenCalledWith(1, "running");
  });
});
